"""Paired participant bootstrap; EEG trials are not independent people."""

from itertools import combinations
import hashlib
import json

import numpy as np

from .data import ROOT


def describe(values, draws):
    values = np.asarray(values, dtype=float)
    bootstrapped = values[draws].mean(axis=1)
    return dict(
        mean=float(values.mean()), median=float(np.median(values)),
        ci95=np.quantile(bootstrapped, [0.025, 0.975]).tolist(),
        participant_range=[float(values.min()), float(values.max())],
    )


def analyze(data, draws):
    """Carry every condition together when a participant is resampled."""
    config = data['config']
    subjects = config['evaluation_subjects']
    points = {(p['subject'], p['task'], p['method'], p['budget']): p
              for p in data['points'] if p['split'] == 'evaluation'}
    baselines = {(b['subject'], b['task']): b for b in data['baselines']}

    def losses(task, method, budget):
        selected = [points[(s, task, method, budget)] for s in subjects]
        if not all(p['feasible'] for p in selected):
            raise ValueError('Cannot compare an incomplete paired cohort')
        return np.array([p['balanced_accuracy_drop'] for p in selected])

    groups, task_differences, method_differences = [], [], []
    for method in config['methods']:
        for budget in config['budgets_bytes_per_second_channel']:
            matrix = np.stack([losses(t, method, budget) for t in config['tasks']], axis=1)
            tied = np.isclose(matrix, matrix.max(axis=1, keepdims=True), atol=1e-10, rtol=0)
            # If all tasks tie, each receives one third of that person's credit.
            credits = tied / tied.sum(axis=1, keepdims=True)
            for i, task in enumerate(config['tasks']):
                groups.append(dict(
                    task=task, method=method, budget=budget,
                    **describe(matrix[:, i], draws),
                    largest_loss_share=float(credits[:, i].mean()),
                    tied_participants=int(np.sum(tied.sum(axis=1) > 1)),
                ))
            for first, second in combinations(range(len(config['tasks'])), 2):
                task_differences.append(dict(
                    first=config['tasks'][first], second=config['tasks'][second],
                    method=method, budget=budget,
                    **describe(matrix[:, first] - matrix[:, second], draws),
                ))
    for task in config['tasks']:
        for budget in config['budgets_bytes_per_second_channel']:
            for first, second in combinations(config['methods'], 2):
                method_differences.append(dict(
                    task=task, first=first, second=second, budget=budget,
                    **describe(losses(task, first, budget) - losses(task, second, budget), draws),
                ))
    return dict(
        groups=groups, task_differences=task_differences,
        method_differences=method_differences,
        baselines=[dict(task=task, **describe(
            [baselines[(s, task)]['balanced_accuracy'] for s in subjects], draws,
        )) for task in config['tasks']],
    )


def main():
    primary_path = ROOT / 'results' / 'benchmark' / 'summary.json'
    alternative_path = ROOT / 'results' / 'robustness' / 'summary.json'
    primary = json.loads(primary_path.read_text())
    alternative = json.loads(alternative_path.read_text())
    subjects = primary['config']['evaluation_subjects']
    if not primary['complete'] or not alternative['complete']:
        raise ValueError('Both decoder comparisons must be complete')
    if subjects != alternative['config']['evaluation_subjects']:
        raise ValueError('Decoder comparisons must use the same people')
    seed, resamples = 321, 10_000
    draws = np.random.default_rng(seed).integers(len(subjects), size=(resamples, len(subjects)))
    result = dict(
        participants=subjects, seed=seed, resamples=resamples,
        interval_note='Pointwise percentile 95% participant-bootstrap intervals; '
                      'all conditions paired; not multiplicity-adjusted or trial-level intervals.',
        primary=analyze(primary, draws), alternative=analyze(alternative, draws),
        primary_summary_sha256=hashlib.sha256(primary_path.read_bytes()).hexdigest(),
        alternative_summary_sha256=hashlib.sha256(alternative_path.read_bytes()).hexdigest(),
    )
    destination = primary_path.with_name('statistics.json')
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f'Participant bootstrap: {len(subjects)} people, {resamples} paired resamples.')


if __name__ == '__main__':
    main()
