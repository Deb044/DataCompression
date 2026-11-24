"""Fixed, deliberately simple FFT target scores; no learned classifier."""

import numpy as np


def decode(signal, config):
    signal = np.asarray(signal, dtype=np.float64)
    centered = signal - signal.mean(axis=1, keepdims=True)
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(signal.shape[1]), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(signal.shape[1], 1 / config['sample_rate_hz'])
    scores = []
    for target in config['target_frequencies_hz']:
        bins = [int(np.argmin(np.abs(frequencies - target * harmonic))) for harmonic in config['harmonics']]
        scores.append(float(spectrum[:, bins].sum()))
    scores = np.asarray(scores)
    runner_up, best = np.sort(scores)[-2:]
    gap = (best - runner_up) / (best + runner_up + 1e-12)
    prediction = config['target_frequencies_hz'][int(np.argmax(scores))]
    return prediction, float(gap), scores


def signal_features(signal, config):
    centered = signal.astype(np.float64) - signal.mean(axis=1, keepdims=True)
    rms = np.sqrt(np.mean(centered ** 2, axis=1))
    range_over_rms = float(np.mean(np.ptp(centered, axis=1) / np.maximum(rms, 1e-12)))
    power = np.abs(np.fft.rfft(centered * np.hanning(signal.shape[1]), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(signal.shape[1], 1 / config['sample_rate_hz'])
    band = power[:, (frequencies >= 6) & (frequencies <= 40)].sum()
    _, _, scores = decode(signal, config)
    concentration = float(scores.sum() / max(float(band), 1e-12))
    return {'range_over_rms': range_over_rms, 'spectral_concentration': concentration}


def distortion(original, reconstruction):
    original = original.astype(np.float64)
    error = original - reconstruction.astype(np.float64)
    denominator = np.linalg.norm(original - original.mean(axis=1, keepdims=True))
    return {'rmse': float(np.sqrt(np.mean(error ** 2))),
            'nrmse': float(np.linalg.norm(error) / denominator) if denominator else None}
