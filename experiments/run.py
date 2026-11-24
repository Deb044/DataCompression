"""Run both controlled experiments and export traceable CSV/JSON results.

Run from the repository root: python -m experiments.run
Raw recordings stay in .data; the site only reads the compact result exports.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
import zlib

import numpy as np

from .analysis import gap_analysis, summarize_rows
from .codec import MU, encode_payload, make_archive, read_archive
from .dataset import DEFAULT_CACHE, ROOT, ensure_files, subject_trials
from .decoder import decode, distortion, signal_features

CONFIG_PATH = Path(__file__).with_name('config.json')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def repository_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run(cache, output):
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text())
    if config['sample_rate_hz'] != 250 or config['mu'] != MU:
        raise ValueError('The benchmark release and EEG1 format require fs=250 and mu=255')
    if set(config['development_subjects']) & set(config['evaluation_subjects']):
        raise ValueError('Development and evaluation participants overlap')
    subjects = config['development_subjects'] + config['evaluation_subjects']
    source_records = ensure_files(subjects, cache)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    example_directory = output / 'archives'
    example_directory.mkdir(exist_ok=True)
    code_commit = repository_commit()
    rows, originals, examples = [], [], []
    for subject in subjects:
        split = 'development' if subject in config['development_subjects'] else 'evaluation'
        subject_correct = 0
        for identity, signal in subject_trials(subject, config, cache):
            prediction, gap, scores = decode(signal, config)
            original = dict(identity, split=split, original_prediction_hz=prediction,
                            original_correct=prediction == identity['target_hz'], gap=gap,
                            **signal_features(signal, config))
            originals.append(original)
            subject_correct += original['original_correct']
            # All four targets of the first evaluation block, chosen before results.
            is_example = subject == config['evaluation_subjects'][0] and identity['block'] == 1
            example = {'id': identity['id'], 'target_hz': identity['target_hz'],
                       'channel': 'Oz', 'original_prediction_hz': prediction,
                       'original_scores': scores.tolist(), 'original': signal[1].round(6).tolist(),
                       'conditions': []} if is_example else None
            conditions = [('float32', 32)] + [(method, bits) for method in config['methods'] for bits in config['bit_depths']]
            for method, bits in conditions:
                payload = encode_payload(signal, bits, method)
                archive = make_archive(payload)
                reconstruction = read_archive(archive)
                if method == 'float32' and reconstruction.tobytes() != signal.tobytes():
                    raise AssertionError('Lossless control failed byte-for-byte equality')
                reconstructed_prediction, _, reconstructed_scores = decode(reconstruction, config)
                row = dict(identity, split=split, method=method, bits=bits,
                           original_prediction_hz=prediction, prediction_hz=reconstructed_prediction,
                           original_correct=bool(original['original_correct']),
                           correct=reconstructed_prediction == identity['target_hz'],
                           flipped=reconstructed_prediction != prediction, gap=gap,
                           raw_float32_bytes=signal.nbytes, payload_bytes=len(payload),
                           archive_bytes=len(archive), archive_sha256=hashlib.sha256(archive).hexdigest(),
                           **distortion(signal, reconstruction))
                rows.append(row)
                if example is not None and method != 'float32':
                    example['conditions'].append({'method': method, 'bits': bits,
                        'prediction_hz': reconstructed_prediction, 'archive_bytes': len(archive),
                        'nrmse': row['nrmse'], 'scores': reconstructed_scores.tolist(),
                        'reconstruction': reconstruction[1].round(6).tolist()})
                if is_example and identity['target_hz'] == config['target_frequencies_hz'][0]:
                    filename = f"{identity['id']}-{method}-{bits}.zip"
                    (example_directory / filename).write_bytes(archive)
            if example is not None:
                examples.append(example)
        print(f'S{subject:02d} {split}: {subject_correct}/24 original decisions correct', flush=True)

    development_gaps = [trial['gap'] for trial in originals if trial['split'] == 'development']
    thresholds = np.quantile(development_gaps, [1 / 3, 2 / 3]).tolist()
    conditions = []
    for split in ['development', 'evaluation']:
        for method, bits in [('float32', 32)] + [(m, b) for m in config['methods'] for b in config['bit_depths']]:
            selected = [row for row in rows if row['split'] == split and row['method'] == method and row['bits'] == bits]
            summary = summarize_rows(selected)
            seconds_channels = len(selected) * len(config['channels']) * (config['stop_sample'] - config['start_sample']) / config['sample_rate_hz']
            summary.update({'split': split, 'method': method, 'bits': bits,
                'archive_bytes_per_second_channel': summary['archive_bytes_total'] / seconds_channels,
                'archive_fraction_of_float32': summary['archive_bytes_total'] / summary['raw_float32_bytes_total'],
                'participants': [dict(subject=s, **summarize_rows([r for r in selected if r['subject'] == s])) for s in (config['development_subjects'] if split == 'development' else config['evaluation_subjects'])]})
            conditions.append(summary)
    gaps = gap_analysis(rows, originals, thresholds, config)
    provenance = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'code_commit': code_commit,
        'config_sha256': hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        'configuration': config, 'source_files': source_records,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                        **{name: importlib.metadata.version(name) for name in ['scipy', 'matplotlib', 'py7zr']},
                        'zlib_runtime': zlib.ZLIB_RUNTIME_VERSION},
        'duration_seconds': round(time.perf_counter() - started, 3),
        'notes': [
            'Official downloaded MATLAB values are float64. Baseline is a declared centered float32 representation, not the native acquisition bit depth.',
            'Every archive includes shape and method. Quantized payloads additionally include float32 per-channel minimum and maximum. All reported ZIP sizes count the complete archive.',
            'Each trial is archived independently; corpus sizes are sums of those independent archive sizes.',
            'No participant, target or trial was selected for high observed accuracy. No artifact rejection was performed.',
            'All participants are experienced SSVEP users. Four-class simplified task, 25% chance accuracy; not the full 40-target benchmark.',
            'Primary vulnerability test: uniform, 2 bits. Other precisions are exploratory and their permutation p values are not multiplicity-corrected.',
            'Permutation controls shuffle original gaps within participant and true-target strata. Their 95% range is a null range, not a confidence interval.',
            'All evaluation participants are shown separately. No population-level claim or clinical conclusion is inferred.',
            'Displayed waveform arrays are rounded to six decimal places; metrics use full reconstructed arrays.',
            'Runtime includes local cache verification and extraction; download time is not included when files were already cached.',
        ],
    }
    summary = {'schema_version': 1, 'status': 'measured', 'provenance': provenance,
               'gap_thresholds': thresholds, 'conditions': conditions, 'gap_analysis': gaps,
               'evaluation_trials': sum(trial['split'] == 'evaluation' for trial in originals),
               'development_trials': sum(trial['split'] == 'development' for trial in originals)}
    write_csv(output / 'trials.csv', rows)
    write_csv(output / 'original_trials.csv', originals)
    write_json(output / 'summary.json', summary)
    write_json(output / 'provenance.json', provenance)
    write_json(output / 'examples.json', {'sample_rate_hz': config['sample_rate_hz'],
               'target_frequencies_hz': config['target_frequencies_hz'], 'trials': examples})
    from .plots import render_figures
    render_figures(summary, examples, output)
    print(f'Results saved to {output}. Evaluation trials: {summary["evaluation_trials"]}', flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--download-only', action='store_true')
    args = parser.parse_args()
    if args.download_only:
        config = json.loads(CONFIG_PATH.read_text())
        ensure_files(config['development_subjects'] + config['evaluation_subjects'], args.cache)
    else:
        run(args.cache, args.output)


if __name__ == '__main__':
    main()
