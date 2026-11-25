"""Three small original-data decoders, frozen during all compression sweeps."""

import numpy as np
from scipy.linalg import eigh
from scipy.signal import butter, sosfiltfilt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def epochs(signal, events, labels, samples):
    valid = (events >= 0) & (events + samples <= signal.shape[1])
    x = np.stack([signal[:, t:t+samples] for t in events[valid]])
    return x, labels[valid], events[valid]


def bandpass(x, low, high, rate):
    return sosfiltfilt(butter(4, [low, high], btype='bandpass', fs=rate, output='sos'), x, axis=-1)


class SSVEPDecoder:
    """CCA against sine/cosine templates, three harmonics, occipital channels."""
    def __init__(self, config):
        self.rate = config['sample_rate_hz']
        self.channels = [config['channels'].index(c) for c in ['O1', 'Oz', 'O2']]
        self.frequencies = [12, 8.57, 6.67, 5.45]  # Source labels 1, 2, 3, 4.

    def fit(self, x, y):
        t = np.arange(x.shape[-1]) / self.rate
        self.references = []
        for f in self.frequencies:
            r = np.array([function(2*np.pi*f*h*t) for h in [1, 2, 3] for function in [np.sin, np.cos]]).T
            self.references.append(np.linalg.qr(r-r.mean(axis=0), mode='reduced')[0])
        return self

    def predict(self, x):
        scores = []
        for trial in x[:, self.channels, :]:
            centered = trial.T - trial.T.mean(axis=0)
            q = np.linalg.qr(centered, mode='reduced')[0]
            scores.append([np.linalg.svd(q.T @ r, compute_uv=False)[0] for r in self.references])
        return np.argmax(scores, axis=1) + 1, np.asarray(scores)


class MotorDecoder:
    """Trace-normalized, regularized CSP plus shrinkage LDA."""
    def __init__(self, config):
        self.rate = config['sample_rate_hz']
        self.channels = [config['channels'].index(c) for c in ['C3', 'Cz', 'C4', 'FC1', 'FC2', 'CP1', 'CP2']]

    def prepare(self, x):
        return bandpass(x[:, self.channels, :].astype(float), 8, 30, self.rate)

    def features(self, x):
        projected = np.einsum('fc,nct->nft', self.filters, self.prepare(x))
        variance = np.var(projected, axis=-1)
        return np.log(np.maximum(variance / np.maximum(variance.sum(axis=1, keepdims=True), 1e-20), 1e-20))

    def fit(self, x, y):
        filtered = self.prepare(x)
        covs = []
        for label in [1, 2]:
            covariance = np.array([trial @ trial.T for trial in filtered[y == label]])
            covariance /= np.trace(covariance, axis1=1, axis2=2)[:, None, None]
            mean = covariance.mean(axis=0)
            covs.append(0.95*mean + 0.05*np.eye(len(self.channels))/len(self.channels))
        _, vectors = eigh(covs[0], covs[0] + covs[1])
        self.filters = vectors[:, [0, 1, -2, -1]].T
        self.classifier = LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto').fit(self.features(x), y)
        return self

    def predict(self, x):
        features = self.features(x)
        return self.classifier.predict(features), self.classifier.decision_function(features)


class ERPDecoder:
    """Single-flash target/non-target classification; not spelling accuracy."""
    def __init__(self, config):
        self.rate = config['sample_rate_hz']

    def features(self, x):
        filtered = bandpass(x.astype(float), 0.5, 12, self.rate)
        # Six 100 ms bins from 0.1 to 0.7 seconds, all shared-montage channels.
        return np.stack([filtered[:, :, round(t*self.rate):round((t+0.1)*self.rate)].mean(axis=-1)
                         for t in np.arange(0.1, 0.7, 0.1)], axis=-1).reshape(len(x), -1)

    def fit(self, x, y):
        self.classifier = make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(
            solver='lsqr', shrinkage='auto', priors=[0.5, 0.5])).fit(self.features(x), y)
        return self

    def predict(self, x):
        features = self.features(x)
        return self.classifier.predict(features), self.classifier.decision_function(features)


def make_decoder(task, config):
    return {'SSVEP': SSVEPDecoder, 'MI': MotorDecoder, 'ERP': ERPDecoder}[task](config)
