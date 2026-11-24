"""A tiny self-contained EEG payload, stored in a real DEFLATE ZIP archive.

Payload: magic, method, bits, channel count, sample count, then optional
float32 channel endpoints and packed codes. Labels and decoder scores are
never stored in the payload. Reconstruction uses only the archived bytes.
"""

import io
import struct
import zipfile

import numpy as np

HEADER = struct.Struct('<4sBBHI')
MAGIC = b'EEG1'
METHODS = {'float32': 0, 'uniform': 1, 'mulaw': 2}
MU = 255  # Part of format version EEG1; not an unstored run-time setting.


def pack_codes(codes, bits):
    """Pack MSB-first codes; pad the last byte with zero bits."""
    codes = np.asarray(codes, dtype=np.uint32).ravel()
    if not 1 <= bits <= 16 or np.any(codes >= 2 ** bits):
        raise ValueError('Invalid bit depth or code outside its range')
    binary = (codes[:, None] >> np.arange(bits - 1, -1, -1)) & 1
    return np.packbits(binary.astype(np.uint8).ravel(), bitorder='big').tobytes()


def unpack_codes(data, bits, count):
    expected = (count * bits + 7) // 8
    if len(data) != expected:
        raise ValueError('Packed code length does not match the declared shape')
    binary = np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder='big')
    if np.any(binary[count * bits:]):
        raise ValueError('Nonzero padding bits')
    binary = binary[:count * bits].reshape(count, bits).astype(np.uint32)
    return binary @ (1 << np.arange(bits - 1, -1, -1, dtype=np.uint32))


def encode_payload(signal, bits=32, method='float32'):
    signal = np.asarray(signal, dtype='<f4')
    if signal.ndim != 2 or not signal.size or not np.isfinite(signal).all():
        raise ValueError('Expected a nonempty finite channels-by-samples array')
    channels, samples = signal.shape
    if method not in METHODS:
        raise ValueError(f'Unknown method: {method}')
    if method == 'float32':
        if bits != 32:
            raise ValueError('The lossless representation uses 32-bit floats')
        return HEADER.pack(MAGIC, METHODS[method], bits, channels, samples) + signal.tobytes()
    if not 1 <= bits <= 16:
        raise ValueError('Quantized bit depth must be between 1 and 16')
    # Endpoints are exactly representable because the chosen input is float32.
    endpoints = np.column_stack((signal.min(axis=1), signal.max(axis=1))).astype('<f4')
    low = endpoints[:, 0].astype(np.float64)[:, None]
    span = (endpoints[:, 1].astype(np.float64) - endpoints[:, 0])[:, None]
    normalized = 2 * (signal.astype(np.float64) - low) / np.where(span == 0, 1, span) - 1
    if method == 'mulaw':
        normalized = np.sign(normalized) * np.log1p(MU * np.abs(normalized)) / np.log1p(MU)
    levels = 2 ** bits - 1
    codes = np.rint((np.clip(normalized, -1, 1) + 1) / 2 * levels).astype(np.uint32)
    return HEADER.pack(MAGIC, METHODS[method], bits, channels, samples) + endpoints.tobytes() + pack_codes(codes, bits)


def decode_payload(payload):
    if len(payload) < HEADER.size:
        raise ValueError('Truncated EEG payload')
    magic, method, bits, channels, samples = HEADER.unpack_from(payload)
    if magic != MAGIC or method not in METHODS.values() or not channels or not samples:
        raise ValueError('Invalid EEG header')
    count = channels * samples
    body = payload[HEADER.size:]
    if method == METHODS['float32']:
        if bits != 32 or len(body) != count * 4:
            raise ValueError('Invalid float32 payload length or precision')
        signal = np.frombuffer(body, dtype='<f4').copy().reshape(channels, samples)
    else:
        if not 1 <= bits <= 16 or len(body) < channels * 8:
            raise ValueError('Invalid quantization metadata')
        endpoints = np.frombuffer(body[:channels * 8], dtype='<f4').reshape(channels, 2).astype(np.float64)
        if not np.isfinite(endpoints).all() or np.any(endpoints[:, 1] < endpoints[:, 0]):
            raise ValueError('Invalid channel endpoints')
        codes = unpack_codes(body[channels * 8:], bits, count).reshape(channels, samples)
        normalized = 2 * codes.astype(np.float64) / (2 ** bits - 1) - 1
        if method == METHODS['mulaw']:
            normalized = np.sign(normalized) * np.expm1(np.abs(normalized) * np.log1p(MU)) / MU
        signal = (endpoints[:, 0, None] + (normalized + 1) / 2 * (endpoints[:, 1] - endpoints[:, 0])[:, None]).astype('<f4')
    if not np.isfinite(signal).all():
        raise ValueError('Decoded nonfinite values')
    return signal


def make_archive(payload):
    output = io.BytesIO()
    entry = zipfile.ZipInfo('eeg.bin', date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(entry, payload, compresslevel=9)
    return output.getvalue()


def read_archive(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.namelist() != ['eeg.bin']:
            raise ValueError('Expected one EEG payload')
        # ZipFile.read verifies the member CRC before reconstruction.
        return decode_payload(archive.read('eeg.bin'))
