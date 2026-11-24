"""Checks for scientific failure modes: bit packing, fidelity and fixed decoding."""

import unittest
import numpy as np

from .analysis import gap_analysis, roc_auc, summarize_rows
from .codec import HEADER, encode_payload, decode_payload, make_archive, read_archive, pack_codes, unpack_codes
from .decoder import decode, distortion


class CodecTests(unittest.TestCase):
    def test_arbitrary_bit_depths_and_padding(self):
        rng = np.random.default_rng(42)
        for bits in range(1, 17):
            codes = rng.integers(0, 2 ** bits, size=37, dtype=np.uint32)
            packed = pack_codes(codes, bits)
            self.assertEqual(len(packed), (37 * bits + 7) // 8)
            np.testing.assert_array_equal(unpack_codes(packed, bits, 37), codes)

    def test_self_contained_reconstruction_and_uniform_error_bound(self):
        rng = np.random.default_rng(12)
        signal = rng.normal(size=(3, 101)).astype('<f4')
        for bits in [2, 4, 6, 8, 12, 16]:
            for method in ['uniform', 'mulaw']:
                payload = encode_payload(signal, bits, method)
                self.assertEqual(len(payload), HEADER.size + 24 + (signal.size * bits + 7) // 8)
                recovered = read_archive(make_archive(payload))
                self.assertEqual(recovered.shape, signal.shape)
                if method == 'uniform':
                    bound = np.ptp(signal.astype(float), axis=1)[:, None] / (2 ** bits - 1) / 2
                    self.assertTrue(np.all(np.abs(recovered - signal) <= bound + 1e-6))
                self.assertTrue(np.isfinite(recovered).all())

    def test_float32_is_byte_exact_and_constant_channels_survive(self):
        signal = np.array([[0, -0.0, 1.125, -2.5], [3, 3, 3, 3]], dtype='<f4')
        recovered = read_archive(make_archive(encode_payload(signal)))
        self.assertEqual(recovered.tobytes(), signal.tobytes())
        for method in ['uniform', 'mulaw']:
            recovered = decode_payload(encode_payload(signal, 2, method))
            np.testing.assert_array_equal(recovered[1], signal[1])

    def test_truncation_and_bad_header_are_rejected(self):
        payload = encode_payload(np.ones((3, 5), dtype='<f4'), 6, 'uniform')
        for broken in [payload[:5], b'NOPE' + payload[4:], payload[:-1]]:
            with self.assertRaises(ValueError):
                decode_payload(broken)


class AnalysisTests(unittest.TestCase):
    def test_fft_finds_known_tones_and_survives_archive_roundtrip(self):
        config = {'sample_rate_hz': 250, 'target_frequencies_hz': [9, 11, 13, 15], 'harmonics': [1, 2]}
        t = np.arange(1000) / 250
        for frequency in config['target_frequencies_hz']:
            signal = np.tile(np.sin(2 * np.pi * frequency * t), (3, 1)).astype('<f4')
            prediction, gap, _ = decode(signal, config)
            self.assertEqual(prediction, frequency)
            self.assertGreater(gap, 0.99)
            recovered = read_archive(make_archive(encode_payload(signal, 8, 'uniform')))
            self.assertEqual(decode(recovered, config)[0], frequency)
            self.assertLess(distortion(signal, recovered)['nrmse'], 0.01)

    def test_auc_direction_ties_and_undefined_outcomes(self):
        self.assertEqual(roc_auc([False, True], [0, 1]), 1)
        self.assertEqual(roc_auc([False, True], [1, 0]), 0)
        self.assertEqual(roc_auc([False, True], [1, 1]), 0.5)
        self.assertIsNone(roc_auc([False, False], [0, 1]))

    def test_preserved_wrong_decisions_are_not_counted_as_accuracy(self):
        row = {'original_correct': False, 'correct': False, 'flipped': False,
               'archive_bytes': 100, 'payload_bytes': 90, 'raw_float32_bytes': 300, 'nrmse': 0.2}
        result = summarize_rows([row])
        self.assertEqual(result['accuracy'], 0)
        self.assertEqual(result['flip_rate'], 0)
        self.assertIsNone(result['correct_to_wrong_rate'])
        self.assertEqual(result['transitions']['wrong_to_wrong'], 1)

    def test_shuffled_control_preserves_participant_confounding(self):
        # All flips happen in one participant. A global shuffle would wrongly
        # erase that confound and create a misleading 0.5-AUC comparison.
        rows, originals = [], []
        for subject, flipped, gap in [(1, False, 0.9), (2, True, 0.1)]:
            for block in range(6):
                identity = f'{subject}-{block}'
                rows.append({'id': identity, 'subject': subject, 'target_hz': 9,
                             'method': 'uniform', 'bits': 2, 'gap': gap,
                             'flipped': flipped, 'original_correct': True,
                             'correct': not flipped, 'archive_bytes': 100,
                             'payload_bytes': 90, 'raw_float32_bytes': 300, 'nrmse': 0.1})
                originals.append({'id': identity, 'subject': subject,
                                  'range_over_rms': 1, 'spectral_concentration': 0.5})
        config = {'evaluation_subjects': [1, 2], 'bit_depths': [2],
                  'primary_method': 'uniform', 'seed': 321, 'permutations': 10}
        result = gap_analysis(rows, originals, [0.3, 0.6], config)[0]
        self.assertEqual(result['predictor_auc']['low_gap'], 1)
        self.assertEqual(result['shuffled_auc_mean'], 1)
        self.assertEqual(result['permutation_p_one_sided'], 1)


if __name__ == '__main__':
    unittest.main()
