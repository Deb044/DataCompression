"""Evaluate alternative decoders on the exact existing compressed corpora."""

import hashlib
import json
from pathlib import Path

import numpy as np

from .alternative_decoders import make_alternative_decoder
from .codec import read_corpus
from .data import CACHE, ROOT, load_recording
from .decoders import epochs
from .run import aggregate, scores, split_recording, write_csv


def decoder_hash():
    names = ['alternative_decoders.py', 'robustness.py']
    return hashlib.sha256(b''.join(Path(__file__).with_name(n).read_bytes() for n in names)).hexdigest()


def evaluate(subject, task, primary):
    config = primary['config']
    signal, events, labels, source = load_recording(subject, task, config)
    training, y_train, testing, truth, offsets, original, _ = split_recording(
        signal, events, labels, task, config,
    )
    decoder = make_alternative_decoder(task, config).fit(training, y_train)
    before, values = decoder.predict(testing)
    baseline = next(b.copy() for b in primary['baselines'] if b['subject'] == subject and b['task'] == task)
    baseline.update(scores(truth, before, values))
    del signal, training, testing

    folder = CACHE / 'encoded' / f'S{subject:02d}_{task}'
    lossless, _ = decoder.predict(epochs(
        read_corpus(folder / 'lossless.eegpack'), offsets, truth,
        config['epoch_seconds'][task] * config['sample_rate_hz'],
    )[0])
    np.testing.assert_array_equal(before, lossless)
    points, predictions = [], []
    for recorded in primary['points']:
        if recorded['subject'] != subject or recorded['task'] != task:
            continue
        point = recorded.copy()
        if point['feasible']:
            reconstructed = read_corpus(folder / f'{point["method"]}_{point["budget"]}.eegpack')
            batch, y, _ = epochs(
                reconstructed, offsets, truth,
                config['epoch_seconds'][task] * config['sample_rate_hz'],
            )
            prediction, values = decoder.predict(batch)
            point.update(scores(y, prediction, values))
            point['balanced_accuracy_drop'] = baseline['balanced_accuracy'] - point['balanced_accuracy']
            point['flip_rate'] = float(np.mean(prediction != before))
            for trial, (target, old, new) in enumerate(zip(y, before, prediction)):
                predictions.append(dict(
                    subject=subject, task=task, split='evaluation', method=point['method'],
                    budget=point['budget'], trial=trial, truth=int(target),
                    original=int(old), reconstructed=int(new),
                ))
        points.append(point)
    print(f'Alternative decoder: S{subject:02d} {task}', flush=True)
    return dict(baseline=baseline, points=points, predictions=predictions, source=source)


def main():
    primary_path = ROOT / 'results' / 'benchmark' / 'summary.json'
    primary = json.loads(primary_path.read_text())
    if not primary['complete']:
        raise ValueError('Complete the primary benchmark first')
    # Development records are not needed for this fixed sensitivity check.
    config = dict(primary['config'], development_subjects=[])
    runs = [evaluate(subject, task, primary)
            for subject in config['evaluation_subjects'] for task in config['tasks']]
    result = aggregate(runs, config)
    result.update(
        decoder_family='alternative', decoder_implementation_sha256=decoder_hash(),
        primary_summary_sha256=hashlib.sha256(primary_path.read_bytes()).hexdigest(),
        decoder_descriptions={
            'SSVEP': 'Harmonic spectral peak/background ratios',
            'MI': 'Channel mu/beta log-power + shrinkage LDA',
            'ERP': 'Time-bin features + balanced logistic regression',
        },
    )
    output = ROOT / 'results' / 'robustness'
    output.mkdir(exist_ok=True)
    (output / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    write_csv(output / 'predictions.csv', [p for r in runs for p in r['predictions']])
    print('Saved alternative-decoder results.', flush=True)


if __name__ == '__main__':
    main()
