"""Fixed, lightweight alternatives for the decoder-sensitivity check."""

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .decoders import ERPDecoder, bandpass


class SpectralDecoder:
    """Score flicker harmonics relative to their local spectral background."""

    def __init__(self, config):
        self.rate = config['sample_rate_hz']
        self.channels = [config['channels'].index(c) for c in ['O1', 'Oz', 'O2']]
        self.targets = [12, 8.57, 6.67, 5.45]

    def fit(self, x, y):
        self.frequencies = np.fft.rfftfreq(x.shape[-1], 1 / self.rate)
        return self

    def predict(self, x):
        signal = x[:, self.channels].astype(float)
        signal -= signal.mean(axis=-1, keepdims=True)
        power = np.abs(np.fft.rfft(signal * np.hanning(signal.shape[-1]), axis=-1)) ** 2
        power = power.mean(axis=1)
        scores = []
        for target in self.targets:
            harmonic_scores = []
            for harmonic in [1, 2, 3]:
                distance = np.abs(self.frequencies - target * harmonic)
                peak = power[:, distance <= 0.25].mean(axis=1)
                background = power[:, (distance >= 0.75) & (distance <= 1.5)].mean(axis=1)
                harmonic_scores.append(peak / np.maximum(background, 1e-20))
            scores.append(np.mean(harmonic_scores, axis=0))
        scores = np.stack(scores, axis=1)
        return scores.argmax(axis=1) + 1, scores


class BandpowerDecoder:
    """Channel log-power in mu/beta bands, without learned spatial filters."""

    def __init__(self, config):
        self.rate = config['sample_rate_hz']
        names = ['C3', 'Cz', 'C4', 'FC1', 'FC2', 'CP1', 'CP2']
        self.channels = [config['channels'].index(c) for c in names]

    def features(self, x):
        signal = x[:, self.channels].astype(float)
        return np.concatenate([
            np.log(np.maximum(np.var(bandpass(signal, low, high, self.rate), axis=-1), 1e-20))
            for low, high in [(8, 12), (13, 30)]
        ], axis=1)

    def fit(self, x, y):
        self.classifier = make_pipeline(
            StandardScaler(),
            LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto'),
        ).fit(self.features(x), y)
        return self

    def predict(self, x):
        features = self.features(x)
        return self.classifier.predict(features), self.classifier.decision_function(features)


class LogisticERPDecoder(ERPDecoder):
    """Keep the original response features; change the decision boundary."""

    def fit(self, x, y):
        self.classifier = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1, class_weight='balanced', max_iter=1000, random_state=321),
        ).fit(self.features(x), y)
        return self


def make_alternative_decoder(task, config):
    classes = {'SSVEP': SpectralDecoder, 'MI': BandpowerDecoder, 'ERP': LogisticERPDecoder}
    return classes[task](config)
