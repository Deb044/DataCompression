"""Descriptive comparisons and a prespecified stratified permutation control."""

import numpy as np
from scipy.stats import rankdata


def roc_auc(outcome, score):
    """Rank-based AUC, with half credit for ties and None for one-class data."""
    outcome = np.asarray(outcome, dtype=bool)
    score = np.asarray(score, dtype=np.float64)
    positives = int(outcome.sum())
    negatives = len(outcome) - positives
    if not positives or not negatives:
        return None
    ranks = rankdata(score)
    return float((ranks[outcome].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def summarize_rows(rows):
    n = len(rows)
    if not n:
        return {'n': 0, 'accuracy': None, 'flip_rate': None, 'correct_to_wrong_rate': None}
    original_correct = sum(row['original_correct'] for row in rows)
    transitions = {key: 0 for key in ['correct_to_correct', 'correct_to_wrong', 'wrong_to_correct', 'wrong_to_wrong']}
    for row in rows:
        before = 'correct' if row['original_correct'] else 'wrong'
        after = 'correct' if row['correct'] else 'wrong'
        transitions[f'{before}_to_{after}'] += 1
    return {
        'n': n, 'accuracy': sum(row['correct'] for row in rows) / n,
        'original_accuracy': original_correct / n,
        'flip_rate': sum(row['flipped'] for row in rows) / n,
        'original_correct_count': original_correct,
        'correct_to_wrong_rate': transitions['correct_to_wrong'] / original_correct if original_correct else None,
        'archive_bytes_total': sum(row['archive_bytes'] for row in rows),
        'payload_bytes_total': sum(row['payload_bytes'] for row in rows),
        'raw_float32_bytes_total': sum(row['raw_float32_bytes'] for row in rows),
        'mean_nrmse': float(np.mean([row['nrmse'] for row in rows if row['nrmse'] is not None])),
        'transitions': transitions,
    }


def gap_analysis(rows, original_trials, thresholds, config):
    evaluation = set(config['evaluation_subjects'])
    originals = {trial['id']: trial for trial in original_trials if trial['subject'] in evaluation}
    summaries = []
    for bits in config['bit_depths']:
        selected = [dict(row) for row in rows if row['subject'] in evaluation and row['method'] == config['primary_method'] and row['bits'] == bits]
        for row in selected:
            row['group'] = ['low', 'middle', 'high'][int(np.searchsorted(thresholds, row['gap'], side='left'))]
        outcome = np.array([row['flipped'] for row in selected])
        gaps = np.array([row['gap'] for row in selected])
        observed = roc_auc(outcome, -gaps)
        # Preserve participant and target membership in every shuffled control.
        strata = {}
        for i, row in enumerate(selected):
            strata.setdefault((row['subject'], row['target_hz']), []).append(i)
        rng = np.random.default_rng(config['seed'] + bits)
        null = []
        if observed is not None:
            for _ in range(config['permutations']):
                shuffled = gaps.copy()
                for indices in strata.values():
                    shuffled[indices] = rng.permutation(gaps[indices])
                null.append(roc_auc(outcome, -shuffled))
        predictors = {
            'low_gap': observed,
            'range_over_rms': roc_auc(outcome, [originals[row['id']]['range_over_rms'] for row in selected]),
            'low_spectral_concentration': roc_auc(outcome, [-originals[row['id']]['spectral_concentration'] for row in selected]),
        }
        summaries.append({
            'bits': bits, 'method': config['primary_method'], 'n': len(selected),
            'failures': int(outcome.sum()), 'groups': {group: summarize_rows([row for row in selected if row['group'] == group]) for group in ['low', 'middle', 'high']},
            'predictor_auc': predictors,
            'shuffled_auc_mean': float(np.mean(null)) if null else None,
            'shuffled_auc_95_range': np.quantile(null, [0.025, 0.975]).tolist() if null else None,
            'permutation_p_one_sided': (1 + sum(value >= observed for value in null)) / (len(null) + 1) if null else None,
            'participants': [{'subject': subject, 'groups': {group: summarize_rows([row for row in selected if row['subject'] == subject and row['group'] == group]) for group in ['low', 'middle', 'high']}} for subject in config['evaluation_subjects']],
        })
    return summaries
