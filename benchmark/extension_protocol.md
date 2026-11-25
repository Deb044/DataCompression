# First-day extension, specified before measuring S07–S26

The original S03–S06 evaluation is retained in `results/pilot/`, including its
configuration, predictions and plots. S01–S02 remain development participants.
The primary extension evaluates the next twenty participants, S07–S26, without
selection by baseline score, artifacts or compressed performance. Only session 1
labeled offline blocks are used. Missing or invalid recordings must be reported;
participants will not silently be replaced. The original preprocessing, split,
montage, compressors, candidate grids and four byte caps remain unchanged.

The pilot suggested that the task with greatest mean score loss depends on the
compressor, and that DCT prefix compression preserves our P300 decoder especially
well. We test whether these observations repeat in the new cohort. The primary
outcome remains the participant-average balanced-accuracy drop in percentage
points. Original scores, actual storage rates and individual changes stay visible.

Uncertainty uses 10,000 participant bootstrap samples with seed 321: resample
participant IDs and carry all tasks, methods and budgets together. Percentile
95% intervals describe each mean and paired difference. These are pointwise,
exploratory intervals, not simultaneous multiple-comparison tests. Trial-level
resampling is not used, particularly because ERP epochs can overlap. Report the
fraction of participants for whom each task has greatest loss, splitting credit
equally across exact ties. Tiny differences should not imply meaningful rankings.

A secondary decoder check uses the same saved compressed corpora. It replaces
CCA with local spectral peak-to-background scoring for SSVEP, CSP with channel
band-power plus shrinkage LDA for motor imagery, and shrinkage LDA with balanced
logistic regression on the same time-bin features for ERP. All settings are fixed
here; classifiers fit only original early data and stay frozen across compression.
These are lightweight alternatives, not optimized state-of-the-art baselines.
Their results are a sensitivity analysis, separate from the primary comparison.

No second recording day, classifier adaptation to compression, new dataset,
post-result subject exclusion or tuning on extension accuracy is included.
