/** Build the white-background, editable presentation from verified study exports.
 * Run with the bundled Node runtime and RUNTIME_NODE_MODULES set to its packages.
 * Optional first argument: private output directory (default: tmp/presentation-redesign).
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const out = path.resolve(process.argv[2] ?? path.join(root, 'tmp/presentation-redesign'));
const packages = process.env.RUNTIME_NODE_MODULES ?? process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
if (!packages) throw new Error('Set RUNTIME_NODE_MODULES to the bundled Node packages.');
const runtimeRequire = createRequire(path.join(packages, '__presentation__.cjs'));
const { Presentation, PresentationFile } = await import(
  pathToFileURL(runtimeRequire.resolve('@oai/artifact-tool')).href);
const { PDFDocument, PDFName, PDFString } = runtimeRequire('pdf-lib');
const data = JSON.parse(await fs.readFile(path.join(here, 'data/study.json'), 'utf8'));
const notes = JSON.parse(await fs.readFile(path.join(here, 'speaker-notes.json'), 'utf8'));

const colors = { ink: '#222222', muted: '#606060', teal: '#337F79',
  SSVEP: '#267C72', MI: '#C2603B', ERP: '#4968B1' };
const font = 'Arial';
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const hyperlinks = [];

function text(slide, value, x, y, w, h, size = 28, color = colors.ink, bold = false) {
  const box = slide.shapes.add({ geometry: 'textbox',
    position: { left: x, top: y, width: w, height: h },
    fill: 'none', line: { fill: 'none', width: 0 } });
  box.text = value;
  box.text.style = { typeface: font, fontSize: size, color, bold,
    insets: 0, verticalAlignment: 'top', autoFit: 'none', wrap: 'word' };
  return box;
}
function link(slide, label, url, x, y, w, size = 18) {
  const box = text(slide, label, x, y, w, 45, size, colors.teal);
  box.hyperlink = { uri: url, isExternal: true };
  hyperlinks.push({ slide: deck.slides.items.indexOf(slide), url, x, y, w, h: 45 });
  return box;
}
function slide(title) {
  const s = deck.slides.add();
  s.background.fill = '#FFFFFF';
  if (title) text(s, title, 64, 42, 1152, 68, 42, colors.teal, true);
  text(s, String(deck.slides.items.length), 1190, 676, 35, 24, 16, '#888888');
  s.speakerNotes.text = notes[deck.slides.items.length - 1];
  return s;
}
function caption(s, value) { text(s, value, 64, 642, 1120, 40, 17, colors.muted); }
// Excel chart workbooks support 15 significant digits. Six decimal places in
// percentage points exceed the displayed precision without altering source data.
function chartNumber(value) { return Number(value.toFixed(6)); }
function estimate(family, task, method, budget) {
  const value = data[family].groups.find(g => g.task === task && g.method === method && g.budget === budget);
  if (!value) throw new Error(`Missing measured result: ${family}/${task}/${method}/${budget}`);
  return value;
}
function nativeTable(s, values, x, y, w, h, widths, size = 23) {
  const table = s.tables.add({ rows: values.length, columns: values[0].length,
    left: x, top: y, width: w, height: h, columnWidths: widths, values });
  table.borders.assign({ fill: '#D9DEDD', width: 0.5, style: 'solid' });
  table.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({
    fill: '#FFFFFF', textStyle: { typeface: font, fontSize: size, color: colors.ink },
    margins: { left: 12, right: 12, top: 4, bottom: 4 } });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: values[0].length }).assign({
    fill: '#F1F5F4', textStyle: { typeface: font, fontSize: size, bold: true, color: colors.ink } });
  return table;
}

// 1. Plain title slide, with personal details confined to this slide.
{
  const s = slide();
  text(s, 'EEG Compression', 84, 174, 1100, 100, 70, colors.teal, true);
  text(s, 'Compression and task performance', 88, 294, 1060, 62, 34);
  text(s, 'Debarghya Das\n240150049', 88, 424, 680, 86, 28);
  text(s, 'Mehta Family School of Data Science and Artificial Intelligence\nIndian Institute of Technology Guwahati', 88, 534, 1050, 70, 22, colors.muted);
  text(s, '25 November 2026', 88, 625, 600, 36, 22, colors.muted);
}

// 2. Motivation. This statistic is network traffic, not global data creation.
{
  const s = slide('Why compression matters');
  text(s, '+18.2%', 64, 198, 510, 130, 102, colors.teal);
  text(s, 'Average annual growth in\nmobile broadband traffic\n2021–2026', 70, 352, 490, 146, 28, colors.muted);
  text(s, 'Video, speech and sensors\nproduce growing streams of data.', 650, 206, 560, 130, 34);
  text(s, 'LLMs, robotics and multimodal\nsystems depend on that data.', 650, 388, 560, 120, 30);
  text(s, 'Fewer bytes to store and transmit', 70, 552, 1110, 62, 34, colors.teal);
  caption(s, 'ITU, Facts and Figures 2026. This measures network traffic, not all data created worldwide.');
}

// 3. Retain the requested method numbering.
{
  const s = slide('Compression across modalities');
  text(s, 'Lossless', 64, 151, 500, 48, 30, colors.ink, true);
  text(s, 'Lossy', 660, 151, 550, 48, 30, colors.ink, true);
  const left = [
    ['1. Huffman coding', 'Short codes for frequent symbols'],
    ['2. ZIP / DEFLATE', 'Repeated strings and entropy coding'],
    ['3. PNG', 'Predict pixels, then encode the differences'],
  ];
  const right = [
    ['4. MP3', 'Allocate precision using a model of hearing'],
    ['5. Uniform / μ-law quantization', 'Use fewer amplitude levels'],
    ['6. JPEG', 'Transform and quantize image detail'],
    ['7. Thresholding / dithering', 'Reduce pixel precision in different ways'],
  ];
  for (const [items, x] of [[left, 64], [right, 660]]) {
    items.forEach(([method, detail], i) => {
      text(s, method, x, 222 + i * 97, 552, 42, 27, colors.teal);
      text(s, detail, x, 267 + i * 97, 550, 39, 22, colors.muted);
    });
  }
  caption(s, 'Quantization discards precision. Entropy coding packs what remains. Thresholding and dithering are steps, not file formats.');
}

// 4. The illustration is generic, not a photo of the study apparatus.
{
  const s = slide('Neural signal capture: EEG');
  s.images.add({ blob: await fs.readFile(path.join(here, 'images/eeg-cap-white.jpg')), contentType: 'image/jpeg', fit: 'contain',
    alt: 'Generic EEG cap illustration, CIV / The Noun Project, CC0',
    position: { left: 75, top: 175, width: 360, height: 365 } });
  text(s, 'Electrodes on the scalp measure\nvoltage differences over time.', 565, 184, 650, 135, 34);
  text(s, 'One time series per channel', 565, 363, 650, 60, 32, colors.teal);
  text(s, 'Neural activity mixes with\nnoise and movement artifacts.', 565, 470, 640, 105, 28, colors.muted);
  caption(s, 'Different tasks use different features of these signals: frequency, spatial patterns, or brief responses.');
}

// 5. Keep illustrative storage arithmetic separate from the benchmark baseline.
{
  const s = slide('Why EEG needs compression');
  text(s, '64 channels × 256 samples/s × 16 bits', 64, 158, 1152, 70, 34);
  text(s, '2.83 GB per day', 64, 270, 1152, 130, 88, colors.teal);
  text(s, 'Storage', 70, 472, 330, 52, 32, colors.ink, true);
  text(s, 'Long recordings accumulate', 70, 537, 345, 70, 25, colors.muted);
  text(s, 'Wireless links', 468, 472, 330, 52, 32, colors.ink, true);
  text(s, 'Limited bandwidth', 468, 537, 340, 70, 25, colors.muted);
  text(s, 'Wearable devices', 865, 472, 350, 52, 32, colors.ink, true);
  text(s, 'Sending bits uses energy', 865, 537, 350, 70, 25, colors.muted);
  caption(s, 'Illustrative raw recording, decimal GB, metadata excluded. The experiment uses a separate 12-channel float32 baseline.');
}

// 6. Short, parallel descriptions retain the literature's technical distinction.
{
  const s = slide('Lossless and lossy EEG compression');
  text(s, 'Lossless', 64, 158, 525, 55, 34, colors.ink, true);
  text(s, 'Predict samples\nEncode the residuals\nRecover every value', 64, 246, 525, 170, 32);
  text(s, 'Memon et al. (1999)\nContext-based lossless / near-lossless coding', 64, 468, 525, 115, 25, colors.muted);
  text(s, 'Lossy', 660, 158, 552, 55, 34, colors.ink, true);
  text(s, 'Transform the signal\nReduce coefficient precision\nEncode what remains', 660, 246, 552, 170, 32);
  text(s, 'Higgins et al. (2013)\nWavelet quantization and thresholding\nDao et al. (2015): survey', 660, 468, 552, 135, 25, colors.muted);
  caption(s, 'Compression ratio measures storage. Waveform error measures signal distortion. Neither alone measures task performance.');
}

// 7. Connect established task-aware work to the narrower comparison here.
{
  const s = slide('Task-preserving EEG compression');
  text(s, 'A close waveform does not guarantee\nthe same task decisions.', 64, 150, 1150, 128, 40);
  const entries = [
    ['Zhang et al. (2022)', 'Personalized SSVEP compression and recognition'],
    ['Strypsteen & Bertrand (2023)', 'Jointly learned coding and inference'],
    ['Carzaniga et al. (2025)', 'BrainCodec: reconstruction and task evaluations'],
  ];
  entries.forEach(([author, finding], i) => {
    text(s, author, 64, 326 + i * 83, 570, 44, 27, colors.ink, true);
    text(s, finding, 660, 326 + i * 83, 552, 68, 25, colors.muted);
  });
  caption(s, 'Our study keeps each original-data reader fixed, then changes the compressor and storage allowance.');
}

// 8. Different task families, rather than variants of the same task.
{
  const s = slide('Our central question');
  text(s, 'At the same storage allowance,', 64, 162, 1150, 68, 38);
  text(s, 'which EEG tasks lose performance fastest?', 64, 244, 1150, 116, 48, colors.teal, true);
  const tasks = [
    ['SSVEP', 'Which flickering target?', 'A sustained rhythm', colors.SSVEP],
    ['Motor imagery', 'Left or right hand?', 'A spatial power pattern', colors.MI],
    ['P300', 'Target or non-target?', 'A brief event response', colors.ERP],
  ];
  tasks.forEach(([task, question, feature, color], i) => {
    const x = 64 + i * 398;
    text(s, task, x, 437, 365, 58, 34, color, true);
    text(s, question, x, 510, 365, 50, 25);
    text(s, feature, x, 571, 365, 54, 24, colors.muted);
  });
}

// 9. Procedure and measured baselines. Details move to the speaker notes.
{
  const s = slide('Experimental setup');
  text(s, '20 new participants    3 tasks    12 channels    128 samples/s', 64, 145, 1152, 65, 30);
  text(s, 'Earlier 60%: calibrate readers', 64, 247, 620, 55, 30);
  text(s, 'Later events: test after compression', 660, 247, 550, 90, 30, colors.teal);
  text(s, 'Uniform, μ-law or DCT, followed by packing and ZIP', 64, 347, 1152, 58, 30);
  const baseline = task => (100 * data.primary.baselines.find(b => b.task === task).mean).toFixed(1) + '%';
  nativeTable(s, [
    ['Task', 'Primary reader', 'Alternative reader', 'Original BA'],
    ['SSVEP', 'CCA', 'Spectral peaks', baseline('SSVEP')],
    ['Motor imagery', 'CSP + LDA', 'Band power + LDA', baseline('MI')],
    ['P300', 'Time bins + LDA', 'Logistic regression', baseline('ERP')],
  ], 64, 426, 1152, 180, [222, 300, 365, 265], 23);
  caption(s, 'Caps: 32, 64, 128, 256 B/s/channel, including reconstruction metadata. Raw float32: 512. BA = balanced accuracy.');
}

// 10. Native charts and table keep the numerical evidence editable.
{
  const s = slide('Storage allowance and recognition loss');
  const tasks = [['SSVEP', 'SSVEP'], ['MI', 'Motor imagery'], ['ERP', 'P300']];
  const budgets = [32, 64, 128, 256];
  const methods = [['uniform', 'Uniform + ZIP'], ['mulaw', 'μ-law + ZIP'], ['dct', 'DCT + ZIP']];
  text(s, 'Mean score loss across 20 participants, primary readers', 64, 124, 1150, 36, 23, colors.muted);
  methods.forEach(([method, label], i) => {
    const x = 64 + i * 395;
    text(s, label, x, 174, 360, 40, 27);
    s.charts.add('line', {
      position: { left: x, top: 220, width: 360, height: 220 },
      categories: budgets.map(String),
      series: tasks.map(([task, name]) => ({ name,
        values: budgets.map(b => chartNumber(100 * estimate('primary', task, method, b).mean)), smooth: false,
        line: { fill: colors[task], width: 3, style: 'solid' },
        marker: { symbol: 'circle', size: 5, fill: colors[task] },
      })), hasLegend: false, lineOptions: { smooth: false },
      xAxis: { textStyle: { typeface: font, fontSize: 17, fill: colors.muted },
        line: { fill: '#AAAAAA', width: 1 }, majorGridlines: null },
      yAxis: { min: -5, max: 20, majorUnit: 5,
        textStyle: { typeface: font, fontSize: 17, fill: colors.muted },
        majorGridlines: { fill: '#DDDDDD', width: 1 }, line: { fill: '#AAAAAA', width: 1 } },
      chartFill: '#FFFFFF', plotAreaFill: '#FFFFFF',
    });
  });
  text(s, 'SSVEP', 64, 450, 110, 32, 20, colors.SSVEP);
  text(s, 'Motor imagery', 178, 450, 175, 32, 20, colors.MI);
  text(s, 'P300', 360, 450, 100, 32, 20, colors.ERP);
  text(s, 'x: allowance (B/s/channel)    y: loss (percentage points)', 520, 450, 690, 32, 20, colors.muted);
  const tableValues = [['At 32 B/s/channel', 'Uniform', 'μ-law', 'DCT']];
  tasks.forEach(([task, label]) => tableValues.push([label, ...methods.map(([method]) =>
    ['primary', 'alternative'].map(f => (100 * estimate(f, task, method, 32).mean).toFixed(2)).join(' / '))]));
  nativeTable(s, tableValues, 64, 480, 1152, 140, [330, 274, 274, 274], 20);
  caption(s, 'Table: primary / alternative reader loss (pp). Lower is better. Lines join tested settings. Intervals are in the linked results.');
}

// 11. A paired comparison preserves uncertainty without a universal ranking.
{
  const s = slide('Summary and findings');
  text(s, 'The reader changes\nthe task ordering.', 64, 164, 545, 140, 40, colors.ink, true);
  text(s, 'Primary SSVEP versus motor imagery:\nno clear separation at the tightest cap.', 64, 349, 550, 100, 27, colors.muted);
  text(s, 'P300: DCT loses fewer points than uniform\nfor both readers and all 20 people.', 64, 512, 1120, 95, 32, colors.teal);
  text(s, 'P300 advantage of DCT over uniform', 665, 159, 550, 75, 26);
  const advantages = ['primary', 'alternative'].map(family => data[family].method_differences.find(
    g => g.task === 'ERP' && g.budget === 32 && g.first === 'uniform' && g.second === 'dct'));
  s.charts.add('scatter', {
    position: { left: 765, top: 250, width: 437, height: 212 },
    categories: [],
    series: [
      ...advantages.map((v, i) => ({ name: ['Primary interval', 'Alternative interval'][i],
        xValues: v.ci95.map(x => chartNumber(x * 100)), values: [1 - i, 1 - i],
        line: { fill: colors.teal, width: 2 }, marker: { symbol: 'none' } })),
      { name: 'Paired mean', xValues: advantages.map(v => chartNumber(v.mean * 100)), values: [1, 0],
        line: { fill: 'none', width: 0 }, marker: { symbol: 'circle', size: 8, fill: colors.teal } },
    ], scatterOptions: { style: 'lineWithMarkers' }, hasLegend: false,
    xAxis: { min: 0, max: 12.5, majorUnit: 5,
      textStyle: { typeface: font, fontSize: 20, fill: colors.muted },
      majorGridlines: { fill: '#DDDDDD', width: 1 }, line: { fill: '#AAAAAA', width: 1 } },
    yAxis: { min: -0.5, max: 1.5, visible: false, majorGridlines: null },
    chartFill: '#FFFFFF', plotAreaFill: '#FFFFFF',
  });
  text(s, 'Primary', 650, 287, 118, 40, 23);
  text(s, 'Alternative', 650, 367, 118, 40, 23);
  text(s, '8.87 pp / 10.05 pp, paired 95% intervals', 665, 468, 550, 38, 22, colors.muted);
  caption(s, '32 B/s/channel. Both P300 readers share low-frequency features. These findings describe the tested pipelines.');
}

// 12. Local conclusions and the next checks, without second-day experiments.
{
  const s = slide('Limitations and future work');
  text(s, 'Limits of this study', 64, 161, 530, 56, 32, colors.ink, true);
  text(s, '20 people, one acquisition study\nOne recording day, offline filtering\nTwo readers per task\nShared P300 features', 64, 260, 540, 270, 29);
  text(s, 'What comes next', 660, 161, 552, 56, 32, colors.ink, true);
  text(s, 'More datasets and task families\nDifferent features and EEG codecs\nCloser matching of achieved rates\nStreaming latency and device energy', 660, 260, 552, 270, 29);
  text(s, 'Preserve the information needed for the intended use.', 64, 571, 1150, 60, 34, colors.teal);
  caption(s, 'Equal maximum byte caps do not guarantee equal achieved file sizes. No universal task ranking or clinical safety claim.');
}

// 13. Short linked references, with full metadata retained in ref.bib and notes.
{
  const s = slide('References');
  const refs = [
    ['ITU (2026)', 'Facts and Figures, p. 16', 'https://www.itu.int/itu-d/reports/statistics/wp-content/uploads/sites/5/2026/11/ITUFactsAndFigures2026.pdf'],
    ['Deutsch (1996)', 'DEFLATE format specification, RFC 1951', 'https://www.rfc-editor.org/rfc/rfc1951'],
    ['Memon, Kong & Cinkler (1999)', 'Context-based EEG compression', 'https://doi.org/10.1109/4233.788586'],
    ['Higgins et al. (2013)', 'Wavelet coefficient quantization', 'https://doi.org/10.1016/j.compbiomed.2013.02.011'],
    ['Dao, Li & Do (2015)', 'Lossy Compression Techniques for EEG Signals', 'https://doi.org/10.1109/ATC.2015.7388309'],
    ['Zhang et al. (2022)', 'Personalized SSVEP compression', 'https://doi.org/10.3390/info13040186'],
    ['Strypsteen & Bertrand (2023)', 'Neural source coding for wireless BCI', 'https://homes.esat.kuleuven.be/~abertran/reports/Strypsteen_ICASSP2023.pdf'],
    ['Carzaniga et al. (2025)', 'The Case for Cleaner Biosignals (BrainCodec)', 'https://proceedings.iclr.cc/paper_files/paper/2025/file/28c9ce39a89c03f0bdd9725907d5abbc-Paper-Conference.pdf'],
    ['Lee et al. (2019)', 'OpenBMI dataset, GigaScience 8, giz002', 'https://doi.org/10.1093/gigascience/giz002'],
    ['OpenAI (2026)', 'ChatGPT 6. AI assistance', 'https://chatgpt.com/'],
  ];
  refs.forEach(([author, title, url], i) => {
    const x = i < 5 ? 64 : 660;
    const y = 143 + (i % 5) * 85;
    text(s, author, x, y, 552, 35, 23, colors.ink, true);
    link(s, title, url, x, y + 38, 552, 21);
  });
  link(s, 'Project website, demonstrations and full results',
    'https://da3021-compression-lab-deb044.solidflask.chatgpt.site/', 64, 609, 1135, 26);
  link(s, 'github.com/Deb044/DataCompression', 'https://github.com/Deb044/DataCompression', 64, 663, 1100, 18);
}

await fs.mkdir(out, { recursive: true });
await (await PresentationFile.exportPptx(deck)).save(path.join(out, 'candidate.pptx'));
// The companion PDF uses high-resolution slide renders. All text, evidence and
// notes remain editable in the PowerPoint. Recreate external links in the PDF.
const pdf = await PDFDocument.create();
pdf.setTitle('EEG Compression');
pdf.setAuthor('Debarghya Das (240150049)');
for (const [index, s] of deck.slides.items.entries()) {
  const image = await deck.export({ slide: s, format: 'png', scale: 2 });
  const bytes = new Uint8Array(await image.arrayBuffer());
  await fs.writeFile(path.join(out, `slide-${String(index + 1).padStart(2, '0')}.png`), bytes);
  const page = pdf.addPage([960, 540]);
  page.drawImage(await pdf.embedPng(bytes), { x: 0, y: 0, width: 960, height: 540 });
  const annotations = hyperlinks.filter(link => link.slide === index).map(link =>
    pdf.context.register(pdf.context.obj({ Type: 'Annot', Subtype: 'Link',
      Rect: [link.x * 0.75, (720 - link.y - link.h) * 0.75,
        (link.x + link.w) * 0.75, (720 - link.y) * 0.75], Border: [0, 0, 0],
      A: { Type: 'Action', S: 'URI', URI: PDFString.of(link.url) } })));
  if (annotations.length) page.node.set(PDFName.of('Annots'), pdf.context.obj(annotations));
}
await fs.writeFile(path.join(out, 'candidate.pdf'), await pdf.save());
await fs.writeFile(path.join(out, 'deck.json'), JSON.stringify(deck.toProto()));
console.log(`Built ${deck.slides.items.length} editable slides in ${out}`);
