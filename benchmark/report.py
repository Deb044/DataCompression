"""Export standalone scientific plots from measured summary JSON."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def main():
    output = ROOT/'results'/'benchmark'
    data = json.loads((output/'summary.json').read_text())
    if not data['complete']:
        raise ValueError('Do not plot incomplete comparisons')
    tasks = {'SSVEP': 'SSVEP', 'MI': 'Motor imagery', 'ERP': 'P300 detection'}
    methods = {'uniform': 'Uniform + ZIP', 'mulaw': 'Mu-law + ZIP', 'dct': 'DCT + ZIP'}
    colors = ['#267c72', '#c2603b', '#4968b1']
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    for ax, (method, title) in zip(axes, methods.items()):
        for color, (task, label) in zip(colors, tasks.items()):
            groups = sorted([g for g in data['groups'] if g['task']==task and g['method']==method and g['complete']], key=lambda g:g['budget'])
            x = [g['budget'] for g in groups]
            ax.plot(x, [100*g['balanced_accuracy_drop'] for g in groups], 'o-', color=color, label=label)
            for subject in data['config']['evaluation_subjects']:
                points = sorted([p for p in data['points'] if p['subject']==subject and p['task']==task and p['method']==method and p['feasible']], key=lambda p:p['budget'])
                ax.plot([p['budget'] for p in points], [100*p['balanced_accuracy_drop'] for p in points], color=color, alpha=0.15, linewidth=0.8)
        ax.axhline(0, color='gray', linestyle='--', linewidth=0.8)
        ax.set_xscale('log', base=2)
        ax.set_xticks([32, 64, 128, 256], ['32', '64', '128', '256'])
        ax.set_title(title)
        ax.set_xlabel('Storage cap (bytes/s/channel)')
        ax.grid(alpha=0.2)
    axes[0].set_ylabel('Balanced-accuracy loss (percentage points)')
    axes[-1].legend()
    fig.suptitle('OpenBMI: paired application sensitivity at matched byte caps')
    fig.text(0.5, 0.01, 'S03–S06 evaluation mean; faint lines show participants. Negative loss = improvement. Lines are guides between tested caps.', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(output/'task_curves.png', dpi=170)
    fig.savefig(output/'task_curves.pdf')
    plt.close(fig)
    fig, axes = plt.subplots(1, 4, figsize=(15, 4), sharey=True)
    color_limit = max(1, max(abs(100*g['balanced_accuracy_drop']) for g in data['groups'] if g['complete']))
    for ax, budget in zip(axes, data['config']['budgets_bytes_per_second_channel']):
        matrix = np.array([[100*next(g['balanced_accuracy_drop'] for g in data['groups'] if g['task']==task and g['method']==method and g['budget']==budget and g['complete']) for method in methods] for task in tasks])
        image = ax.imshow(matrix, cmap='RdBu_r', vmin=-color_limit, vmax=color_limit)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f'{matrix[i,j]:.1f}', ha='center', va='center')
        ax.set_xticks(range(3), ['Uniform', 'Mu-law', 'DCT'], rotation=30)
        ax.set_yticks(range(3), list(tasks.values()))
        ax.set_title(f'{budget} bytes/s/channel')
    fig.suptitle('Does the largest mean loss belong to the same application across codecs?')
    fig.colorbar(image, ax=axes.tolist(), label='Balanced-accuracy loss (percentage points)', shrink=0.8)
    fig.savefig(output/'ranking.png', dpi=170, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
