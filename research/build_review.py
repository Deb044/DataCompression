"""Build the source-grounded review and experiment protocol. No results are simulated."""

from pathlib import Path
from xml.sax.saxutils import escape
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    Flowable,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "eeg_compression_review_and_experiments.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
FONT_DIR = Path("C:/Windows/Fonts")
for name, filename in [("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"),
                       ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")

NAVY = colors.HexColor("#14334B")
TEAL = colors.HexColor("#087F83")
INK = colors.HexColor("#263746")
MUTED = colors.HexColor("#566774")
PALE = colors.HexColor("#EAF5F4")
LINE = colors.HexColor("#D9E3E8")
WIDTH, HEIGHT = A4
MARGIN = 47
CONTENT_WIDTH = WIDTH - 2 * MARGIN

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("Body", fontName="Arial", fontSize=10, leading=14.3,
                          textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle("SmallBody", parent=styles["Body"], fontSize=8.8, leading=12.1, spaceAfter=6))
styles.add(ParagraphStyle("Label", parent=styles["Body"], fontName="Arial-Bold",
                          fontSize=8.5, leading=11, textColor=TEAL, spaceAfter=9))
styles.add(ParagraphStyle("TitleMain", parent=styles["Body"], fontName="Arial-Bold",
                          fontSize=28, leading=32, textColor=NAVY, spaceAfter=14))
styles.add(ParagraphStyle("Section", parent=styles["Body"], fontName="Arial-Bold",
                          fontSize=20, leading=24, textColor=NAVY, spaceAfter=14))
styles.add(ParagraphStyle("Sub", parent=styles["Body"], fontName="Arial-Bold",
                          fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=7, spaceAfter=6,
                          keepWithNext=True))
styles.add(ParagraphStyle("Cell", parent=styles["SmallBody"], fontSize=8.4, leading=11.5, spaceAfter=0))
styles.add(ParagraphStyle("CellHead", parent=styles["Cell"], fontName="Arial-Bold", textColor=colors.white))
styles.add(ParagraphStyle("Reference", parent=styles["SmallBody"], fontSize=8.4, leading=11.5, spaceAfter=9))

refs = [
    ("N. Memon, X. Kong and J. Cinkler", "Context-based lossless and near-lossless compression of EEG signals", "IEEE Transactions on Information Technology in Biomedicine 3(3), 231-238 (1999)", "https://doi.org/10.1109/4233.788586", "Indexed abstract; full text not audited."),
    ("G. Higgins, B. McGinley, E. Jones and M. Glavin", "An evaluation of the effects of wavelet coefficient quantisation in transform based EEG compression", "Computers in Biology and Medicine 43(6), 661-669 (2013)", "https://doi.org/10.1016/j.compbiomed.2013.02.011", "Indexed abstract; lawful manuscript at PMC4754580, intermittently inaccessible."),
    ("S. Zhang, K. Ma, Y. Yin, B. Ren and M. Liu", "A Personalized Compression Method for Steady-State Visual Evoked Potential EEG Signals", "Information 13(4), 186 (2022)", "https://doi.org/10.3390/info13040186", "Open full text."),
    ("T. Strypsteen and A. Bertrand", "Neural Source Coding for Bandwidth-Efficient Brain-Computer Interfacing with Wireless Neuro-Sensor Networks", "ICASSP (2023)", "https://homes.esat.kuleuven.be/~abertran/reports/Strypsteen_ICASSP2023.pdf", "Open author manuscript."),
    ("X. Wang, J. Zhang and X. Wu", "A feature enhanced EEG compression model using asymmetric encoding-decoding network", "Journal of Neural Engineering 21(3) (2024)", "https://doi.org/10.1088/1741-2552/ad48ba", "PubMed abstract, PMID 38718785; full-text methods not audited."),
    ("F. S. Carzaniga, G. Hoppeler, M. Hersche, K. A. Schindler and A. Rahimi", "The Case for Cleaner Biosignals: High-fidelity Neural Compressor Enables Transfer from Cleaner iEEG to Noisier EEG", "ICLR (2025)", "https://proceedings.iclr.cc/paper_files/paper/2025/file/28c9ce39a89c03f0bdd9725907d5abbc-Paper-Conference.pdf", "Open conference paper; EEG/iEEG BrainCodec, distinct from an fMRI codec of the same name."),
    ("A. Kastrati, L. Lanzendoerfer, R. Rigoni, J. Staib Matilla and R. Wattenhofer", "Adapting Neural Audio Codecs to EEG", "arXiv:2511.23142 (2025)", "https://arxiv.org/abs/2511.23142", "Preprint; abstract assessed. Archival peer-review status not verified."),
    ("C. Xie", "Adaptive Data Compression and Reconstruction for Memory-Bounded EEG Continual Learning", "arXiv:2605.03085 (2026)", "https://arxiv.org/abs/2605.03085", "Preprint; full text available. Findings are provisional."),
    ("Y. Zhang, S. Q. Xie, H. Wang, C. Shi and Z.-Q. Zhang", "Bayesian-based Classification Confidence Estimation for Enhancing SSVEP Detection", "IEEE Transactions on Instrumentation and Measurement 72, 6503612 (2023)", "https://eprints.whiterose.ac.uk/id/eprint/199879/", "Open accepted manuscript; DOI 10.1109/TIM.2023.3284952. Adjacent confidence study."),
    ("A. Damoah and T. Liang", "Optimizing Multichannel EEG Data: An Investigation of Current EEG Data Compression Methods", "Author-posted manuscript listing KDD Undergraduate Consortium (2024)", "https://faculty.cs.gwu.edu/xiaodongqu/papers/KDD_2024_Compression_Andrews.pdf", "Contextual review only. The manuscript has a placeholder DOI; archival publication status not verified."),
    ("Y. Wang, X. Chen, X. Gao and S. Gao", "A Benchmark Dataset for SSVEP-Based Brain-Computer Interfaces", "IEEE Transactions on Neural Systems and Rehabilitation Engineering 25(10), 1746-1752 (2017)", "https://doi.org/10.1109/TNSRE.2016.2627556", "Dataset information: https://bci.med.tsinghua.edu.cn/download.html. Published online in 2016; journal issue 2017."),
    ("G. Schalk", "EEG Motor Movement/Imagery Dataset, version 1.0.0", "PhysioNet (2009)", "https://physionet.org/content/eegmmidb/1.0.0/", "Official dataset documentation. Dataset DOI 10.13026/C28G6P."),
    ("P. Deutsch", "DEFLATE Compressed Data Format Specification version 1.3", "RFC 1951 (1996)", "https://www.rfc-editor.org/rfc/rfc1951", "Public format specification; explains LZ77 and Huffman coding."),
    ("ITU-T", "G.711: Pulse code modulation (PCM) of voice frequencies", "Recommendation G.711 (11/1988)", "https://www.itu.int/rec/T-REC-G.711-198811-I/en", "Voice-coding context only; a custom EEG compander is not automatically G.711 compliant."),
]

def cite(*numbers):
    return " ".join(f'<link href="{refs[n-1][3]}" color="#087F83">[{n}]</link>' for n in numbers)

story = []

def p(text, small=False):
    story.append(Paragraph(text, styles["SmallBody" if small else "Body"]))

def sub(title, text=None):
    story.append(Paragraph(title, styles["Sub"]))
    if text:
        p(text)

def page(number, title):
    if story:
        story.append(PageBreak())
    story.append(Paragraph(f"{number:02d} / EEG COMPRESSION", styles["Label"]))
    story.append(Paragraph(title, styles["Section"]))

def callout(title, text):
    items = [Paragraph(title, styles["Sub"]), Paragraph(text, styles["Body"])]
    box = Table([[items]], colWidths=[CONTENT_WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE),
                            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                            ("LEFTPADDING", (0, 0), (-1, -1), 12),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                            ("TOPPADDING", (0, 0), (-1, -1), 7),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.extend([box, Spacer(1, 10)])

def table(headers, rows, proportions):
    cells = [[Paragraph(x, styles["CellHead"]) for x in headers]]
    cells.extend([[Paragraph(x, styles["Cell"]) for x in row] for row in rows])
    t = Table(cells, colWidths=[CONTENT_WIDTH * x for x in proportions], repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY),
                          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F9")]),
                          ("VALIGN", (0, 0), (-1, -1), "TOP"),
                          ("LEFTPADDING", (0, 0), (-1, -1), 8),
                          ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                          ("TOPPADDING", (0, 0), (-1, -1), 8),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                          ("LINEBELOW", (0, 0), (-1, 0), 0.5, NAVY),
                          ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE)]))
    story.extend([t, Spacer(1, 9)])


class Pipeline(Flowable):
    def __init__(self):
        super().__init__()
        self.width = CONTENT_WIDTH
        self.height = 76

    def draw(self):
        labels = [("EEG", "fixed preprocessing"), ("Quantize", "introduces loss"),
                  ("Pack + ZIP", "lossless storage"), ("Reconstruct", "then FFT + decision")]
        box_w = (self.width - 3 * 14) / 4
        for i, (title, desc) in enumerate(labels):
            x = i * (box_w + 14)
            self.canv.setFillColor(PALE)
            self.canv.setStrokeColor(LINE)
            self.canv.roundRect(x, 12, box_w, 52, 5, fill=1, stroke=1)
            self.canv.setFillColor(NAVY)
            self.canv.setFont("Arial-Bold", 9)
            self.canv.drawCentredString(x + box_w / 2, 43, title)
            self.canv.setFont("Arial", 7.5)
            self.canv.drawCentredString(x + box_w / 2, 27, desc)
            if i < 3:
                self.canv.setStrokeColor(TEAL)
                self.canv.line(x + box_w + 2, 38, x + box_w + 12, 38)
                self.canv.line(x + box_w + 9, 41, x + box_w + 12, 38)
                self.canv.line(x + box_w + 9, 35, x + box_w + 12, 38)


story.append(Paragraph("DA3021 / COURSE PROJECT / 24 NOVEMBER 2026", styles["Label"]))
story.append(Paragraph("Compressing EEG:<br/>What Must Survive?", styles["TitleMain"]))
p("A rapid structured literature review and two controlled experiment protocols")
callout("The project question", "How much can we reduce EEG storage while preserving useful decisions, and which recordings lose those decisions first?")
p("EEG is a collection of sampled voltage signals. Compression can preserve every recorded value, preserve the waveform approximately, or prioritize information needed for a particular analysis. These goals overlap, but they are not interchangeable. Our review follows that progression from lossless coding to task-aware and neural methods.")
p("The literature already establishes that EEG can be compressed and evaluated through downstream tasks. Our contribution will be a transparent synthesis and a small, reproducible experiment using familiar course ideas: quantization, Fourier analysis, spectral features and lossless coding. A new algorithm or a positive result is not required.")
sub("Scope and evidence status")
p("Coverage: representative EEG waveform-compression work from 1999 through the search cutoff of <b>24 November 2026</b>. Eight core studies, one adjacent confidence paper, one contextual review and four dataset/format references are included. Two core works are labelled preprints. This is a rapid review with systematic elements, not an exhaustive systematic review or meta-analysis.")
callout("No experimental results yet", "This document reports literature findings and a proposed protocol. No EEG experiments have been run for this report. All planned comparisons, plots and success criteria below are prospective.")
table(["Reading map", "Pages"], [
    ["Foundations and measurement", "2"], ["Evidence map and research gaps", "3-4"],
    ["Two experiment protocols", "5-6"], ["Reading path and presentation storyline", "7"],
    ["References and search audit", "8-9"],
], [0.82, 0.18])

page(2, "From fewer bytes to useful decisions")
sub("1. Lossless coding preserves the chosen input exactly")
p("ZIP is a container that can use several compression methods. DEFLATE combines repeated-sequence coding with Huffman coding. It operates on bytes, without knowing which EEG feature matters. Quantization is a separate operation: once values are rounded, ZIP preserves those rounded values exactly, not the original waveform." + cite(13))
p("Early EEG work compared general-purpose and predictive lossless methods, then explored bounded-error near-lossless coding. That establishes a useful baseline: storage can be reduced without introducing a classification trade-off, but the achievable gain depends on the representation and redundancy." + cite(1))
sub("2. Quantization exchanges precision for storage")
p("For channel values between endpoints a and z, b bits provide L = 2<super>b</super> levels. Uniform quantization rounds each sample to its nearest level, with step (z - a)/(L - 1). The endpoints or an equivalent scale must be stored. The often-used noise approximation, step squared divided by 12, requires assumptions about quantization error; it is not guaranteed for a particular EEG recording.")
p("Transform coding first expresses the signal using coefficients, then quantizes or discards selected coefficients. Higgins and colleagues explicitly compared coefficient quantization with thresholding in a wavelet-based EEG codec. Our sample-domain quantizer is a simple baseline, not a reproduction of that method." + cite(2))
story.append(Pipeline())
sub("3. Waveform fidelity and task fidelity need separate measurements")
p("A low mean-squared error measures numerical similarity; it does not establish that a particular decision survives. Conversely, an unchanged decision does not establish faithful recovery of everything in the recording. Published task-aware and neural studies therefore provide important precedents for checking reconstructed EEG through downstream analysis." + cite(3, 4, 5, 6))
table(["Measure", "Definition for our experiment"], [
    ["Stored size", "Bytes in the actual archive, including scales, shape, bit depth, padding and container overhead. Also report bytes per second per channel."],
    ["Waveform distortion", "NRMSE = ||x - reconstructed x|| / ||x - mean(x)||, pooling the declared channels and samples. State this mean-removal convention; constant inputs need a separate flag."],
    ["Task effect", "True-label accuracy change, prediction-flip rate and the fraction of originally correct decisions that become wrong."],
], [0.25, 0.75])
p("<b>Brief mu-law bridge.</b> A logarithmic compander gives relatively finer resolution near zero and coarser resolution at large magnitudes. It motivates an optional quantizer comparison. A custom continuous mu-law experiment on normalized EEG would not be a bit-exact implementation of the G.711 voice standard." + cite(14), small=True)

page(3, "Evidence map: what is established?")
p("Each row summarizes what a source reports. The interpretation column states its relevance to this project, not an independent validation of the authors' results. A = abstract-level assessment; F = full text available for focused reading.", small=True)
table(["Study / access", "Approach and evidence", "Implication for our project"], [
    ["Memon et al.<br/>1999 / A " + cite(1), "Compares lossless methods and explores bounded-error near-lossless EEG coding.", "General-purpose compression and controlled loss have a long history; ZIP alone is a baseline."],
    ["Higgins et al.<br/>2013 / A " + cite(2), "Compares wavelet-coefficient quantization with thresholding within SPIHT compression.", "Reducing precision before entropy coding is established; our simple quantizer teaches that trade-off."],
    ["Zhang et al.<br/>2022 / F " + cite(3), "Personalized SSVEP compression combines a transform, neural reconstruction and nonuniform residual quantization; evaluates recognition.", "SSVEP accuracy versus compression is prior work, not our novelty claim."],
    ["Strypsteen and Bertrand<br/>2023 / F " + cite(4), "Jointly learns source coding and inference for motor execution in an emulated wireless EEG network; compares low-bit quantization.", "Task-specific coding and sensor-node bit allocation already exist. Their jointly trained decoder differs from our frozen decoder."],
    ["Wang et al.<br/>2024 / A " + cite(5), "Asymmetric neural encoding/decoding; evaluates reconstructed EEG on ERP and motor-imagery tasks.", "A small encoder and multiple downstream tasks are established evaluation directions."],
    ["Carzaniga et al.<br/>2025 / F " + cite(6), "BrainCodec explores training transfer between iEEG and EEG, with reconstruction, downstream tasks and expert assessment.", "Data domain and training distribution matter; a reported ratio is not a universal safe setting."],
    ["Kastrati et al.<br/>2025 / A; preprint " + cite(7), "Adapts pretrained neural audio coding to EEG and explores channel structure, sampling and quantization choices.", "Audio-to-EEG adaptation is already being explored; this is not evidence that ordinary MP3 preserves EEG."],
    ["Xie<br/>2026 / F; preprint " + cite(8), "ADaCoRe combines resampling, protected timepoints and confidence-based replay-example selection for continual learning.", "Confidence and EEG compression already coexist. Selecting examples differs from selecting each trial's bit depth."],
], [0.24, 0.40, 0.36])
p("<b>Adjacent evidence:</b> SSVEP confidence estimation uses separation among recognition scores to assess reliability. This motivates our trial-level hypothesis, but does not establish that the same gap predicts quantization damage." + cite(9), small=True)
p("A 2024 author-posted review also maps multichannel EEG compression. Its manuscript contains a placeholder DOI; we use it for orientation, not as a verified archival benchmark." + cite(10), small=True)

page(4, "Synthesis: gaps we can investigate")
sub("What the selected literature supports")
p("The reviewed approaches span exact reconstruction, bounded or approximate waveform recovery, and preservation of application performance. Learned and task-aware methods can be effective in their tested settings. These findings do not provide a single compression ratio, bit depth or distortion threshold that applies to every dataset, recording setup and decoder.")
sub("Gap A / Comparable storage accounting")
p("Published methods use different input precisions, channel sets, datasets and definitions of compression rate. Some optimize transmission from sensor nodes; others reconstruct full recordings. Our synthesis is that their headline ratios should not be ranked without aligning those assumptions. <b>Our attempt:</b> report actual archive sizes against a declared input representation, with all reconstruction metadata counted.")
sub("Gap B / Aggregate accuracy can hide trial-level failures")
p("A small overall accuracy change can coexist with some correct predictions becoming wrong and other wrong predictions becoming correct. The selected task-preserving studies motivate examining downstream behavior, but their headline summaries do not answer which of our individual trials will fail. <b>Our attempt:</b> retain each trial's label, original prediction and reconstructed prediction throughout the precision sweep.")
sub("Gap C / Reliability is not necessarily compression tolerance")
p("The confidence paper estimates whether an original decision is reliable. ADaCoRe uses confidence for replay-example selection. Neither mechanism, as described in the reviewed material, establishes that a raw top-two score gap is a reliable rule for allocating our quantization bits. <b>Our attempt:</b> test that relationship against a shuffled-score control and simple waveform predictors." + cite(8, 9))
sub("Gap D / Evidence across tasks and participants")
p("Multiple-task evaluations already exist. What remains open for our small experiment is whether a simple relationship learned on development participants repeats on unseen participants, and eventually another task. <b>Our attempt:</b> separate development and evaluation participants. A second EEG task is optional; differences between two datasets cannot isolate a causal effect of task alone.")
callout("How to phrase these gaps", "These are limitations and unanswered questions within the reviewed evidence and our proposed setup. They are not claims that the entire field has ignored storage accounting, trial-level analysis or confidence-aware methods.")
p("<b>Critical comparison:</b> a decoder retrained jointly with a compressor can adapt to distortion; a frozen original decoder cannot. These are different deployment questions. Our experiment deliberately measures compatibility with an existing analysis pipeline. It cannot establish superiority to published neural compressors.")
p("<b>Scope boundary:</b> this is a storage and analysis experiment. Computing the original decision at the encoder has a cost. We will not infer energy savings or clinical suitability from fewer stored bytes.", small=True)

page(5, "Experiment 1 / How many bits are enough?")
callout("Question and status", "How do actual storage, waveform error and target-recognition accuracy change as EEG precision decreases? Planned experiment; no result is assumed.")
sub("Data and a fixed, interpretable task")
p("Use a small subset of the public SSVEP benchmark. The original dataset has 35 participants, 64 channels and 40 stimulus targets. Start with S1-S2 for development, then S3-S8 for evaluation if downloads and time permit; disclose any smaller final subset. Read channel names, frequencies and trial timing from the official metadata." + cite(11))
p("Predeclare four widely separated targets, 9, 11, 13 and 15 Hz, verifying their metadata entries. This is a simplified four-class task with 25% chance accuracy, not the full benchmark. Use O1, Oz and O2 and a four-second interval fully inside stimulation, fixed after checking onset metadata on development data. Keep all trials for the chosen targets; do not select participants or trials for high accuracy.")
sub("Decoder and precision sweep")
p("Store the mean-centered trial segment before windowing. For both original and reconstructed segments, remove any remaining mean, apply one Hann window and compute an FFT. Score candidates by summed fundamental and second-harmonic power across channels. Freeze the bin rule, normalization and weights on development data. If the original decoder is weak, disclose it; do not tune using evaluation labels.")
p("Compress the same fixed preprocessed waveform at b = 16, 12, 8, 6, 4 and 2 bits. For each trial/channel, use uniform quantization with recorded minimum and maximum endpoints. Pack b-bit codes into bytes and archive them with one fixed ZIP configuration. Store endpoints, dimensions, bit depth and padding rules. Reconstruct from the stored archive before recomputing the same FFT scores.")
table(["Control", "Why it is needed"], [
    ["Unquantized input + ZIP", "Lossless reference; verify byte-for-byte reconstruction of the chosen float32 representation."],
    ["Quantization without ZIP", "Separates savings from lower precision from further lossless savings."],
    ["Same trials and decoder", "Makes changes paired; preprocessing and classifier settings stay fixed through the sweep."],
    ["Declared denominator", "Primary ratio uses the selected preprocessed float32 payload. Separately report any native-integer baseline; never imply float32 was the original acquisition resolution."],
], [0.29, 0.71])
sub("Outputs and interpretation")
p("Plot accuracy versus actual bytes per second per channel, and NRMSE versus the same storage measure. Show participant-level paired changes and a trial transition table: correct-to-correct, correct-to-wrong, wrong-to-correct and wrong-to-wrong. Add one waveform/spectrum example using a predeclared selection rule. Do not assume accuracy decreases monotonically as bits fall.")
p("Optional only after the main run: add a continuous mu-law compander with a fixed mu = 255 and the same endpoint handling. Compare its measured storage-accuracy curve against uniform quantization; equal bit depth does not guarantee equal ZIP size. This would be a baseline comparison, not a novel codec.", small=True)

page(6, "Experiment 2 / Which trials fail first?")
callout("Hypothesis, not a finding", "At a fixed precision, trials with smaller original top-two score gaps may be more likely to change their predicted target. Confidence and quantization sensitivity need not agree.")
sub("Use the same data; change one question")
p("Reuse every reconstructed trial from Experiment 1. For the original nonnegative candidate scores s1 >= s2, define gap g = (s1 - s2)/(s1 + s2 + epsilon), with a fixed small epsilon for zero scores. This is a score-separation index, not a calibrated probability and not a new confidence estimator." + cite(9))
p("On development participants only, define low, middle and high gap groups using pooled tertiles. Freeze these thresholds before applying them to evaluation participants. Quantization parameters and decoding stay unchanged. Report group counts: a tiny group is weak evidence, even if its rate looks dramatic.")
sub("Two outcomes keep the interpretation honest")
p("<b>Decision stability:</b> among all trials, how often does the reconstructed prediction differ from the original? <b>Useful-decision loss:</b> among originally correct trials, how often does quantization make them wrong? Report originally wrong trials separately. Preserving a wrong prediction is stability, not recovered accuracy.")
table(["Comparison", "Controlled purpose"], [
    ["Gap groups at each bit depth", "Tests whether original separation is associated with later failures. Use participant-level rates; repeated versions of a trial are not independent observations."],
    ["Shuffled gap control", "Shuffle gaps among trials within each participant and true target, retaining the outcome and data. Repeat with a declared seed; this tests information beyond participant and target membership."],
    ["Simple signal predictors", "Compare amplitude range relative to RMS and spectral concentration against the score gap. Assess failure-prediction ranking, such as ROC AUC, only when failure and nonfailure cases both exist; otherwise report it as undefined."],
], [0.31, 0.69])
sub("Predeclared reporting")
p("Show failure rate versus bit depth for the three gap groups, plus participant-level differences between low- and high-gap trials. Use a participant bootstrap for uncertainty only if enough evaluation participants remain; with a tiny sample, show every participant instead of a precise-looking interval. If no failures occur, lower precision is a follow-up condition, not a hidden replacement of the reported sweep.")
sub("Optional extension: allocate bits, rather than just predict failures")
p("Choose a two-level precision rule using development data. On evaluation trials, compare gap-guided allocation with uniform precision and randomized allocation using the same count of high/low-bit assignments. Count actual metadata and archive bytes; random assignments may change ZIP size. Compare overlapping storage budgets or show the full curves. Do not choose settings using evaluation accuracy.")
p("<b>Useful null result:</b> if the gap is no better than simple signal statistics or the shuffled control, the project shows a limit of translating classification confidence into compression policy. That is a valid finding. We must report the observation before suggesting an explanation.", small=True)

page(7, "Reading pathway and presentation flow")
table(["Stage / background", "Read, notice and use"], [
    ["1. Entry / bits and bytes", "RFC 1951: begin with the overview rather than format minutiae. Notice how repetition coding and variable-length codes work together. Use it for the ZIP foundation." + cite(13)],
    ["2. Field orientation / sampled signals", "Damoah-Liang's author-posted review offers a short method map. Treat its publication metadata cautiously; use it to identify families, not to certify performance rankings." + cite(10)],
    ["3. Quantization / basic transforms", "Higgins et al. is a bridge from a rounding operation to transform coding. Begin with the abstract; full text is linked through PMC when accessible. Distinguish coefficient coding from our sample-domain baseline." + cite(2)],
    ["4. Application / FFT and SSVEP", "Read Zhang et al.'s SSVEP method and evaluation. Notice that preserving target recognition is already an explicit goal. The proposed project follows that evaluation principle without reproducing its neural pipeline." + cite(3)],
    ["5. Technical grounding / ML basics", "Read Strypsteen-Bertrand for joint optimization of bitrate and inference. Then read the SSVEP confidence paper. Notice the difference between an uncertain decision and a decision vulnerable to quantization." + cite(4, 9)],
    ["6. Modern evidence and frontier / neural networks", "Read the ICLR EEG/iEEG BrainCodec paper, then the audio-adaptation and ADaCoRe preprints. Notice distribution transfer, input framing and example selection; these are distinct mechanisms, not one generic idea of compression." + cite(6, 7, 8)],
], [0.28, 0.72])
sub("A nine-minute storyline")
p("<b>0:00-1:00 - Motivation:</b> EEG generates multiple sampled signals; what information must storage preserve?<br/><b>1:00-2:15 - Course connection:</b> bits, ZIP, quantization, a short mu-law bridge, FFT and SSVEP.<br/><b>2:15-3:45 - Literature:</b> exact values -> approximate waveform -> useful decisions. Show three representative papers and the evidence map.<br/><b>3:45-6:00 - Experiment 1:</b> real storage-accuracy curves, reconstruction examples and the controls.<br/><b>6:00-7:30 - Experiment 2:</b> gap groups, failures and the shuffled control.<br/><b>7:30-9:00 - Learning and reflection:</b> what happened, what surprised us, limitations, next steps and references.")
sub("Delivery priorities before 25 November EOD")
p("First finish the lossless control and one participant's end-to-end run. Then freeze the protocol and run the small evaluation subset. Generate figures and log all deviations before polishing the site and slides. Reserve time for the presentation PDF, a sub-10-minute recording and link-access checks. If time is tight, keep the review plus Experiment 1 and make Experiment 2 a documented attempt.")
p("An eyes-open/closed task is an optional later extension using the PhysioNet baselines and alpha-power features. It requires its own participant split and evaluation; its binary accuracy should not be directly ranked against four-class SSVEP accuracy." + cite(12), small=True)

page(8, "References and access notes")
p("Numbered links in the text open the source. Titles and metadata were checked against primary publication records or author manuscripts. Access notes distinguish full-text availability from abstract-level assessment.", small=True)
for n, (authors, title, venue, url, note) in enumerate(refs, 1):
    text = f'<b>[{n}] {escape(authors)}.</b> {escape(title)}. {escape(venue)}. '
    text += f'<link href="{escape(url)}" color="#087F83">Source / DOI</link>. {escape(note)}'
    story.append(Paragraph(text, styles["Reference"]))

page(9, "Search audit and limits of the review")
log = json.loads((ROOT / "research" / "search_log.json").read_text(encoding="utf-8"))
sub("How sources were found")
p("Search cutoff: 24 November 2026. General web discovery was followed by verification on PubMed, journal and conference pages, institutional repositories, arXiv and official dataset pages. Reference lists in the task-aware and confidence papers provided backward links. We did not perform a reproducible export of every result from IEEE Xplore, Scopus or Web of Science.")
p("The accompanying search log records the query strings and inclusion/exclusion criteria. It is an audit of the searches used, not a registered systematic-review protocol. Source selection is purposive and representative. Search ranking, English-language coverage, access restrictions and a single reviewer can affect the selected set.")
sub("Representative executed queries")
for q in [log["queries_executed"][0], log["queries_executed"][1],
          log["queries_executed"][10], log["queries_executed"][14]]:
    p(escape(q), small=True)
sub("Inclusion, exclusions and selected-reference counts")
p("Included direct compression of recorded EEG with reconstruction or task evaluation, spanning classical and learned methods. A confidence paper and a review manuscript were retained as adjacent context. Excluded model-weight compression without input-signal coding, fMRI-only studies, compression-as-complexity studies, and unverified repository benchmark claims.")
p("Selected set: <b>8 core papers + 1 confidence paper + 1 contextual review + 4 dataset/format references = 14 references</b>. These are bibliography counts. The total number of screened candidates was not recorded, so a PRISMA flow count would be misleading.")
sub("Quality appraisal and missing evidence")
p("This is a qualitative synthesis, not a pooled effect estimate. Full-text access was uneven: several older or publisher-restricted studies were assessed through complete indexed abstracts. We did not audit their code, reproduce reported results, or verify every compression denominator and train/test split. Those unknowns are not evidence that the original authors omitted them.")
p("No head-to-head numerical ranking is defensible from this review. Clinical safety, hardware energy, performance after long-term distribution shift, and preservation of every future analysis remain outside our proposed experiments. Preprints provide context, not established consensus. A failed exact-keyword search cannot establish a globally new idea.")
callout("Transparent project statement", "We review established EEG compression methods and conduct controlled exploratory tests of a simple quantization-and-ZIP pipeline. We report measured outcomes and limitations, and investigate score-gap-guided preservation as a hypothesis rather than a claimed first contribution.")
p("<b>Assistance disclosure:</b> AI assistance was used for literature discovery, synthesis and protocol drafting. The report distinguishes source reports from proposed experiments. The student should read the central papers, verify the experiment implementation, and cite the LLM assistance used in the final submission.", small=True)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 37, WIDTH - MARGIN, 37)
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 23, "EEG compression | Rapid structured review | 24 Nov 2026")
    canvas.drawRightString(WIDTH - MARGIN, 23, str(doc.page))
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN,
                        topMargin=42, bottomMargin=50, title="Compressing EEG: What Must Survive?",
                        author="DA3021 project working review; prepared with AI assistance")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
