# EEG Compresion

An interactive, self-contained introduction to data compression and a measured benchmark of three EEG applications: SSVEP recognition, motor imagery and single-flash P300 detection.

## The question

At the same storage allowance, which application-and-decoder combinations lose performance fastest, and does their ordering depend on the compressor?

This is a small paired benchmark. It cannot establish a universal ranking of EEG tasks. Same participants and acquisition setup reduce confounding, but decoders, class counts and baseline difficulty still differ.

## Website

Public site: https://da3021-compression-lab-deb044.solidflask.chatgpt.site/

For local use, run `python -m http.server 8000` and open http://localhost:8000. The default Contents page links to Overview, Techniques, EEG, Literature and Experiments. There is no frontend build or runtime package dependency. Synthetic demonstrations are labeled separately from measured EEG results.

## Reproduce

Python, a CPU and 16 GB RAM are sufficient for the implemented sequential loader. Downloads and the full run can take substantial time depending on the connection and CPU; there is no GPU requirement.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest benchmark.test_benchmark -v
.\.venv\Scripts\python.exe -m benchmark.data
.\.venv\Scripts\python.exe -m benchmark.run
.\.venv\Scripts\python.exe -m benchmark.verify --replay
.\.venv\Scripts\python.exe -m benchmark.report
```

On other systems use the corresponding virtual-environment Python path. `benchmark.run --subjects 1 --tasks SSVEP --baseline-only --output tmp/baseline-check` is a small original-data check. Subset runs are marked incomplete and must not be presented as the final benchmark.

Data and encoded reconstruction corpora are cached in ignored `.data/openbmi/`. The initial download is several GB: six participants, three tasks, session 1 offline blocks. Process one MATLAB recording at a time. The loader then caches the common-preprocessed arrays, avoiding repeated decompression of large MATLAB variables. Measured caches are tied to protocol and implementation hashes. Delete only stale `*_measured.json` files if intentionally changing the implementation; the original source cache can be retained.

## Fixed protocol

The initial protocol was committed before inspecting waveforms or classification outcomes. See `benchmark/config.json` and the recorded implementation/protocol hashes. No evaluation participant was selected or excluded based on results.

- Data: [Lee et al., OpenBMI (2019)](https://doi.org/10.1093/gigascience/giz002), dataset DOI [10.5524/100542](https://doi.org/10.5524/100542). Official GigaDB object-storage URLs follow the current MOABB loader.
- Development participants S01–S02; evaluation participants S03–S06. Session 1, labeled offline (`*_train`) variables only. Online and resting-state blocks are not used.
- The MATLAB files have compressed top-level variables. The downloader identifies the offline variable by name, fetches its entire byte range and prepends the original MATLAB header. ERP puts the online variable first, unlike MI and SSVEP. Every source URL, range, total source length and locally computed SHA256 is exported. These hashes pin downloaded ranges; they are not publisher-authenticated checksums of the full files.
- Event indices are converted from MATLAB one-based indices. ERP source events can be stored out of order; onset-label pairs are stably sorted together. No labels are inferred or repaired. Source label mappings are checked explicitly.
- Shared stored montage: C3, Cz, C4, FC1, FC2, CP1, CP2, Pz, POz, O1, Oz, O2. Source channels are selected by name, not guessed index. Auxiliary EMG is excluded.
- Shared representation: resample 1000 Hz source recordings to 128 Hz with anti-alias filtering, then fourth-order 0.5–40 Hz Butterworth forward/backward filtering and float32 conversion. This is offline/noncausal filtering on the continuous offline recording, not a streaming system. Its temporal filtering dependencies are not eliminated by the epoch guard.
- Chronological split at 60% of source events. Training epochs must finish at least two seconds before the boundary; test epochs begin at least two seconds after. No overlapping train/test epochs. Classifiers for evaluation subjects are calibrated using their own early block; evaluation subjects are not unseen to their own classifier.
- SSVEP and MI use 4-second epochs; ERP uses 1-second epochs. ERP epochs can overlap within a block, but compression is applied once to the continuous test interval, not independently to overlapping epochs. The actual unique test-interval duration defines storage rate, including intervening gaps.

## Frozen decoders

- SSVEP: CCA on O1/Oz/O2 against sine/cosine references at 12, 8.57, 6.67 and 5.45 Hz with three harmonics. Rank-deficient compressed input is handled by an SVD signal subspace. No label-fitted classifier.
- MI: 8–30 Hz filtering on seven motor-region channels, trace-normalized covariance, 5% identity regularization, four CSP filters (two from each eigenvalue extreme), log normalized variance, shrinkage LDA.
- ERP: 0.5–12 Hz filtering, six 100 ms averages from 0.1 to 0.7 seconds on all twelve channels, standardization and equal-prior shrinkage LDA. This measures target/non-target detection per flash, not 36-character spelling accuracy.

Each fitted decoder is reused unchanged for every reconstruction. No retraining or codec selection based on test accuracy occurs.

## Matched storage allowances

Three pipelines: symmetric uniform amplitude quantization, symmetric mu-law companding (mu=255) followed by uniform quantization, and orthonormal type-II DCT prefix retention followed by symmetric coefficient quantization. All use integer bit packing and DEFLATE ZIP level 6. Mu-law here is a continuous teaching compander, not G.711.

One-second frames receive caps of 32, 64, 128 and 256 bytes/second/channel. With twelve channels these mean total caps of 384, 768, 1536 and 3072 bytes/second. Raw selected float32 requires 512 bytes/second/channel. Each codec sees every stored channel, even when its task decoder uses a subset.

A self-contained `.eegpack` contains a JSON header with channel order, sampling rate and dimensions, followed by length-prefixed independent frame ZIPs. Each frame stores the format version, method, precision, shape, retained-coefficient count and float32 per-channel scale. Mu=255 and the DCT convention are fixed by version EEG2. All these bytes count. Global-header overhead is conservatively reserved across frames, so the complete corpus cannot exceed its cap.

For each input frame the encoder searches the finite candidate grid in config and chooses the feasible candidate with lowest sample-domain MSE. This uses original waveform values available at encoding, but no labels, classifier outputs or downstream accuracy. DCT search considers the declared prefix lengths and coefficient precisions. Infeasible conditions are explicitly reported, never silently replaced. Equal caps do not imply exactly equal achieved sizes; actual rates are exported. Encoder search costs and decoder model weights are outside the storage measurement. Task event annotations are agreed separately for all codecs and are not encoded as EEG payload.

A float32+ZIP control must reconstruct byte-exact input samples and preserve all decisions. Every lossy score is computed after decoding its saved corpus, not an unarchived approximation.

## Measurements and interpretation

Primary score: balanced accuracy; primary comparison: its absolute drop from the original baseline, in percentage points. Negative drops are improvements. Report original baselines and chance (25% SSVEP, 50% MI/ERP), ordinary accuracy, binary ROC-AUC, prediction-change rates, full confusion matrices, NRMSE and actual bytes. NRMSE is the error norm divided by the norm of channel-mean-removed original samples. Participant means have equal weight, rather than allowing ERP's larger trial count to dominate. The interface additionally reports (mean compressed balanced accuracy − chance) / (mean original balanced accuracy − chance), withholding this ratio when the original mean is within five percentage points of chance. This is a descriptive normalization, not a statistical correction or a new primary metric. It is not clipped to [0, 1].

The interface flags baselines within five percentage points of chance as weak; this is a descriptive warning and does not exclude participants. Participants, especially low-baseline MI users, remain visible individually. Four evaluation participants do not support a universal or clinically validated task ranking. Plotted participant ranges are not confidence intervals. Lines between tested budgets are guides only. Method-specific ranks are descriptive, including ties, not significance tests. No superiority over optimized codecs is claimed.

## Files

- `benchmark/config.json`: frozen protocol and finite codec grids.
- `benchmark/data.py`: verified range downloads, source mappings and common preprocessing.
- `benchmark/codec.py`: self-contained ZIP frame encoders and corpus reader.
- `benchmark/decoders.py`: the three original-data decoders.
- `benchmark/run.py`: chronological evaluation and recorded exports.
- `benchmark/test_benchmark.py`: codec, cap, leakage and decoding edge-case checks.
- `benchmark/verify.py`: independent metric/byte checks and optional complete evaluation replay.
- `benchmark/report.py`: standalone plots from measured data.
- `results/benchmark/summary.json`: configuration, measured points, participant aggregates, environment and source hashes.
- `results/benchmark/predictions.csv`: original and reconstructed predictions for every tested condition.
- `results/benchmark/archives/`: first-frame examples for S03; full encoded test corpora remain in the ignored local cache and can be regenerated.
- `experiment-view.js`: interactive results display; it refuses incomplete exports.

The earlier single-task precision/score-gap experiments are superseded and removed from the active site and code. Their history remains in Git. Literature references are contextual evidence, not reproduced performance results. The original literature search log is historical and does not document this new experimental protocol.

AI assistance was used for source discovery, writing and implementation. All research numbers shown on the site come from recorded runs and are independently checked; no participant recordings are redistributed in the public repository.
