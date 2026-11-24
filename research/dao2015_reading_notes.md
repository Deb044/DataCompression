# Supplementary background reading: Dao, Li and Do (2015)

Added to the website on 24 November 2026, after the initial eight-study review and protocol PDF. The original search log and report remain historical artifacts, not updated claims of a larger systematic search.

- Paper: Phuong Thi Dao, Xue Jun Li and Hung Ngoc Do, _Lossy Compression Techniques for EEG Signals_, ATC 2015, pp. 154–159.
- DOI: https://doi.org/10.1109/ATC.2015.7388309
- Institutional record and lawful manuscript: https://openrepository.aut.ac.nz/items/9c3f09eb-77fc-4c3e-8597-02569b5417ed
- Access: all six pages of the user-supplied manuscript extracted and read; pages 1–3 visually checked, including the PRD equation. Publication metadata checked against the institutional record.

## Material used

Sections I–II motivate compression for long-duration, multichannel acquisition and describe irregular EEG activity, transient events, shared structure, a transform/quantization/coding pipeline, and CR and PRD. Sections III–IV organize classical approaches and discuss dataset dependence, post-reconstruction seizure detection and device power costs. The website paraphrases this background and links it to the existing experiments. No figure or performance table was copied, and no cited algorithm was replicated.

## Interpretation and corrections

- Exact lossless reconstruction must have zero sample distortion. The introduction's statement associating lossless coding with nonzero PRD was not repeated.
- DFT, DCT and DWT are transforms; quantization is a distinct, potentially lossy operation. The manuscript's loose classification of DCT/DWT as quantizers was not adopted.
- The manuscript's PRD uses sqrt(sum squared error / sum squared original samples), multiplied by 100. Our `experiments/decoder.py` NRMSE divides the error norm by the norm of channel-wise mean-removed original data, without multiplying by 100. These are different conventions.
- A quoted 10% PRD criterion is historical, task-dependent evidence, not a general safety threshold. Neither a low global error nor our preserved SSVEP classification validates clinical use.
- Seizure-detection figures in the survey were not promoted to general performance claims. Underlying studies were not newly audited for those numerical results.
- The 64-channel, 256 Hz, 16-bit, 24-hour storage example is illustrative arithmetic: 64 × 256 × 16 × 86,400 / 8 = 2,831,155,200 bytes, or 2.83 decimal GB, excluding metadata.
- The pipeline SVG is an original conceptual illustration, not measured data. Our implemented compressor quantizes time samples directly, then packs and ZIP-compresses them; it has no wavelet stage.
