"""Export presentation figures from measured results and participant intervals."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TASKS = {'SSVEP': 'Flickering targets (SSVEP)', 'MI': 'Imagined movement', 'ERP': 'Target flashes (P300)'}
METHODS = {'uniform': 'Uniform quantization + ZIP', 'mulaw': 'Mu-law quantization + ZIP', 'dct': 'DCT-based compression + ZIP'}
COLORS = ['#267c72', '#c2603b', '#4968b1']


def select(groups, task, method):
    return sorted([g for g in groups if g['task'] == task and g['method'] == method],
                  key=lambda g: g['budget'])


def curve(ax, groups, method):
    for (task, label), color in zip(TASKS.items(), COLORS):
        points = select(groups, task, method)
        x = [g['budget'] for g in points]
        y = [100 * g['mean'] for g in points]
        bounds = np.array([g['ci95'] for g in points]) * 100
        ax.plot(x, y, 'o-', color=color, linewidth=2, label=label)
        ax.fill_between(x, bounds[:, 0], bounds[:, 1], color=color, alpha=0.13)
    ax.axhline(0, linestyle='--', linewidth=1, color='gray')
    ax.set_xscale('log', base=2)
    ax.set_xticks([32, 64, 128, 256], ['32', '64', '128', '256'])
    ax.set_xlabel('Storage allowance (bytes/s/channel)')
    ax.set_title(METHODS[method], pad=14)
    ax.grid(alpha=0.2)


def main():
    output = ROOT / 'results' / 'benchmark'
    primary = json.loads((output / 'summary.json').read_text())
    statistics = json.loads((output / 'statistics.json').read_text())
    if not primary['complete']:
        raise ValueError('Do not plot incomplete comparisons')
    groups = statistics['primary']['groups']
    count = len(statistics['participants'])
    intervals = np.array([g['ci95'] for g in groups]) * 100
    limits = (min(-2, intervals.min() - 1), intervals.max() + 1)
    note = (f'{count} new participants, session 1. Shading: pointwise 95% participant-bootstrap intervals.\n'
            'Lower is better; below zero means improvement. Lines join measured settings only.')
    with plt.rc_context({'font.size': 12}):
        for method in METHODS:
            fig, ax = plt.subplots(figsize=(9, 5.6))
            curve(ax, groups, method)
            ax.set_ylim(*limits)
            ax.set_ylabel('Score lost (percentage points)')
            ax.legend(fontsize=10, loc='upper right')
            fig.text(0.5, 0.015, note, ha='center', fontsize=10)
            fig.tight_layout(rect=[0, 0.09, 1, 1])
            fig.savefig(output / f'story_{method}.png', dpi=160)
            plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(16, 5.4), sharey=True)
        for ax, method in zip(axes, METHODS):
            curve(ax, groups, method)
            ax.set_ylim(*limits)
        axes[0].set_ylabel('Score lost (percentage points)')
        axes[-1].legend(fontsize=9)
        fig.text(0.5, 0.01, note, ha='center', fontsize=10)
        fig.tight_layout(rect=[0, 0.12, 1, 1])
        fig.savefig(output / 'task_curves.png', dpi=160)
        fig.savefig(output / 'task_curves.pdf')
        plt.close(fig)

        fig, axes = plt.subplots(1, 4, figsize=(15, 4), sharey=True)
        color_limit = max(1, max(abs(100 * g['mean']) for g in groups))
        for ax, budget in zip(axes, primary['config']['budgets_bytes_per_second_channel']):
            matrix = np.array([[100 * next(g['mean'] for g in groups
                               if g['task'] == task and g['method'] == method and g['budget'] == budget)
                               for method in METHODS] for task in TASKS])
            image = ax.imshow(matrix, cmap='RdBu_r', vmin=-color_limit, vmax=color_limit)
            for row, column in np.ndindex(matrix.shape):
                ax.text(column, row, f'{matrix[row, column]:.2f}', ha='center', va='center')
            ax.set_xticks(range(3), ['Uniform', 'Mu-law', 'DCT'], rotation=30)
            ax.set_yticks(range(3), ['SSVEP', 'Motor imagery', 'P300'])
            ax.set_title(f'{budget} bytes/s/channel')
        fig.suptitle(f'Mean score loss across {count} new participants; primary decoders')
        fig.colorbar(image, ax=axes.tolist(), label='Score lost (percentage points)', shrink=0.8)
        fig.savefig(output / 'ranking.png', dpi=160, bbox_inches='tight')
        plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharey=True)
        subjects = statistics['participants']
        for ax, method in zip(axes, METHODS):
            for column, (task, color) in enumerate(zip(TASKS, COLORS)):
                points = [next(p['balanced_accuracy_drop'] * 100 for p in primary['points']
                               if p['subject'] == subject and p['task'] == task
                               and p['method'] == method and p['budget'] == 32) for subject in subjects]
                ax.scatter(column + np.linspace(-0.12, 0.12, len(points)), points,
                           color=color, alpha=0.7, s=28)
                ax.scatter(column, np.mean(points), color='black', marker='D', s=45, zorder=4)
            ax.axhline(0, linestyle='--', color='gray', linewidth=1)
            ax.set_xticks(range(3), ['SSVEP', 'Motor imagery', 'P300'])
            ax.set_title(METHODS[method], fontsize=12)
            ax.grid(axis='y', alpha=0.2)
        axes[0].set_ylabel('Score lost (percentage points)')
        fig.suptitle('Do the averages describe every person? Tightest allowance: 32 bytes/s/channel')
        fig.text(0.5, 0.015, 'Each colored dot is one participant; black diamonds are means. Horizontal offsets separate people only.',
                 ha='center', fontsize=10)
        fig.tight_layout(rect=[0, 0.06, 1, 0.95])
        fig.savefig(output / 'participants.png', dpi=160)
        plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharey=True)
        for ax, task in zip(axes, TASKS):
            for offset, family, label, color in [(-0.18, 'primary', 'Primary decoder', '#267c72'),
                                                 (0.18, 'alternative', 'Alternative decoder', '#c2603b')]:
                selected = [next(g for g in statistics[family]['groups']
                                 if g['task'] == task and g['method'] == method and g['budget'] == 32)
                            for method in METHODS]
                means = np.array([g['mean'] for g in selected]) * 100
                bounds = np.array([g['ci95'] for g in selected]) * 100
                ax.bar(np.arange(3) + offset, means, width=0.34, color=color, label=label,
                       yerr=np.stack([means - bounds[:, 0], bounds[:, 1] - means]), capsize=3)
            ax.set_xticks(range(3), ['Uniform', 'Mu-law', 'DCT'])
            ax.set_title(TASKS[task], fontsize=12)
            ax.axhline(0, color='gray', linewidth=1)
            ax.grid(axis='y', alpha=0.2)
        axes[0].set_ylabel("Score lost from each decoder's own baseline (pp)")
        axes[-1].legend(fontsize=10)
        fig.suptitle('Change the decision system; keep people and compressed recordings fixed')
        fig.text(0.5, 0.015, '32 bytes/s/channel. Error bars: pointwise 95% participant-bootstrap intervals. Baselines differ by decoder.',
                 ha='center', fontsize=10)
        fig.tight_layout(rect=[0, 0.06, 1, 0.95])
        fig.savefig(output / 'decoder_check.png', dpi=160)
        plt.close(fig)

        fig, axes = plt.subplots(1, 3, figsize=(16, 5.4), sharey=True)
        for ax, method in zip(axes, METHODS):
            for (task, label), color in zip(TASKS.items(), COLORS):
                selected = select(primary['groups'], task, method)
                ax.plot([g['rate'] for g in selected],
                        [100 * g['balanced_accuracy_drop'] for g in selected], 'o-', color=color, label=label)
            ax.set_xscale('log', base=2)
            ax.set_xlabel('Actual mean storage rate (bytes/s/channel)')
            ax.set_title(METHODS[method], fontsize=12)
            ax.axhline(0, linestyle='--', color='gray', linewidth=1)
            ax.grid(alpha=0.2)
        axes[0].set_ylabel('Score lost (percentage points)')
        axes[-1].legend(fontsize=9)
        fig.text(0.5, 0.015, 'Each point is a participant mean at one tested allowance. Actual sizes can differ under the same cap.',
                 ha='center', fontsize=10)
        fig.tight_layout(rect=[0, 0.06, 1, 1])
        fig.savefig(output / 'actual_rates.png', dpi=160)
        plt.close(fig)


if __name__ == '__main__':
    main()
