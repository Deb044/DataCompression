# EEG Compresion

A DA3021 course project: compression foundations, an introduction to EEG based on the course slides, a rapid structured literature review, and two controlled experiments on public SSVEP recordings. The title preserves the requested spelling.

## View the site

Serve the repository as static files:

```sh
python -m http.server 8000
```

Open http://localhost:8000. The site has no framework, external scripts, package installation or build step. Its five chapters are Overview, Techniques, EEG, Literature and Experiments. Browser demonstrations are clearly marked as synthetic or illustrative; the EEG results are loaded from recorded Python exports.

The hosted site is publicly visible to anyone with its URL. The public repository contains the site and result exports; it does not contain the original participant files.

## Reproduce the experiments

Python 3.11+ and a CPU are sufficient. From the repository root, on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest experiments.test_experiments -v
.\.venv\Scripts\python.exe -m experiments.run
.\.venv\Scripts\python.exe -m experiments.verify
```

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`. The first run downloads approximately 844 MB of original archives/metadata from the official Tsinghua server. Extraction needs roughly another 1.5 GB of disk space. Files are cached in ignored `.data/benchmark/`; participants are loaded one at a time. To download without analysis, add `--download-only`. Use `--cache PATH` and `--output PATH` to change the locations.

The source manifest pins sizes and SHA256 values computed from official HTTPS downloads. These are local reproducibility pins, not publisher-authenticated checksums. Cached extracted files are tied to their source archive and checked before reuse. A changed source fails verification instead of silently changing the experiment.

### Fixed task and split

- Dataset: [Wang et al., SSVEP benchmark](https://doi.org/10.1109/TNSRE.2016.2627556), [official downloads](https://bci.med.tsinghua.edu.cn/download.html).
- Development: S1–S2, 48 trials. Evaluation: S3–S8, 144 trials. These are all **experienced participants**, not a representative sample of all 35 participants.
- Targets: 9, 11, 13 and 15 Hz, six trials each per participant. This is a simplified four-class task with 25% chance accuracy, not the full 40-target benchmark.
- Channels: O1, Oz and O2, selected by channel names in the official metadata. Frequency indices are also resolved from metadata, whose order is not sorted.
- Released sampling rate: 250 Hz. Window: samples `160:1160`, corresponding to 0.14–4.14 seconds after stimulus onset. The epoch begins 0.5 seconds before onset.
- Preprocessing: subtract each channel's window mean and convert to float32. No artifact rejection or additional filtering.
- Decoder: demean, apply one Hann window, FFT, then sum power at the nearest bins to each candidate's fundamental and second harmonic across all three channels. Equal weights, no classifier training or evaluation-set tuning.

The protocol is in `experiments/config.json`, committed before reading the waveforms. The original downloaded MATLAB arrays are float64; the float32 storage denominator is a declared representation change, **not** a claim about the acquisition resolution. The maximum float32 casting discrepancy is exported per trial. Amplitude units were not explicit in the official readme, so plots use “dataset amplitude units.”

### Experiment 1: how many bits are enough?

Quantize at 16, 12, 8, 6, 4 and 2 bits using uniform quantization and the optional continuous μ-law baseline (μ = 255). Each trial/channel uses stored float32 minimum/maximum endpoints. Codes are packed into actual b-bit fields with zero tail padding. A versioned binary header stores method and dimensions; μ = 255 is fixed by format version EEG1.

Store the payload in a one-member DEFLATE ZIP archive with a fixed filename/date and level 9 compression. Reconstruct using only that archive, then run the same decoder. The lossless float32 control is checked byte-for-byte. Archives do not contain target labels or original decoder scores.

Measure payload bytes before ZIP, complete archive bytes, NRMSE, true-label accuracy, prediction flips and all correct/wrong transitions. Each trial is archived independently; corpus sizes sum independent archives. Ratios use the selected centered float32 payload. Different Python/zlib versions may produce different archive sizes; the measured environment is recorded.

NRMSE is `||x - reconstructed_x|| / ||x - per_channel_mean(x)||`, pooling channels and samples. Constant signals have undefined NRMSE. The continuous μ-law baseline is not a bit-exact G.711 implementation. Equal bit depths do not imply equal ZIP sizes.

In this EEG variant, μ-law follows min–max normalization to [−1, 1], so its fine-resolution region is centered on the channel's range midpoint, not necessarily zero in the mean-centered recording. The results apply to this declared variant. Symmetric scaling around physical zero would be a separate controlled comparison, not a conclusion from this run.

### Experiment 2: which predictions change?

Compute the original normalized score gap `(best - runner_up) / (best + runner_up + 1e-12)`. Development-participant tertiles define low/middle/high groups; the thresholds are frozen before evaluating S3–S8. Evaluation group sizes need not be equal.

The prespecified primary condition is **uniform, 2 bits**. Report prediction flips separately from originally correct decisions becoming wrong. Compare low-gap failure-ranking ROC AUC with amplitude range/RMS and low spectral concentration. Spectral concentration is the candidate-bin power divided by total FFT power in 6–40 Hz. These predictors are fixed; none is fitted on evaluation labels.

Use 500 seeded gap shuffles within participant and true-target strata. The central 95% shuffled range is a null range, not a confidence interval. The shuffled mean need not be 0.5, because between-participant and target differences remain. AUC/permutation tests are undefined if all predictions have the same flip outcome. Other precision conditions are exploratory and their p values are not multiplicity-corrected. Participant-level results are shown instead of treating all repeated reconstructions as independent participants.

Adaptive bit allocation and a second EEG task are not implemented: they remain extensions beyond the two core experiments. This keeps the completed comparison small and interpretable.

## Measured findings and their limits

The checked-in run contains 2,496 condition-level rows across 192 original trials. On the 144 evaluation trials, original accuracy was **87.50%**. Uniform 2-bit accuracy was **86.81%**, but **12 predictions changed**: five correct answers became wrong, four wrong answers became correct, and three wrong answers changed to other wrong answers. This illustrates why aggregate accuracy alone is incomplete.

Uniform 2-bit storage was **47.38 actual ZIP bytes/second/channel**, against 1,000 bytes/second/channel for the selected uncompressed float32 representation. Mean NRMSE was approximately **0.599**: preserving many decisions did not mean faithful waveform recovery. These are observations for this small, simplified task, not a generally safe EEG compression setting.

The primary score-gap AUC was approximately **0.963**, compared with approximately **0.872** for the stratified shuffled null mean. Only 12 flips were observed; the strong-looking pooled ranking must be interpreted with the cohort and decoder restrictions. See the complete rows, group counts, participant results and null controls on the site.

Results and data needed to inspect them:

- `results/summary.json`: all conditions, participant summaries and gap controls.
- `results/trials.csv`: every paired reconstruction, including actual byte counts and archive hashes.
- `results/original_trials.csv`: original decisions and signal features.
- `results/provenance.json`: exact code commit, configuration, source pins, environment and timing.
- `results/examples.json`: four predeclared examples from S3 block 1, all selected targets, with original and reconstructed Oz traces. Display arrays are rounded; metrics use full precision.
- `results/archives/`: all 13 conditions for the first predeclared example, including the byte-exact float32 control.
- `results/*.png`: standalone scientific figures generated from the measured exports.

The static page reads these files. Its selectors inspect saved results; it does not rerun the Python experiment or download the original corpus in a visitor's browser. Regenerate the exports with the run command after changing the protocol.

## Source layout

| File                                                       | Responsibility                                                                  |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `index.html`, `styles.css`                                 | Lesson content and responsive layout                                            |
| `app.js`, `signal.js`, `samples.js`, `zip.js`              | Navigation and clearly labelled foundation demonstrations                       |
| `literature.js`, `content/references.json`                 | Curated review summaries and verified references                                |
| `experiment-view.js`, `table.js`                           | Render saved experiment exports and interactive recorded examples               |
| `experiments/dataset.py`                                   | Verified downloads, cache and trial extraction                                  |
| `experiments/codec.py`                                     | Bit packing, self-contained payload and ZIP reconstruction                      |
| `experiments/decoder.py`                                   | Fixed FFT scores, waveform error and signal features                            |
| `experiments/analysis.py`                                  | Paired summaries, AUC and stratified permutation controls                       |
| `experiments/run.py`, `experiments/plots.py`               | Reproducible run and figure exports                                             |
| `experiments/test_experiments.py`, `experiments/verify.py` | Meaningful algorithm checks and independent result audit                        |
| `research/`, `output/pdf/`                                 | Search log and original literature-review/protocol PDF, prepared before the run |

## Sources and disclosure

The site's EEG introduction follows the supplied course slides, _Neural Signal Capture_, particularly multichannel EEG (p. 172), cortical activity (p. 175), the alpha demonstration (pp. 180–183), bands (p. 184) and artifacts (pp. 186–187). The original course PDF is not redistributed.

The review is a **rapid structured review**, not an exhaustive systematic review. It marks preprints, abstract-level access and uncertain publication metadata. We do not claim a globally new compression method, clinical suitability, hardware energy savings or superiority over learned codecs. See `content/references.json`, the PDF and `research/search_log.json` for source details and coverage limits.

AI assistance was used for literature discovery, drafting, code and protocol development. Measured outputs are generated by the supplied code, not fabricated by the language model. Read and verify the central sources before presenting the work.

The Techniques chapter also covers PNG and common lossy JPEG coding. `image-demo.js` encodes opaque synthetic images with the browser PNG/JPEG encoders, reporting actual file bytes and decoded RGB RMSE. Quality settings are encoder parameters, not percentages of retained information.
