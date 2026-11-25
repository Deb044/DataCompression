"""Export small editable chart/table inputs from the verified study results."""

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(folder, name):
    return json.loads((ROOT / 'results' / folder / name).read_text())


def write_csv(name, fields, rows):
    with (HERE / 'data' / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    primary = read('benchmark', 'summary.json')
    alternative = read('robustness', 'summary.json')
    statistics = read('benchmark', 'statistics.json')
    for folder in ['benchmark', 'robustness']:
        verification = read(folder, 'verification.json')
        assert verification['replayed'] and verification['bootstrap_intervals_checked']
        assert verification['summary_sha256'] == hashlib.sha256(
            (ROOT / 'results' / folder / 'summary.json').read_bytes()).hexdigest()
    assert primary['complete'] and alternative['complete']
    assert primary['config']['evaluation_subjects'] == list(range(7, 27))
    (HERE / 'data').mkdir(exist_ok=True)
    # The white-background PowerPoint reads the same verified estimates as LaTeX.
    deck_data = {family: statistics[family] for family in ['primary', 'alternative']}
    (HERE / 'data' / 'study.json').write_text(
        json.dumps(deck_data, indent=2) + '\n', encoding='utf-8')

    def estimate(family, task, method, budget):
        return next(g for g in statistics[family]['groups']
                    if g['task'] == task and g['method'] == method and g['budget'] == budget)

    fields = ['budget'] + [name for task in ['SSVEP', 'MI', 'ERP']
                           for name in [task, task + 'lo', task + 'hi']]
    for method in primary['config']['methods']:
        rows = []
        for budget in primary['config']['budgets_bytes_per_second_channel']:
            row = dict(budget=budget)
            for task in primary['config']['tasks']:
                value = estimate('primary', task, method, budget)
                row.update({task: 100 * value['mean'], task + 'lo': 100 * value['ci95'][0],
                            task + 'hi': 100 * value['ci95'][1]})
            rows.append(row)
        write_csv(method + '.csv', fields, rows)

    table = [r'{\fontsize{8.5}{10.5}\selectfont', r'\begin{tabular}{lrrr}',
             r'\toprule', r'Task & Uniform & $\mu$-law & DCT\\', r'\midrule']
    for task, label in [('SSVEP', 'SSVEP'), ('MI', 'Motor imagery'), ('ERP', 'P300')]:
        values = []
        for method in primary['config']['methods']:
            first = estimate('primary', task, method, 32)['mean'] * 100
            second = estimate('alternative', task, method, 32)['mean'] * 100
            values.append(r'\textcolor{eegteal}{%.2f} / \textcolor{eegcoral}{%.2f}' % (first, second))
        table.append(label + ' & ' + ' & '.join(values) + r'\\')
    table += [r'\bottomrule', r'\end{tabular}}']
    (HERE / 'data' / 'tight-table.tex').write_text('\n'.join(table) + '\n', encoding='utf-8')

    numbers, advantages = [], []
    for task in primary['config']['tasks']:
        baseline = next(g['mean'] for g in statistics['primary']['baselines'] if g['task'] == task)
        numbers.append(r'\newcommand{\Baseline%s}{%.1f}' % (task, 100 * baseline))
    for row, family, label in [(1, 'primary', 'Primary'), (0, 'alternative', 'Alternative')]:
        value = next(g for g in statistics[family]['method_differences']
                     if g['task'] == 'ERP' and g['budget'] == 32
                     and g['first'] == 'uniform' and g['second'] == 'dct')
        mean, low, high = [100 * x for x in [value['mean'], *value['ci95']]]
        advantages.append(dict(row=row, mean=mean, minus=mean-low, plus=high-mean))
        numbers.append(r'\newcommand{\%sAdvantage}{%.2f}' % (label, mean))
    write_csv('p300-advantage.csv', ['row', 'mean', 'minus', 'plus'], advantages)
    (HERE / 'data' / 'numbers.tex').write_text('\n'.join(numbers) + '\n', encoding='utf-8')
    print('Exported measured chart inputs, uncertainty bounds and result table.')


if __name__ == '__main__':
    main()
