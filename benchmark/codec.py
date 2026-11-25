"""Small, self-contained frame codecs with real ZIP byte accounting.

All methods store float32 symmetric per-channel scales and packed integer codes.
DCT stores its prefix length; omitted coefficients are zero. One frame is one
independent ZIP archive, including all headers. No target labels enter this file.
"""

import io
import json
import struct
import zipfile

import numpy as np
from scipy.fft import dct, idct

HEADER = struct.Struct('<4sBBHHHH')
METHOD = {'float32': 0, 'uniform': 1, 'mulaw': 2, 'dct': 3}
MU = 255


def pack(codes, bits):
    codes = np.asarray(codes, dtype=np.uint32).ravel()
    if not 1 <= bits <= 16 or np.any(codes >= (1 << bits)):
        raise ValueError('Invalid codes or bit depth')
    binary = (codes[:, None] >> np.arange(bits-1, -1, -1)) & 1
    return np.packbits(binary.astype(np.uint8).ravel(), bitorder='big').tobytes()


def unpack(data, bits, count):
    if len(data) != (count * bits + 7) // 8:
        raise ValueError('Wrong packed length')
    binary = np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder='big')
    if np.any(binary[count*bits:]):
        raise ValueError('Invalid padding')
    return binary[:count*bits].reshape(count, bits) @ (1 << np.arange(bits-1, -1, -1))


def archive(payload):
    stream = io.BytesIO()
    entry = zipfile.ZipInfo('frame.bin', date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr(entry, payload, compresslevel=6)
    return stream.getvalue()


def encode(frame, method, bits=32, retained=None, sample_rate=128):
    x = np.asarray(frame, dtype='<f4')
    if x.ndim != 2 or not x.size or not np.isfinite(x).all():
        raise ValueError('Expected finite channels-by-samples data')
    channels, samples = x.shape
    if method == 'float32':
        if bits != 32:
            raise ValueError('Float32 requires 32 bits')
        return archive(HEADER.pack(b'EEG2', 0, 32, channels, samples, samples, sample_rate) + x.tobytes())
    retained = samples if method != 'dct' else int(retained)
    if method not in METHOD or not 1 <= retained <= samples or not 1 <= bits <= 16:
        raise ValueError('Invalid codec configuration')
    values = dct(x.astype(float), type=2, norm='ortho', axis=1)[:, :retained] if method == 'dct' else x.astype(float)
    scales = np.max(np.abs(values), axis=1).astype('<f4')
    normalized = values / np.where(scales == 0, 1, scales)[:, None]
    if method == 'mulaw':
        normalized = np.sign(normalized) * np.log1p(MU * np.abs(normalized)) / np.log1p(MU)
    codes = np.rint((np.clip(normalized, -1, 1) + 1) / 2 * (2**bits-1)).astype(np.uint32)
    header = HEADER.pack(b'EEG2', METHOD[method], bits, channels, samples, retained, sample_rate)
    return archive(header + scales.tobytes() + pack(codes, bits))


def decode(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if z.namelist() != ['frame.bin']:
            raise ValueError('Unexpected ZIP contents')
        payload = z.read('frame.bin')  # Includes CRC verification.
    if len(payload) < HEADER.size:
        raise ValueError('Truncated header')
    magic, method, bits, channels, samples, retained, rate = HEADER.unpack_from(payload)
    if magic != b'EEG2' or method not in METHOD.values() or not channels or not samples or not rate:
        raise ValueError('Invalid frame header')
    body = payload[HEADER.size:]
    if method == 0:
        if bits != 32 or retained != samples or len(body) != channels*samples*4:
            raise ValueError('Invalid float32 length')
        return np.frombuffer(body, dtype='<f4').reshape(channels, samples).copy()
    if not 1 <= bits <= 16 or not 1 <= retained <= samples or (method != 3 and retained != samples):
        raise ValueError('Invalid shape or precision')
    scales = np.frombuffer(body[:channels*4], dtype='<f4')
    if len(scales) != channels or np.any(scales < 0) or not np.isfinite(scales).all():
        raise ValueError('Invalid scales')
    values = 2 * unpack(body[channels*4:], bits, channels*retained).reshape(channels, retained) / (2**bits-1) - 1
    if method == 2:
        values = np.sign(values) * np.expm1(np.abs(values)*np.log1p(MU)) / MU
    values *= scales[:, None]
    if method == 3:
        values = idct(np.pad(values, ((0, 0), (0, samples-retained))), type=2, norm='ortho', axis=1)
    result = values.astype('<f4')
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite reconstruction')
    return result


def candidates(frame, method, config):
    if method == 'dct':
        for retained in config['dct_coefficients']:
            for bits in config['dct_bits']:
                yield bits, retained, encode(frame, method, bits, retained, config['sample_rate_hz'])
    else:
        for bits in config['amplitude_bits']:
            yield bits, frame.shape[1], encode(frame, method, bits, sample_rate=config['sample_rate_hz'])


def choose_frames(frame, method, config, overhead=0):
    """Select least-MSE feasible candidates using the input waveform only."""
    channels, samples = frame.shape
    caps = {budget: int(budget * channels * samples / config['sample_rate_hz']) - overhead
            for budget in config['budgets_bytes_per_second_channel']}
    best = {budget: None for budget in caps}
    for bits, retained, encoded in candidates(frame, method, config):
        feasible = [budget for budget, cap in caps.items() if len(encoded) <= cap]
        if not feasible:
            continue
        recovered = decode(encoded)
        error = float(np.mean((frame.astype(float)-recovered.astype(float))**2))
        for budget in feasible:
            if best[budget] is None or error < best[budget]['mse']:
                best[budget] = dict(mse=error, data=encoded, recovered=recovered,
                                    bits=bits, retained=retained, bytes=len(encoded))
    return best


def corpus_header(channels, samples, config):
    metadata = json.dumps(dict(channels=config['channels'], sample_rate=config['sample_rate_hz'],
                               samples=samples, frame_samples=config['sample_rate_hz'],
                               format='EEG2 length-prefixed ZIP frames'), separators=(',', ':')).encode()
    return b'EEGPACK2' + struct.pack('<I', len(metadata)) + metadata


def read_corpus(path):
    """Reconstruct using only the file; labels and original values are absent."""
    with open(path, 'rb') as stream:
        if stream.read(8) != b'EEGPACK2':
            raise ValueError('Bad corpus magic')
        metadata = json.loads(stream.read(struct.unpack('<I', stream.read(4))[0]))
        frames = []
        while prefix := stream.read(4):
            length = struct.unpack('<I', prefix)[0]
            data = stream.read(length)
            if len(data) != length:
                raise ValueError('Truncated frame')
            frames.append(decode(data))
    x = np.concatenate(frames, axis=1)
    if x.shape != (len(metadata['channels']), metadata['samples']):
        raise ValueError('Corpus shape mismatch')
    return x
