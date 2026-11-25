# Three-task benchmark: verification and interpretation

Audit date: 25 November 2026. This document concerns the replacement OpenBMI experiment, not the superseded single-task experiment. The benchmark is original teaching code, not a reproduction of an optimized published compressor.

## Claim-to-evidence checks

| Claim | Evidence and disposition |
| --- | --- |
| Three distinct paradigms from the same people and acquisition study | **Verified:** source variables and class maps in `benchmark/data.py`; session-1 S01–S06 source URLs and byte-range hashes are in `results/benchmark/summary.json`. Source mappings are explicitly checked. |
| Train/test epochs do not overlap | **Verified:** chronological 60% boundary, two-second guard, endpoint checks in `benchmark/run.py`, and synthetic split test. This does not remove the continuous noncausal preprocessing dependency across the boundary. |
| Classifiers remain fixed across compressors and caps | **Verified:** each decoder is fitted once per subject/task on original early events. Reconstruction is passed only to prediction. Evaluation participants still supply their own calibration data; this is not unseen-subject classification. |
| Reconstruction uses only encoded data | **Verified:** every score reads its saved `.eegpack`; ZIP CRC, frame metadata, scales, precision and DCT prefix are read by `benchmark/codec.py`. Labels and original scores are not in the codec. |
| Matched actual storage caps | **Verified:** all 216 conditions feasible. Complete corpus bytes, including ZIP headers, length prefixes and global metadata, fit their declared caps. Actual rates independently recomputed. Equal caps leave different unused space; this is not an exact equal-file-size comparison. |
| Lossless control | **Verified:** each run checks exact float32 recovery and unchanged decisions; the independent evaluation replay also checks the stored lossless corpora. |
| Reported scores and participant averages | **Verified:** `python -m benchmark.verify --replay` checks 216 points, 36 aggregates, 61,932 exported trial predictions and all byte caps. It refits original-data models and replays all 144 evaluation reconstructions. |
| Graphs show measured observations | **Verified:** `benchmark/report.py` and `experiment-view.js` read the same recorded summary. No smoothing or extra observations; joining lines are disclosed as guides. Faint static-plot lines are participants, not confidence intervals. |
| One universally hardest EEG task | **Unsupported:** only four evaluation participants, one session, one montage and one decoder per paradigm. The website explicitly limits conclusions to this benchmark. |

## Important implementation findings

1. ERP variable order differs from MI/SSVEP: its online variable can precede the offline variable. The downloader was corrected to identify the requested variable rather than assume order. Only labeled offline data is used.
2. Some ERP flash onsets are out of order. Timestamp-label pairs are stably sorted together, with no event deletion or label repair. Source mappings and changes in ordering are retained in provenance.
3. Heavy compression can create constant or dependent channels. CCA now uses only the numerical SVD signal subspace, avoiding arbitrary QR completion; a zero-input test checks this case. Final measurements were rerun after that correction.
4. ERP epochs overlap within the test block. Encoding the continuous interval once avoids charging repeatedly for the same samples. Storage is per unique test-interval second, including intervening gaps.

## Recorded observations

The evaluation participant means before compression are 88.94% balanced accuracy for SSVEP, 62.41% for MI and 80.87% for ERP. MI participant S06 has a below-chance baseline and remains included, visibly flagged. Baseline difficulty is therefore a material confound when interpreting loss.

At the 32-byte/s/channel cap, mean balanced-accuracy losses (percentage points) are:

| Application | Uniform | Mu-law | DCT |
| --- | ---: | ---: | ---: |
| SSVEP | 8.48 | 5.17 | 4.57 |
| Motor imagery | 9.48 | 3.30 | 3.66 |
| P300 detection | 8.92 | 9.18 | 0.10 |

Thus the application with the largest descriptive mean loss changes with the method at this cap. This is an observation from the benchmark, not evidence that the order is statistically stable in the wider population. Differences at the highest caps are often zero or very small.

DCT prefix retention and the ERP decoder's low-frequency filtering are compatible design choices; that is a plausible explanation for ERP preservation here, not an isolated causal result. Codec grids have different flexibility, and per-frame settings minimize waveform MSE, not task loss. Search compute and model weights are not included in the storage metric.

## Reproducibility limits

Local source fingerprints pin the downloaded offline MATLAB ranges; they do not authenticate complete publisher files. Original recordings and full encoded evaluation corpora are cached locally and not redistributed. Selected first-frame archives and all predictions are public. Python, NumPy, SciPy and scikit-learn versions, protocol hash and implementation hash accompany the results. Exact DEFLATE sizes can depend on the runtime library. No clinical, battery, real-time or broad novelty claim is made.
