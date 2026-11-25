# EEG Compression presentation

Twelve content slides in the supplied Beamer Boadilla/seahorse/serif style,
with the template's default 4:3 aspect ratio. There is no separate title or
outline slide. Author: Debarghya Das, 240150049. Date: 25 November 2026.

Build from this directory:

```text
tectonic main.tex
```

Alternatively, run `pdflatex main.tex` twice with Beamer, TikZ, PGFPlots and
booktabs installed. No shell escape or bibliography run is required. The last
slide uses a concise linked bibliography so the requested twelve-slide count
stays fixed; full reusable entries are in `ref.bib`.

Text, diagrams, tables and the PGFPlots charts remain editable in LaTeX.
Presenter notes are embedded using Beamer's `\note{...}` and hidden in the
projected PDF. Change the note option in `main.tex` to produce a notes version.

`data/` contains the small measured chart inputs and result table, included so
the source archive compiles independently of the repository. To regenerate
them inside the repository, run `python presentation/generate_data.py`. The
generator checks the verification records and reads only the committed
twenty-person extension exports; it does not rerun experiments.

Primary and alternative losses are measured relative to each reader's own
baseline. Confidence intervals are pointwise participant-bootstrap intervals.
They are not simultaneous tests, and the plot lines do not add observations.

Image sources:

- `images/logo/IITG.jpg`: official institute banner from
  https://www.iitg.ac.in/core/img/iitglogo.jpg, discovered on the institute's
  homepage. Displayed unchanged, with original proportions.
- `images/eeg-cap.png`: CIV, *EEG Cap - The Noun Project*, CC0 public domain,
  via https://commons.wikimedia.org/wiki/File:EEG_Cap_-_The_Noun_Project.svg.
  The PNG is Wikimedia's raster preview of the original SVG. It is a generic
  illustration, not the OpenBMI recording apparatus.

Numerical source for the introduction: ITU *Facts and Figures 2026*, p. 16.
The 18.2% figure refers to average annual **mobile broadband traffic** growth
since 2021, not all data creation. The 2.83 GB/day EEG example is explicitly
illustrative arithmetic and uses a different representation from the benchmark.
