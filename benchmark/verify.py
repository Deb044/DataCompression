"""Independent metric/size checks plus optional decoder replay from stored bytes."""

from collections import defaultdict
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score, accuracy_score

from .codec import decode, read_corpus
from .data import CACHE, ROOT, digest, load_recording
from .decoders import epochs, make_decoder
from .run import implementation_hash, split_recording


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', action='store_true', help='Refit originals and decode every stored evaluation corpus')
    parser.add_argument('--alternative', action='store_true', help='Verify the alternative-decoder export')
    args = parser.parse_args()
    output = ROOT/'results'/('robustness' if args.alternative else 'benchmark')
    result = json.loads((output/'summary.json').read_text())
    config = result['config']
    assert result['complete']
    expected_config = json.loads((ROOT/'benchmark'/'config.json').read_text())
    decoder_factory = make_decoder
    if args.alternative:
        from .alternative_decoders import make_alternative_decoder
        from .robustness import decoder_hash
        expected_config['development_subjects'] = []
        decoder_factory = make_alternative_decoder
        assert result['decoder_implementation_sha256'] == decoder_hash()
        assert result['primary_summary_sha256'] == digest(ROOT/'results'/'benchmark'/'summary.json')
    assert config == expected_config
    assert result['implementation_sha256'] == implementation_hash()
    expected_keys = {(s, t, m, b) for s in config['development_subjects']+config['evaluation_subjects']
                     for t in config['tasks'] for m in config['methods']
                     for b in config['budgets_bytes_per_second_channel']}
    actual_keys = [(p['subject'], p['task'], p['method'], p['budget']) for p in result['points']]
    assert set(actual_keys) == expected_keys and len(actual_keys) == len(expected_keys)
    predictions = defaultdict(list)
    with (output/'predictions.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            key = (int(row['subject']), row['task'], row['method'], int(row['budget']))
            predictions[key].append(row)
    baseline = {(b['subject'], b['task']): b for b in result['baselines']}
    for point in result['points']:
        key = (point['subject'], point['task'], point['method'], point['budget'])
        if not point['feasible']:
            assert key not in predictions
            continue
        rows = predictions[key]
        assert [int(r['trial']) for r in rows] == list(range(len(rows)))
        truth = [int(r['truth']) for r in rows]
        before = [int(r['original']) for r in rows]
        after = [int(r['reconstructed']) for r in rows]
        assert len(rows) == point['n_test']
        np.testing.assert_allclose(balanced_accuracy_score(truth, after), point['balanced_accuracy'])
        np.testing.assert_allclose(accuracy_score(truth, after), point['accuracy'])
        original_ba = balanced_accuracy_score(truth, before)
        np.testing.assert_allclose(original_ba, baseline[key[:2]]['balanced_accuracy'])
        np.testing.assert_allclose(original_ba-point['balanced_accuracy'], point['balanced_accuracy_drop'])
        np.testing.assert_allclose(np.mean(np.array(before)!=after), point['flip_rate'])
        cap = point['budget']*point['channels']*point['duration_seconds']
        assert point['archive_bytes'] <= cap
        corpus = CACHE/'encoded'/f'S{point["subject"]:02d}_{point["task"]}'/f'{point["method"]}_{point["budget"]}.eegpack'
        assert corpus.stat().st_size == point['archive_bytes']
        assert digest(corpus) == point['encoded_sha256']
        np.testing.assert_allclose(point['rate'], point['archive_bytes']/(point['channels']*point['duration_seconds']))
    for group in result['groups']:
        points = [p for p in result['points'] if p['task']==group['task'] and p['method']==group['method'] and p['budget']==group['budget'] and p['split']=='evaluation' and p['feasible']]
        assert group['complete'] == (len(points)==len(config['evaluation_subjects']))
        if group['complete']:
            for field in ['balanced_accuracy', 'balanced_accuracy_drop', 'accuracy', 'rate', 'nrmse', 'flip_rate']:
                np.testing.assert_allclose(np.mean([p[field] for p in points]), group[field])
    for sample in (output/'archives').glob('*.zip'):
        assert decode(sample.read_bytes()).shape == (len(config['channels']), config['sample_rate_hz'])
    if args.replay:
        for subject in config['evaluation_subjects']:
            for task in config['tasks']:
                signal, events, labels, _ = load_recording(subject, task, config)
                training, y_train, testing, truth, offsets, original, _ = split_recording(signal, events, labels, task, config)
                decoder = decoder_factory(task, config).fit(training, y_train)
                np.testing.assert_array_equal(original, read_corpus(CACHE/'encoded'/f'S{subject:02d}_{task}'/'lossless.eegpack'))
                for point in result['points']:
                    if point['subject']!=subject or point['task']!=task or not point['feasible']:
                        continue
                    path = CACHE/'encoded'/f'S{subject:02d}_{task}'/f'{point["method"]}_{point["budget"]}.eegpack'
                    reconstructed = read_corpus(path)
                    batch, y, _ = epochs(reconstructed, offsets, truth, config['epoch_seconds'][task]*config['sample_rate_hz'])
                    actual, _ = decoder.predict(batch)
                    expected = [int(r['reconstructed']) for r in predictions[(subject, task, point['method'], point['budget'])]]
                    np.testing.assert_array_equal(actual, expected)
                    centered = original.astype(float)-original.mean(axis=1, keepdims=True)
                    np.testing.assert_allclose(np.linalg.norm(original.astype(float)-reconstructed.astype(float))/np.linalg.norm(centered), point['nrmse'])
                print(f'Replayed S{subject:02d} {task}', flush=True)
    print(f'Checked {len(result["points"])} measured points, {len(result["groups"])} aggregates, '
          f'{sum(map(len,predictions.values()))} trial predictions and all byte caps.', flush=True)


if __name__ == '__main__':
    main()
