"""Cache verified HTTP byte ranges containing OpenBMI's offline MATLAB variable.

The official files are MATLAB v5. Inspect compressed top-level variables and
download the complete labeled offline variable plus the original 128-byte header.
Record its source byte interval and the SHA256 of this assembled MATLAB file.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import struct
import urllib.request
import zlib

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, resample_poly, sosfiltfilt

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / '.data' / 'openbmi'
BASE = 'https://s3.ap-northeast-1.wasabisys.com/gigadb-datasets/live/pub/10.5524/100001_101000/100542/'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fetch_offline(subject, task, cache=CACHE):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    name = f'sess01_subj{subject:02d}_EEG_{task}.mat'
    path = cache / name
    record_path = path.with_suffix('.source.json')
    if path.exists() and record_path.exists():
        record = json.loads(record_path.read_text())
        if path.stat().st_size != record['downloaded_bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'Cached source changed: {path}')
        return path, record
    url = BASE + f'session1/s{subject}/' + name
    request = urllib.request.Request(url, headers={'Range': 'bytes=0-4095'})
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 206:
            raise ValueError('Source must honor HTTP ranges')
        head = response.read()
        total = int(response.headers['Content-Range'].split('/')[-1])
    variable = f'EEG_{task}_train'
    if head[126:128] != b'IM':
        raise ValueError('Expected little-endian MATLAB v5')
    offset = 128
    # ERP files put the online test variable first. Inspect tags and names rather
    # than assuming all three tasks have the same top-level variable order.
    while offset < total:
        if offset == 128:
            chunk = head[128:]
        else:
            request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-{min(offset+4095,total-1)}'})
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 206:
                    raise ValueError('Source must honor HTTP ranges')
                chunk = response.read()
        kind, count = struct.unpack('<II', chunk[:8])
        if kind != 15:
            raise ValueError('Expected a compressed MATLAB variable')
        preview = zlib.decompressobj().decompress(chunk[8:])
        if variable.encode() in preview[:100]:
            break
        offset += 8 + count
    else:
        raise ValueError('Labeled offline variable missing')
    length = 136 + count
    source_end = offset + 8 + count - 1
    partial = path.with_suffix('.part')
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-{source_end}'})
    with urllib.request.urlopen(request, timeout=180) as response, partial.open('wb') as output:
        if response.status != 206 or response.headers['Content-Range'] != f'bytes {offset}-{source_end}/{total}':
            raise ValueError('Unexpected source range')
        output.write(head[:128])
        for block in iter(lambda: response.read(1024 * 1024), b''):
            output.write(block)
    if partial.stat().st_size != length:
        raise ValueError('Incomplete source range')
    partial.replace(path)
    record = dict(subject=subject, task=task, file=name, url=url,
                  source_bytes=total, range_start=offset, range_end=source_end,
                  downloaded_bytes=length, sha256=digest(path), variable=variable)
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    print(f'Downloaded S{subject:02d} {task}: {length / 1e6:.1f} MB', flush=True)
    return path, record


def load_recording(subject, task, config, cache=CACHE):
    """Load one participant/task at a time; keep EMG and labels out of the codec."""
    path, record = fetch_offline(subject, task, cache)
    signature = hashlib.sha256(json.dumps({k: config[k] for k in [
        'channels', 'sample_rate_hz', 'common_bandpass_hz']}, sort_keys=True).encode()).hexdigest()[:16]
    prepared = Path(cache) / f'S{subject:02d}_{task}_{signature}.npz'
    metadata = prepared.with_suffix('.json')
    if prepared.exists() and metadata.exists():
        source = json.loads(metadata.read_text())
        if source['sha256'] != record['sha256']:
            raise ValueError('Prepared recording belongs to another source')
        with np.load(prepared) as cached:
            return cached['signal'], cached['events'], cached['labels'], source
    mat = loadmat(path, variable_names=[record['variable']], simplify_cells=True)
    data = mat[record['variable']]
    names = [str(name).strip() for name in np.asarray(data['chan']).ravel()]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate source channel names')
    indices = [names.index(name) for name in config['channels']]
    source_rate = int(data['fs'])
    # MATLAB t indexes samples from one. Convert explicitly before resampling.
    onsets = (np.asarray(data['t']).ravel().astype(float) - 1) / source_rate
    labels = np.asarray(data['y_dec']).ravel().astype(int)
    if len(onsets) != len(labels) or len(np.unique(onsets)) != len(onsets):
        raise ValueError('Invalid or duplicate source events')
    # ERP stores the first flashes of some sequences out of time order. Sort
    # onset-label pairs together; never reorder the labels independently.
    order = np.argsort(onsets, kind='stable')
    reordered = int(np.sum(order != np.arange(len(order))))
    onsets, labels = onsets[order], labels[order]
    mappings = np.asarray(data['class'], dtype=object).tolist()
    expected = {'SSVEP': [['1', 'up'], ['2', 'left'], ['3', 'right'], ['4', 'down']],
                'MI': [['1', 'right'], ['2', 'left']],
                'ERP': [['1', 'target'], ['2', 'nontarget']]}
    if [[str(a), str(b).lower()] for a, b in mappings] != expected[task]:
        raise ValueError(f'Unexpected source label mapping: {mappings}')
    signal = np.asarray(data['x'][:, indices], dtype=np.float64).T
    del mat, data
    rate = config['sample_rate_hz']
    from math import gcd
    divisor = gcd(source_rate, rate)
    signal = resample_poly(signal, rate // divisor, source_rate // divisor, axis=1)
    sos = butter(4, config['common_bandpass_hz'], btype='bandpass', fs=rate, output='sos')
    signal = sosfiltfilt(sos, signal, axis=1).astype(np.float32)
    events = np.rint(onsets * rate).astype(int)
    if not np.isfinite(signal).all() or np.any(events < 0):
        raise ValueError('Invalid signal or events')
    source = dict(record, source_sample_rate=source_rate, source_mapping=mappings,
                  channel_names=names, source_events_reordered=reordered)
    np.savez(prepared, signal=signal, events=events, labels=labels)
    metadata.write_text(json.dumps(source, indent=2))
    return signal, events, labels, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subjects', nargs='+', type=int, default=[1, 2, 3, 4, 5, 6])
    args = parser.parse_args()
    jobs = [(subject, task) for subject in args.subjects for task in ['SSVEP', 'MI', 'ERP']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda job: fetch_offline(*job), jobs))


if __name__ == '__main__':
    main()
