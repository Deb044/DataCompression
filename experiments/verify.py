"""Audit exported results independently of the presentation layer.

Checks aggregate counts against CSV rows and recomputes predictions and errors
from the archived example. No new data selection or classifier tuning occurs.
"""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .analysis import roc_auc
from .codec import read_archive
from .dataset import ROOT
from .decoder import decode, distortion


def verify(output=ROOT / 'results'):
    output = Path(output)
    summary = json.loads((output / 'summary.json').read_text())
    config = summary['provenance']['configuration']
    with (output / 'trials.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    trial_count = (len(config['development_subjects']) + len(config['evaluation_subjects'])) * 24
    conditions = 1 + len(config['methods']) * len(config['bit_depths'])
    assert len(rows) == trial_count * conditions
    assert len({(r['id'], r['method'], r['bits']) for r in rows}) == len(rows)
    for condition in summary['conditions']:
        selected = [r for r in rows if r['split'] == condition['split'] and r['method'] == condition['method'] and int(r['bits']) == condition['bits']]
        assert len(selected) == condition['n']
        assert sum(int(r['archive_bytes']) for r in selected) == condition['archive_bytes_total']
        assert sum(r['correct'] == 'True' for r in selected) / len(selected) == condition['accuracy']
        assert sum(r['flipped'] == 'True' for r in selected) / len(selected) == condition['flip_rate']
        for r in selected:
            assert (r['prediction_hz'] == r['target_hz']) == (r['correct'] == 'True')
            assert (r['prediction_hz'] != r['original_prediction_hz']) == (r['flipped'] == 'True')
    for condition in summary['gap_analysis']:
        selected = [r for r in rows if r['split'] == 'evaluation' and r['method'] == config['primary_method'] and int(r['bits']) == condition['bits']]
        observed = roc_auc([r['flipped'] == 'True' for r in selected], [-float(r['gap']) for r in selected])
        assert observed == condition['predictor_auc']['low_gap']
        assert sum(group['n'] for group in condition['groups'].values()) == len(selected)
    archives = sorted((output / 'archives').glob('*.zip'))
    assert len(archives) == conditions
    original_path = next(p for p in archives if p.name.endswith('-float32-32.zip'))
    original = read_archive(original_path.read_bytes())
    for path in archives:
        data = path.read_bytes()
        matching = next(r for r in rows if path.name == f"{r['id']}-{r['method']}-{r['bits']}.zip")
        assert len(data) == int(matching['archive_bytes'])
        assert hashlib.sha256(data).hexdigest() == matching['archive_sha256']
        reconstructed = read_archive(data)
        assert decode(reconstructed, config)[0] == int(matching['prediction_hz'])
        measured = distortion(original, reconstructed)
        np.testing.assert_allclose(measured['nrmse'], float(matching['nrmse']), atol=1e-12)
    print(f'Verified {len(rows)} paired-condition rows, {len(summary["conditions"])} aggregates, all gap AUCs and {len(archives)} self-contained archives.')


if __name__ == '__main__':
    verify()
