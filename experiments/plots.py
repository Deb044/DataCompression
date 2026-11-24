"""Export scientific figures from measured outputs, not illustrative values."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

COLORS = {'uniform': '#087f83', 'mulaw': '#c05a3a', 'float32': '#25394b'}


def save(figure, output, name):
    figure.savefig(output / f'{name}.png', dpi=180, bbox_inches='tight')
    plt.close(figure)


def render_figures(summary, examples, output):
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.facecolor': 'white'})
    conditions = [row for row in summary['conditions'] if row['split'] == 'evaluation']
    baseline = next(row for row in conditions if row['method'] == 'float32')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), layout='constrained')
    for method in ['uniform', 'mulaw']:
        selected = [row for row in conditions if row['method'] == method]
        x = [row['archive_bytes_per_second_channel'] for row in selected]
        for ax, field in zip(axes, ['accuracy', 'mean_nrmse']):
            y = [row[field] for row in selected]
            ax.plot(x, y, 'o-', color=COLORS[method], label=method)
            for row, xx, yy in zip(selected, x, y):
                if row['bits'] in [2, 4, 8]:
                    offset = (3, 8) if method == 'uniform' else (3, -15)
                    ax.annotate(str(row['bits']) + 'b', (xx, yy), xytext=offset, textcoords='offset points', fontsize=8)
            ax.set_xlabel('Actual ZIP bytes / second / channel')
            ax.grid(alpha=0.2)
    axes[0].axhline(baseline['accuracy'], color=COLORS['float32'], linestyle='--', label='Original decision accuracy')
    axes[0].axhline(0.25, color='gray', linestyle=':', label='4-class chance')
    axes[0].set(ylabel='Target recognition accuracy', ylim=(0, 1.08), title='Decisions after reconstruction')
    axes[1].set(ylabel='Mean normalized RMSE', title='Waveform distortion')
    axes[0].legend(fontsize=8, loc='lower right')
    axes[1].legend(fontsize=8)
    fig.suptitle('Six experienced evaluation participants; 144 paired four-second trials', fontsize=11)
    save(fig, output, 'precision')

    gaps = summary['gap_analysis']
    primary_bits = summary['provenance']['configuration']['primary_bit_depth']
    primary = next(row for row in gaps if row['bits'] == primary_bits)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
    for group, color in [('low', '#c05a3a'), ('middle', '#6571a0'), ('high', '#087f83')]:
        axes[0].plot(range(len(gaps)), [row['groups'][group]['flip_rate'] for row in gaps], 'o-', label=group + ' gap', color=color)
    axes[0].set_xticks(range(len(gaps)), [row['bits'] for row in gaps])
    axes[0].set(xlabel='Bits per sample (uniform quantization)', ylabel='Prediction flip rate', ylim=(-0.02, 1.02), title='Groups fixed using development participants')
    axes[0].legend(fontsize=8)
    groups = ['low', 'middle', 'high']
    axes[1].bar(groups, [primary['groups'][group]['flip_rate'] or 0 for group in groups], color=['#c05a3a', '#6571a0', '#087f83'])
    for i, group in enumerate(groups):
        n = primary['groups'][group]['n']
        axes[1].text(i, (primary['groups'][group]['flip_rate'] or 0) + 0.025, f'n={n}', ha='center')
    axes[1].set(ylabel='Prediction flip rate', ylim=(0, 1.08), title=f'Prespecified primary condition: {primary_bits} bits')
    for ax in axes: ax.grid(axis='y', alpha=0.2)
    save(fig, output, 'gap')

    fig, ax = plt.subplots(figsize=(8, 3.9), layout='constrained')
    labels = ['Low score gap', 'Range / RMS', 'Low spectral\nconcentration', 'Shuffled gap\n(null mean)']
    values = list(primary['predictor_auc'].values()) + [primary['shuffled_auc_mean']]
    if all(value is None for value in values):
        ax.text(0.5, 0.5, 'AUC undefined: only one outcome class at this precision', ha='center', transform=ax.transAxes)
    else:
        ax.bar(labels, [value or 0 for value in values], color=['#087f83', '#6571a0', '#c05a3a', '#a9b2b9'])
        interval = primary['shuffled_auc_95_range']
        if interval is not None:
            ax.vlines(3, interval[0], interval[1], color='#25394b', linewidth=3, label='95% shuffled null range')
        ax.axhline(0.5, linestyle=':', color='gray')
        ax.set(ylabel='Failure-prediction ROC AUC', ylim=(0, 1.05))
        ax.legend(fontsize=8)
    ax.set_title(f'Uniform {primary_bits}-bit: {primary["failures"]}/{primary["n"]} predictions changed')
    save(fig, output, 'predictors')

    example = examples[0]  # First target of first evaluation block, not selected for effect.
    condition = next(row for row in example['conditions'] if row['method'] == 'uniform' and row['bits'] == primary_bits)
    original, recovered = np.array(example['original']), np.array(condition['reconstruction'])
    fs = summary['provenance']['configuration']['sample_rate_hz']
    t = np.arange(len(original)) / fs
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.5), layout='constrained')
    axes[0].plot(t, original, color=COLORS['uniform'], label='Original Oz')
    axes[0].plot(t, recovered, color=COLORS['mulaw'], linewidth=0.8, alpha=0.8, label=f'Reconstructed ({primary_bits} bits)')
    axes[0].set(xlabel='Time within stored segment (s)', ylabel='Dataset amplitude units')
    axes[0].legend(fontsize=8)
    f = np.fft.rfftfreq(len(original), 1 / fs)
    for values, label, color in [(original, 'Original', COLORS['uniform']), (recovered, 'Reconstructed', COLORS['mulaw'])]:
        power = np.abs(np.fft.rfft((values - values.mean()) * np.hanning(len(values)))) ** 2
        axes[1].plot(f, power, label=label, color=color, linewidth=1)
    axes[1].set(xlim=(6, 35), xlabel='Frequency (Hz)', ylabel='FFT power (arbitrary units)')
    fig.suptitle(f'Predetermined example: {example["id"]}, target {example["target_hz"]} Hz; not a representative-effect claim', fontsize=10)
    save(fig, output, 'example')
