# EEG Compression presentation

The current presentation contains thirteen slides: a title and twelve content
slides. It uses a plain white, widescreen layout, Arial text and restrained teal
headings, inspired by the supplied video and neural signal reference slides.
Author: Debarghya Das, 240150049. Date: 25 November 2026.

Download the [editable PowerPoint](../output/presentation/eeg-compression.pptx)
or [PDF](../output/presentation/eeg-compression.pdf). PowerPoint contains native
charts and tables, embedded chart workbooks, linked references and presenter
notes. The companion PDF uses high-resolution slide renders and retains the
reference hyperlinks. Edit text and chart values in the PowerPoint.

## Source and rebuilding

`build.mjs` creates the white presentation using the bundled `@oai/artifact-tool`
and `pdf-lib` packages. It reads `data/study.json` and `speaker-notes.json`.
Set `RUNTIME_NODE_MODULES` to the bundled runtime's Node packages, then run:

```text
node presentation/build.mjs
```

The build writes draft files and slide previews to `tmp/presentation-redesign`.
An optional first argument changes that private output directory. The released
PowerPoint also packages each chart's literal values as an embedded workbook.
Chart values use six decimal places in percentage points for Excel compatibility.
Full precision remains in the JSON source.

To refresh measured inputs from the repository:

```text
python presentation/generate_data.py
```

The generator checks the verification records and reads only the committed
twenty-person extension exports. It does not rerun experiments. Earlier `.tex`
files and the LaTeX archive preserve the previous presentation, and are not used
to build the current white design.

## Evidence and references

Primary and alternative losses are relative to each reader's own baseline.
The results curves show means and connect only tested storage settings.
The summary plot retains paired participant-bootstrap 95% intervals. Complete
pointwise intervals and individual measurements remain on the project website.
The references slide includes the website and ChatGPT 6 attribution.

The introduction's 18.2% statistic is average annual **mobile broadband traffic**
growth since 2021, from ITU *Facts and Figures 2026*, p. 16. It does not measure
all data creation. The 2.83 GB/day EEG example is illustrative arithmetic and
uses a different representation from the benchmark.

`images/eeg-cap.png` is CIV's *EEG Cap - The Noun Project*, CC0 public domain,
via https://commons.wikimedia.org/wiki/File:EEG_Cap_-_The_Noun_Project.svg.
`images/eeg-cap-white.jpg` is the same illustration on white for file
compatibility. It is a generic illustration, not the OpenBMI apparatus.

Design references: [Coswara presentation](https://www.youtube.com/watch?v=qjDDt1vJ4_M)
and the user-supplied neural signal capture PDF, especially pp. 165-173.
The full research bibliography remains in `ref.bib`; slide-specific citations
are in the presenter notes.
