"""Readable single-panel figures for the public experiment narrative.

These are new views of the recorded results, not new experiments.
All three figures share the same vertical scale for direct visual comparison.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    output = Path(__file__).resolve().parent.parent / 'results' / 'benchmark'
    data = json.loads((output / 'summary.json').read_text())
    if not data['complete']:
        raise ValueError('Do not illustrate incomplete comparisons')
    tasks = {'SSVEP': 'Flickering targets (SSVEP)', 'MI': 'Imagined movement', 'ERP': 'Target flashes (P300)'}
    methods = {'uniform': 'Uniform quantization + ZIP', 'mulaw': 'Mu-law quantization + ZIP', 'dct': 'DCT-based compression + ZIP'}
    colors = ['#267c72', '#c2603b', '#4968b1']
    values = [100 * g['balanced_accuracy_drop'] for g in data['groups'] if g['complete']]
    limits = (min(-2, min(values)-1), max(values)+1.5)
    with plt.rc_context({'font.size': 12}):
        for method, title in methods.items():
            fig, ax = plt.subplots(figsize=(9, 5.3))
            for (task, label), color in zip(tasks.items(), colors):
                groups = sorted([g for g in data['groups'] if g['task']==task and g['method']==method and g['complete']], key=lambda g:g['budget'])
                ax.plot([g['budget'] for g in groups], [100*g['balanced_accuracy_drop'] for g in groups], 'o-', label=label, color=color, linewidth=2)
            ax.axhline(0, linestyle='--', linewidth=1, color='gray')
            ax.set_xscale('log', base=2)
            ax.set_xticks([32, 64, 128, 256], ['32', '64', '128', '256'])
            ax.set_ylim(*limits)
            ax.set_xlabel('Storage allowance (bytes per second per channel)')
            ax.set_ylabel('Score lost (percentage points)')
            ax.set_title(title, pad=14)
            ax.grid(alpha=0.2)
            ax.legend(fontsize=10, loc='upper right')
            fig.text(0.5, 0.015, 'Four-person evaluation mean. Lower is better; below zero means improvement.\nPoints are measurements; lines are guides. Same vertical scale in all three plots.', ha='center', fontsize=10)
            fig.tight_layout(rect=[0, 0.09, 1, 1])
            fig.savefig(output / f'story_{method}.png', dpi=160)
            plt.close(fig)


if __name__ == '__main__':
    main()
