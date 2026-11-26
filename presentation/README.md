# Every Bit of the Brain

The presentation is titled **Every Bit of the Brain**, with the subtitle
**How much EEG data can be lost?** It contains sixteen slides.
The opening separates data growth from the need for compression, and the
results table has its own slide. A final Thank You slide after the references
links to the website and repository. The OpenBMI dataset citation uses the same style as the other
references, with full bibliographic details in the notes. Content slides place
text on the left and visual evidence on the right. The references use two
uniform columns. The final slide contains only centered thanks and two links. Headings and subheadings are turquoise,
with grey/black body text and a consistent Arial size hierarchy.
Author: Debarghya Das, 240150049. Date: 25 November 2026.

Download the [editable PowerPoint](../output/presentation/every-bit-of-the-brain.pptx)
or [PDF](../output/presentation/every-bit-of-the-brain.pdf). PowerPoint contains native
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

The build writes draft files and slide previews to `tmp/presentation-uniform`.
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
The references slide includes the OpenBMI dataset and ChatGPT 6 attribution.
The following Thank You slide contains clickable website and repository links.

The data-growth graph uses selected IDC report editions: 33 ZB estimated for
2018, 64.2 ZB estimated for 2020 (as reported by UNCTAD), and a 393.9 ZB forecast
for 2028 from IDC's 2024 report, reproduced by Seagate. The forecast is labelled
explicitly and is not presented as an observed total. These figures include
created/replicated data and are not storage capacity or unique information.
The quote by Ginni Rometty comes from IBM Digital Analytics.

`data/zip-example.json` is a separate teaching example: 65,536 bytes of repeated
text become a 370-byte ZIP archive in the committed run. The generator includes
archive overhead and verifies exact recovery. This is not an EEG result.
The quantization plot is an illustrative sine wave. The 2.83 GB/day example is
arithmetic for a 64-channel raw recording, not our benchmark representation.

`images/eeg-cap.png` is CIV's *EEG Cap - The Noun Project*, CC0 public domain,
via https://commons.wikimedia.org/wiki/File:EEG_Cap_-_The_Noun_Project.svg.
`images/eeg-cap-white.jpg` is the same illustration on white for file
compatibility. It is a generic illustration, not the OpenBMI apparatus.
`images/eeg-traces-reference.jpg` is the multichannel illustration from p. 172
of the supplied neural signal capture reference. Its underlying recording is
not identified there, and it is not used as experimental evidence.

Design references: [Coswara presentation](https://www.youtube.com/watch?v=qjDDt1vJ4_M)
and the user-supplied neural signal capture PDF, especially pp. 165-173.
The full research bibliography remains in `ref.bib`; slide-specific citations
are in the presenter notes.

The experiment slides call the primary decoder **Decoder 1** and the alternative
decoder **Decoder 2**, explain score loss in percentage points, and retain the
original measurements. Exact algorithm names and protocol details remain in
the presenter notes.

The current edition labels the summary discussion **Reflections** and emphasizes
variation across decoder and compressor choices. The limitations begin with the
exploratory nature of the study and its opportunities for scaling up. Results and
research tables sit directly below their headings, with explanations immediately
below them. The numerical results are unchanged.

The lossless/lossy research slide contrasts LPC and AR prediction with
transform coding using DCT and DWT. It explains exact residual coding and
coefficient quantization without claiming that a predictor alone is lossless
or that the transforms themselves discard information.
