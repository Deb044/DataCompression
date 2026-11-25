"""Measure task performance at matched byte caps; never synthesize results."""

from pathlib import Path
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import platform
import struct
import subprocess
import time

import numpy as np
import scipy
import sklearn
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, roc_auc_score

from . import codec
from .data import CACHE, ROOT, load_recording
from .decoders import epochs, make_decoder

CONFIG_PATH = Path(__file__).with_name('config.json')


def implementation_hash():
    return hashlib.sha256(b''.join(Path(__file__).with_name(name).read_bytes()
        for name in ['run.py', 'data.py', 'codec.py', 'decoders.py'])).hexdigest()


def split_recording(signal, events, labels, task, config):
    """Chronological offline split with no overlapping train/test epochs."""
    rate = config['sample_rate_hz']
    width = round(config['epoch_seconds'][task]*rate)
    boundary = int(events[int(len(events)*config['training_fraction'])])
    guard = round(config['boundary_guard_seconds']*rate)
    train = events + width <= boundary - guard
    test = events >= boundary + guard
    start = math.floor((boundary + guard)/rate)*rate
    last = min(signal.shape[1]//rate*rate, math.ceil((events[test][-1]+width)/rate)*rate)
    test_signal = signal[:, start:last]
    x_train, y_train, train_events = epochs(signal, events[train], labels[train], width)
    x_test, y_test, test_events = epochs(test_signal, events[test]-start, labels[test], width)
    expected = {1, 2, 3, 4} if task == 'SSVEP' else {1, 2}
    if set(y_train) != expected or set(y_test) != expected:
        raise ValueError('Both chronological blocks must contain every class')
    return x_train, y_train, x_test, y_test, test_events, test_signal, dict(
        source_events=len(events), training_epochs=len(y_train), test_epochs=len(y_test),
        train_class_counts=dict(Counter(map(str, y_train))), test_class_counts=dict(Counter(map(str, y_test))),
        split_sample=boundary, test_start_sample=start, test_stop_sample=last,
        last_training_epoch_end=int(train_events[-1]+width), first_test_epoch_start=int(test_events[0]+start))


def scores(y, prediction, values):
    result = dict(accuracy=float(accuracy_score(y, prediction)),
                  balanced_accuracy=float(balanced_accuracy_score(y, prediction)),
                  confusion_matrix=confusion_matrix(y, prediction).tolist())
    if len(np.unique(y)) == 2:
        # sklearn's decision score points toward class 2. ERP target is class 1.
        result['roc_auc'] = float(roc_auc_score(y == 2, values))
    return result


def run_subject(subject, task, config, output, baseline_only=False):
    started = time.time()
    signal, events, labels, source = load_recording(subject, task, config)
    training, y_train, testing, truth, test_events, original, split = split_recording(signal, events, labels, task, config)
    decoder = make_decoder(task, config).fit(training, y_train)
    before, before_scores = decoder.predict(testing)
    baseline = scores(truth, before, before_scores)
    print(f'S{subject:02d} {task}: baseline balanced accuracy {baseline["balanced_accuracy"]:.3f}; '
          f'train {len(y_train)}, test {len(truth)}', flush=True)
    identity = dict(subject=subject, task=task,
                    split='development' if subject in config['development_subjects'] else 'evaluation')
    baseline = dict(identity, **baseline, n_test=len(truth), **split)
    if baseline_only:
        return dict(baseline=baseline, points=[], predictions=[], source=source)
    del signal, training, testing
    rate = config['sample_rate_hz']
    channels, samples = original.shape
    frames = samples // rate
    header = codec.corpus_header(channels, samples, config)
    overhead = 4 + math.ceil(len(header)/frames)
    destination = CACHE / 'encoded' / f'S{subject:02d}_{task}'
    destination.mkdir(parents=True, exist_ok=True)
    budgets = config['budgets_bytes_per_second_channel']
    control_path = destination / 'lossless.eegpack'
    with control_path.open('wb') as control:
        control.write(header)
        for start in range(0, samples, rate):
            encoded = codec.encode(original[:, start:start+rate], 'float32', sample_rate=rate)
            control.write(struct.pack('<I', len(encoded)) + encoded)
    recovered = codec.read_corpus(control_path)
    if not np.array_equal(original, recovered):
        raise AssertionError('Lossless corpus must recover exact float32 samples')
    check, _ = decoder.predict(epochs(recovered, test_events, truth, config['epoch_seconds'][task]*rate)[0])
    if not np.array_equal(check, before):
        raise AssertionError('Lossless decoder decisions changed')
    baseline.update(raw_bytes=original.nbytes, duration_seconds=samples/rate,
                    lossless_bytes=control_path.stat().st_size, lossless_verified=True,
                    signal_channels=channels)
    points, predictions = [], []
    original_norm = float(np.linalg.norm(original.astype(float)-original.mean(axis=1, keepdims=True)))
    for method in config['methods']:
        paths = {b: destination / f'{method}_{b}.eegpack' for b in budgets}
        streams = {b: path.open('wb') for b, path in paths.items()}
        for stream in streams.values():
            stream.write(header)
        feasible = {b: True for b in budgets}
        settings = {b: Counter() for b in budgets}
        examples = {}
        try:
            for i, start in enumerate(range(0, samples, rate)):
                best = codec.choose_frames(original[:, start:start+rate], method, config, overhead)
                for budget, selected in best.items():
                    if selected is None:
                        feasible[budget] = False
                        continue
                    streams[budget].write(struct.pack('<I', selected['bytes']) + selected['data'])
                    settings[budget][f'{selected["bits"]}bits/{selected["retained"]}coefficients'] += 1
                    if i == 0:
                        examples[budget] = selected['data']
        finally:
            for stream in streams.values():
                stream.close()
        for budget in budgets:
            common = dict(identity, method=method, budget=budget, feasible=feasible[budget])
            if not feasible[budget]:
                points.append(common)
                continue
            recovered = codec.read_corpus(paths[budget])
            actual_bytes = paths[budget].stat().st_size
            cap = budget*channels*samples/rate
            if actual_bytes > cap:
                raise AssertionError('Archive exceeds declared corpus budget')
            prediction, values = decoder.predict(epochs(recovered, test_events, truth, config['epoch_seconds'][task]*rate)[0])
            measured = scores(truth, prediction, values)
            measured.update(archive_bytes=actual_bytes, raw_bytes=original.nbytes,
                            duration_seconds=samples/rate, channels=channels,
                            rate=actual_bytes/(channels*samples/rate),
                            nrmse=float(np.linalg.norm(original.astype(float)-recovered.astype(float))/original_norm),
                            balanced_accuracy_drop=baseline['balanced_accuracy']-measured['balanced_accuracy'],
                            flip_rate=float(np.mean(prediction != before)), n_test=len(truth),
                            settings=dict(settings[budget]),
                            encoded_sha256=hashlib.sha256(paths[budget].read_bytes()).hexdigest())
            points.append(dict(common, **measured))
            for i, (target, old, new) in enumerate(zip(truth, before, prediction)):
                predictions.append(dict(identity, method=method, budget=budget, trial=i,
                                         truth=int(target), original=int(old), reconstructed=int(new)))
            # Small independent example, not an uncounted shared codebook.
            if subject == config['evaluation_subjects'][0]:
                sample = output / 'archives' / f'{task}_{method}_{budget}_first-frame.zip'
                sample.parent.mkdir(exist_ok=True)
                sample.write_bytes(examples[budget])
        print(f'S{subject:02d} {task}: {method} finished ({frames} frames)', flush=True)
    baseline['elapsed_seconds'] = time.time()-started
    return dict(baseline=baseline, points=points, predictions=predictions, source=source)


def aggregate(runs, config):
    baselines = [run['baseline'] for run in runs]
    points = [point for run in runs for point in run['points']]
    groups = []
    for task in config['tasks']:
        for method in config['methods']:
            for budget in config['budgets_bytes_per_second_channel']:
                selected = [p for p in points if p['task']==task and p['method']==method and p['budget']==budget and p['split']=='evaluation']
                valid = [p for p in selected if p['feasible']]
                complete = len(valid)==len(config['evaluation_subjects'])
                group = dict(task=task, method=method, budget=budget, complete=complete, n_subjects=len(valid))
                if complete:
                    for field in ['balanced_accuracy', 'balanced_accuracy_drop', 'accuracy', 'flip_rate', 'nrmse', 'rate']:
                        values = np.array([p[field] for p in valid])
                        group[field] = float(values.mean())
                        group[field+'_range'] = [float(values.min()), float(values.max())]
                    group['original_balanced_accuracy'] = float(np.mean([b['balanced_accuracy'] for b in baselines if b['task']==task and b['split']=='evaluation']))
                groups.append(group)
    expected = {(s,t) for s in config['development_subjects']+config['evaluation_subjects'] for t in config['tasks']}
    return dict(config=config, baselines=baselines, points=points, groups=groups,
                complete={(b['subject'],b['task']) for b in baselines} == expected and bool(points),
                sources=[run['source'] for run in runs],
                environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__),
                code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                protocol_sha256=hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                implementation_sha256=implementation_hash(),
                interpretation='Small paired application-and-decoder benchmark; not a universal ranking of EEG task difficulty.')


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subjects', nargs='+', type=int)
    parser.add_argument('--tasks', nargs='+', choices=['SSVEP', 'MI', 'ERP'])
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'results'/'benchmark')
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    runs = []
    for subject in args.subjects or config['development_subjects']+config['evaluation_subjects']:
        for task in args.tasks or config['tasks']:
            cache = CACHE / f'S{subject:02d}_{task}_measured.json'
            protocol_hash = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
            if not args.baseline_only and cache.exists():
                result = json.loads(cache.read_text())
                if result.get('protocol_hash') != protocol_hash or result.get('implementation_hash') != implementation_hash():
                    raise ValueError('Measured cache belongs to another protocol or implementation')
                print(f'Reusing measured S{subject:02d} {task}', flush=True)
            else:
                result = run_subject(subject, task, config, args.output, args.baseline_only)
                result['protocol_hash'] = protocol_hash
                result['implementation_hash'] = implementation_hash()
                if not args.baseline_only:
                    cache.write_text(json.dumps(result))
            runs.append(result)
            name = 'baselines.json' if args.baseline_only else 'summary.json'
            (args.output/name).write_text(json.dumps(aggregate(runs, config), indent=2, allow_nan=False)+'\n')
    if not args.baseline_only:
        write_csv(args.output/'predictions.csv', [p for r in runs for p in r['predictions']])
        print('Recorded summary and trial predictions.', flush=True)


if __name__ == '__main__':
    main()
