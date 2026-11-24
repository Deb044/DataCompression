"""Download pinned official files and load a small declared SSVEP subset."""

from pathlib import Path
import hashlib
import json
import time
import urllib.request

import numpy as np
import py7zr
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_CACHE = ROOT / '.data' / 'benchmark'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_files(subjects, cache=DEFAULT_CACHE):
    """Verify cached originals or download from the manifest's official URLs."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / 'data_manifest.json').read_text())
    names = {'Readme.txt', '64-channels.loc', 'Freq_Phase.mat'} | {f'S{s}.mat.7z' for s in subjects}
    records = [record for record in manifest['files'] if record['file'] in names]
    if {record['file'] for record in records} != names:
        raise ValueError('Requested subject is not in the pinned source manifest')
    for record in records:
        destination = cache / record['file']
        if not destination.exists():
            partial = destination.with_suffix(destination.suffix + '.part')
            for attempt in range(3):
                try:
                    print(f"Downloading {record['file']} ({record['bytes'] / 1e6:.1f} MB)", flush=True)
                    with urllib.request.urlopen(record['url'], timeout=90) as response, partial.open('wb') as output:
                        for chunk in iter(lambda: response.read(1024 * 1024), b''):
                            output.write(chunk)
                    if partial.stat().st_size != record['bytes'] or sha256(partial) != record['sha256']:
                        raise ValueError('Download differs from the pinned source')
                    partial.replace(destination)
                    break
                except (OSError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(1 + attempt)
        if destination.stat().st_size != record['bytes'] or sha256(destination) != record['sha256']:
            raise ValueError(f'{destination.name} differs from the pinned download; do not silently reuse it')
    return records


def metadata(config, cache=DEFAULT_CACHE):
    cache = Path(cache)
    channels = [line.split()[-1] for line in (cache / '64-channels.loc').read_text().splitlines() if line.strip()]
    frequencies = np.asarray(loadmat(cache / 'Freq_Phase.mat')['freqs']).ravel()
    channel_indices = [channels.index(name) for name in config['channels']]
    target_indices = []
    for frequency in config['target_frequencies_hz']:
        matches = np.flatnonzero(np.isclose(frequencies, frequency))
        if len(matches) != 1:
            raise ValueError(f'Frequency metadata is ambiguous for {frequency}')
        target_indices.append(int(matches[0]))
    if len(channels) != 64 or len(frequencies) != 40:
        raise ValueError('Unexpected benchmark metadata')
    return channel_indices, target_indices


def subject_trials(subject, config, cache=DEFAULT_CACHE):
    """Yield 24 centered float32 trials without keeping other subjects in RAM."""
    cache = Path(cache)
    channel_indices, target_indices = metadata(config, cache)
    archive_path = cache / f'S{subject}.mat.7z'
    with py7zr.SevenZipFile(archive_path) as archive:
        members = archive.getnames()
        if len(members) != 1 or Path(members[0]).name != members[0] or not members[0].lower().endswith('.mat'):
            raise ValueError('Unexpected archive member layout')
        mat_path = cache / members[0]
        extraction_path = cache / f'{members[0]}.extraction.json'
        archive_digest = sha256(archive_path)
        extraction = json.loads(extraction_path.read_text()) if extraction_path.exists() else {}
        cache_valid = (mat_path.exists() and extraction.get('archive_sha256') == archive_digest
                       and extraction.get('mat_sha256') == sha256(mat_path))
        if not cache_valid:
            print(f'Extracting S{subject}', flush=True)
            archive.extract(path=cache, targets=members)
            extraction_path.write_text(json.dumps({'archive_sha256': archive_digest,
                                                   'mat_sha256': sha256(mat_path)}))
    data = loadmat(mat_path, variable_names=['data'])['data']
    if data.shape != (64, 1500, 40, 6) or data.dtype != np.float64:
        raise ValueError(f'Unexpected S{subject} data shape or representation')
    start, stop = config['start_sample'], config['stop_sample']
    if not 125 <= start < stop <= 1375:
        raise ValueError('Analysis interval must be within stimulation')
    for block in range(6):
        for frequency, target_index in zip(config['target_frequencies_hz'], target_indices):
            original = data[channel_indices, start:stop, target_index, block]
            if not np.isfinite(original).all():
                raise ValueError('Nonfinite dataset values')
            centered = original - original.mean(axis=1, keepdims=True)
            signal = centered.astype('<f4')
            yield {'id': f'S{subject:02d}-B{block + 1}-F{frequency}', 'subject': subject,
                   'block': block + 1, 'target_hz': frequency,
                   'float32_cast_max_abs': float(np.max(np.abs(centered - signal)))}, signal
