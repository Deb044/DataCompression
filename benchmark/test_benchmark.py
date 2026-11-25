"""Checks for fidelity, actual byte caps, label isolation and split leakage."""

import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from . import codec
from .decoders import SSVEPDecoder
from .run import split_recording

CONFIG = json.loads(Path(__file__).with_name('config.json').read_text())


class BenchmarkTests(unittest.TestCase):
    def test_arbitrary_bit_packing_and_padding(self):
        rng = np.random.default_rng(3)
        for bits in range(1, 17):
            codes = rng.integers(0, 2**bits, 37, dtype=np.uint32)
            np.testing.assert_array_equal(codec.unpack(codec.pack(codes, bits), bits, len(codes)), codes)
        with self.assertRaises(ValueError):
            codec.unpack(b'\xff', 1, 1)

    def test_self_contained_reconstruction_and_error_bound(self):
        x = np.random.default_rng(1).normal(size=(12, 128)).astype(np.float32)
        np.testing.assert_array_equal(codec.decode(codec.encode(x, 'float32')), x)
        for method in ['uniform', 'mulaw', 'dct']:
            result = codec.decode(codec.encode(x, method, 12, 128))
            self.assertEqual(result.shape, x.shape)
            self.assertTrue(np.isfinite(result).all())
            self.assertLess(np.sqrt(np.mean((x-result)**2)), 0.01)
        result = codec.decode(codec.encode(x, 'uniform', 4))
        bound = np.max(np.abs(x), axis=1)[:, None] / 15
        self.assertTrue(np.all(np.abs(x-result) <= bound+1e-6))

    def test_complete_corpus_obeys_caps_and_roundtrips(self):
        config = copy.deepcopy(CONFIG)
        x = np.random.default_rng(2).normal(size=(12, 128)).astype(np.float32)
        header = codec.corpus_header(12, 128, config)
        for method in config['methods']:
            selected = codec.choose_frames(x, method, config, overhead=4+len(header))
            for budget, choice in selected.items():
                if choice is None:
                    continue
                data = header + struct.pack('<I', choice['bytes']) + choice['data']
                self.assertLessEqual(len(data), budget*12)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)/'frames.eegpack'
                    path.write_bytes(data)
                    np.testing.assert_array_equal(codec.read_corpus(path), choice['recovered'])

    def test_no_overlapping_epochs_across_boundary(self):
        events = np.arange(0, 4000, 100)
        labels = np.tile([1, 2], 20)
        signal = np.ones((12, 5000), dtype=np.float32)
        _, _, _, _, _, _, split = split_recording(signal, events, labels, 'ERP', CONFIG)
        self.assertLess(split['last_training_epoch_end'], split['first_test_epoch_start'])

    def test_cca_recognizes_known_frequencies_without_labels(self):
        t = np.arange(512)/128
        examples = np.array([np.tile(np.sin(2*np.pi*f*t), (12, 1)) for f in [12, 8.57, 6.67, 5.45]])
        decoder = SSVEPDecoder(CONFIG).fit(examples, np.array([4, 3, 2, 1]))
        predictions, _ = decoder.predict(examples)
        np.testing.assert_array_equal(predictions, [1, 2, 3, 4])
        _, scores = decoder.predict(np.zeros_like(examples))
        np.testing.assert_array_equal(scores, np.zeros((4, 4)))


if __name__ == '__main__':
    unittest.main()
