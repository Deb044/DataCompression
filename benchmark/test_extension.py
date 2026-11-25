"""Tests that target paired inference and the new spectral decoder."""

import unittest
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
import tempfile

import numpy as np

from .alternative_decoders import SpectralDecoder
from .data import download_range
from .statistics import analyze
from .test_benchmark import CONFIG


class ExtensionTests(unittest.TestCase):
    def test_short_download_resumes_and_wrong_range_is_rejected(self):
        class Response(BytesIO):
            status = 206

            def __init__(self, data, content_range):
                super().__init__(data)
                self.headers = {'Content-Range': content_range}

        with tempfile.TemporaryDirectory() as folder:
            partial = Path(folder) / 'source.part'
            responses = [Response(b'ab', 'bytes 0-4/5'), Response(b'cde', 'bytes 2-4/5')]
            with patch('urllib.request.urlopen', side_effect=responses) as request:
                download_range('https://example.com/source', partial, b'h' * 128, 0, 4, 5)
            self.assertEqual(partial.read_bytes(), b'h' * 128 + b'abcde')
            self.assertEqual(request.call_args_list[1].args[0].get_header('Range'), 'bytes=2-4')
            invalid = Path(folder) / 'invalid.part'
            with patch('urllib.request.urlopen', return_value=Response(b'abcde', 'bytes 1-5/6')):
                with self.assertRaises(ValueError):
                    download_range('https://example.com/source', invalid, b'h' * 128, 0, 4, 5)
            self.assertEqual(invalid.stat().st_size, 128)

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
