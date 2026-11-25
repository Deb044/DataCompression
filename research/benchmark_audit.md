# First-day EEG extension: verification and interpretation

Audit date: 25 November 2026. This twenty-person extension supersedes the original four-person pilot as the main result. The unchanged pilot data and original audit remain in `results/pilot/`. This is a benchmark of simple compressors, not an optimized EEG codec reproduction.

## Cohorts and frozen comparison

S01–S02 are development participants. S03–S06 are the pilot. The new evaluation cohort is S07–S26, selected in advance without exclusion by baseline or compression outcome. All twenty completed all three tasks in the first recording session. No second-day recordings are used. The extension protocol was committed in ee482a0 before new-cohort measurements.

Preprocessing, 12 stored channels, 128 Hz representation, 0.5–40 Hz common bandpass, chronological 60% split, two-second epoch guard, codec grids and four byte caps remain fixed. Decoders fit only original early data, then remain frozen. Evaluation subjects supply their own calibration; this is not unseen-person classification. Continuous offline noncausal filtering can introduce dependencies beyond the epoch guard.

## Independent checks

- Primary: 792 conditions, 227,052 exported trial predictions and all byte caps checked.
- Alternative: 720 conditions, 206,400 exported trial predictions and all byte caps checked.
- 720 saved evaluation corpora decoded with each decoder family: 1,440 replayed decoder evaluations.
- Every evaluation lossless corpus recovers the exact selected float32 input and preserves predictions. Every lossy score is reproduced from its stored bytes.
- Means, medians, pointwise 95% intervals and paired task/method differences were independently rebuilt from verified point exports. Bootstrap: 10,000 whole-person resamples, seed 321, all conditions carried together. These are not multiplicity-adjusted hypothesis tests.
- Eight focused unit tests pass, covering bit packing, reconstruction, complete-corpus caps, split overlap, CCA, spectral decoding, paired resampling/ties and interrupted-download resumption.
- Export verification records pin summary and prediction-file SHA256 values. Git attributes preserve hashed scientific files without line-ending conversion. Source files match committed bytes.

## Original balanced accuracy

| Task | Primary decoder | Alternative decoder |
| --- | ---: | ---: |
| SSVEP | 93.40% | 80.88% |
| MI | 69.93% | 62.07% |
| ERP | 81.60% | 83.83% |

Three motor-imagery primary baselines are within five points of chance; they remain included. Task difficulty and original performance differ materially.

## Tightest allowance: 32 bytes/s/channel

| Decoder family | Task | Uniform loss | Mu-law loss | DCT loss |
| --- | --- | ---: | ---: | ---: |
| primary | SSVEP | 12.13 pp | 12.95 pp | 8.82 pp |
| primary | MI | 9.22 pp | 10.91 pp | 4.10 pp |
| primary | ERP | 9.47 pp | 9.60 pp | 0.61 pp |
| alternative | SSVEP | 4.92 pp | 7.58 pp | 10.88 pp |
| alternative | MI | 8.44 pp | 7.75 pp | 7.46 pp |
| alternative | ERP | 12.30 pp | 12.25 pp | 2.25 pp |

SSVEP has the greatest mean primary-decoder loss under all three methods at this allowance. However, every primary SSVEP-minus-MI paired interval crosses zero. Uniform primary SSVEP has greatest loss in 8/20 people, not everyone. The pilot’s uniform and mu-law task ordering does not repeat in the new primary cohort.

With alternative decoders, P300 has greatest mean loss under uniform and mu-law, while SSVEP does under DCT. Alternative original scores also differ. This demonstrates sensitivity to the readout pipeline; it is not evidence of an intrinsic universal task ordering.

The P300 DCT-versus-uniform result repeats across both readers and all twenty people. Mean paired reduction in loss: 8.87 pp [pointwise 95% interval 7.95–9.83] for the primary reader, and 10.05 pp [9.00–11.20] for the alternative. Both readers use the same low-frequency time-bin features; changing only the classifier does not test all P300 feature representations. DCT low-frequency retention is compatible with those features, but causality was not isolated.

## Decoder and storage details

Primary: occipital CCA with three harmonics; regularized CSP + shrinkage LDA; and low-frequency response-bin features + equal-prior shrinkage LDA. Alternative: harmonic spectral peak/background ratios; channel mu/beta log-power + standardized shrinkage LDA; and the same P300 response-bin features + balanced logistic regression, C=1. No compression-specific retraining or test-label tuning.

All methods choose minimum-MSE feasible candidates from their fixed grids without labels. Complete frame ZIP bytes, scales, packed codes, length prefixes and global reconstruction metadata count. Equal maximum allowances leave different unused space; actual rates and their plots are supplied. Models and task annotations are outside EEG payload for all codecs. Search grids and encoder computation differ. No superiority over optimized codecs is claimed.

## Data integrity and limits

Official offline MATLAB variables are selected by name, including ERP’s different variable order. Event onset/label pairs are stably sorted together. Source label maps and channel names are checked. Downloads resume verified byte ranges; truncated files never become accepted recordings. SHA256 values pin locally assembled ranges, not publisher-authenticated complete-file checksums. Original recordings and full reconstruction corpora remain in the ignored local cache, not the public repository.

Twenty new people strengthen the pilot but remain one acquisition study, one recording day, one montage and two chosen readouts per task. The sample is not a random population sample. Absolute point loss is the primary outcome; above-chance retention is supplementary and depends strongly on baseline. Prediction changes, waveform error and task scores answer different questions. No clinical, real-time, battery-life or universal novelty claim is made.
