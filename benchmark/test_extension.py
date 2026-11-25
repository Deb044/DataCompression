"""Tests that target paired inference and the new spectral decoder."""

import unittest

import numpy as np

from .alternative_decoders import SpectralDecoder
from .statistics import analyze
from .test_benchmark import CONFIG


class ExtensionTests(unittest.TestCase):
    def test_spectral_decoder_and_constant_input(self):
        time = np.arange(512) / 128
        x = np.array([np.tile(np.sin(2 * np.pi * f * time), (12, 1))
                      for f in [12, 8.57, 6.67, 5.45]])
        decoder = SpectralDecoder(CONFIG).fit(x, [1, 2, 3, 4])
        np.testing.assert_array_equal(decoder.predict(x)[0], [1, 2, 3, 4])
        self.assertTrue(np.isfinite(decoder.predict(np.zeros_like(x))[1]).all())

    def test_bootstrap_keeps_task_pairs_and_splits_tie_credit(self):
        config = dict(evaluation_subjects=[7, 8, 9], tasks=['A', 'B', 'C'],
                      methods=['uniform'], budgets_bytes_per_second_channel=[32, 64])
        points, baselines = [], []
        for subject, offset in zip(config['evaluation_subjects'], [0, 0.1, 0.2]):
            for task, difference in zip(config['tasks'], [0, 0.02, 0.04]):
                baselines.append(dict(subject=subject, task=task, balanced_accuracy=0.8))
                for budget in [32, 64]:
                    points.append(dict(subject=subject, task=task, method='uniform', budget=budget,
                                       split='evaluation', feasible=True,
                                       balanced_accuracy_drop=offset+difference if budget == 32 else 0))
        draws = np.random.default_rng(2).integers(3, size=(1000, 3))
        result = analyze(dict(config=config, points=points, baselines=baselines), draws)
        difference = next(d for d in result['task_differences']
                          if d['first'] == 'A' and d['second'] == 'B' and d['budget'] == 32)
        np.testing.assert_allclose(difference['ci95'], [-0.02, -0.02])
        tied = [g for g in result['groups'] if g['budget'] == 64]
        np.testing.assert_allclose([g['largest_loss_share'] for g in tied], [1/3]*3)


if __name__ == '__main__':
    unittest.main()
