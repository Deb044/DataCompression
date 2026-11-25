/** Build the presentation from verified study data. No experiments run here.
 * Set RUNTIME_NODE_MODULES to the bundled Node packages, then run:
 * node presentation/build.mjs [private-output-directory]
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const out = path.resolve(process.argv[2] ?? path.join(root, 'tmp/presentation-uniform'));
const packages = process.env.RUNTIME_NODE_MODULES ?? process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
if (!packages) throw new Error('Set RUNTIME_NODE_MODULES to the bundled Node packages.');
const runtimeRequire = createRequire(path.join(packages, '__presentation__.cjs'));
const { Presentation, PresentationFile } = await import(pathToFileURL(runtimeRequire.resolve('@oai/artifact-tool')).href);
const { PDFDocument, PDFName, PDFString } = runtimeRequire('pdf-lib');
const readJSON = async file => JSON.parse(await fs.readFile(path.join(here, file), 'utf8'));
const data = await readJSON('data/study.json');
const zipExample = await readJSON('data/zip-example.json');
const notes = await readJSON('speaker-notes.json');

// One hierarchy and two consistent columns. Colored strokes belong to plots,
// while all body text and chart labels remain neutral.
const style = {
  font: 'Arial', heading: 42, subheading: 29, body: 25, small: 20, caption: 16,
  turquoise: '#337F79', ink: '#252525', grey: '#5D5D5D',
  x: 64, leftWidth: 452, visualX: 570, visualWidth: 646,
};
const taskColors = { SSVEP: '#267C72', MI: '#C2603B', ERP: '#4968B1' };
const tasks = [['SSVEP', 'SSVEP'], ['MI', 'Motor imagery'], ['ERP', 'P300']];
const methods = [['uniform', 'Uniform + ZIP'], ['mulaw', 'μ-law + ZIP'], ['dct', 'DCT + ZIP']];
const budgets = [32, 64, 128, 256];
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const hyperlinks = [];

function text(s, value, x, y, w, h, size = style.body, bold = false) {
  const box = s.shapes.add({ geometry: 'textbox',
    position: { left: x, top: y, width: w, height: h },
    fill: 'none', line: { fill: 'none', width: 0 } });
  box.text = value;
  box.text.style = { typeface: style.font, fontSize: size, color: style.ink,
    bold, insets: 0, verticalAlignment: 'top', autoFit: 'none', wrap: 'word' };
  return box;
}
function heading(s, label, y = 145, x = style.x, w = style.leftWidth) {
  const box = text(s, label, x, y, w, 70, style.subheading, true);
  box.text.color = style.turquoise;
  return box;
}
function body(s, value, y, h = 100) { return text(s, value, style.x, y, style.leftWidth, h); }
function bullets(s, items, y, h = 310, size = style.body) {
  const box = text(s, '', style.x, y, style.leftWidth, h, size);
  box.text = items.map(item => ({
    bulletCharacter: '•', marginLeft: 18 * 12700, indent: -9 * 12700,
    spaceAfter: 13 * 100, runs: [item],
  }));
  return box;
}
function caption(s, value) {
  const box = text(s, value, 64, 649, 1110, 42, style.caption);
  box.text.color = style.grey;
}
function slide(title) {
  const s = deck.slides.add();
  s.background.fill = '#FFFFFF';
  if (title) {
    const box = text(s, title, 64, 40, 1152, 70, style.heading, true);
    box.text.color = style.turquoise;
  }
  const number = text(s, String(deck.slides.items.length), 1190, 680, 36, 24, 16);
  number.text.color = '#888888';
  s.speakerNotes.text = notes[deck.slides.items.length - 1];
  return s;
}
function link(s, label, url, x, y, w, size = style.small, h = 36) {
  const box = text(s, label, x, y, w, h, size);
  box.hyperlink = { uri: url, isExternal: true };
  hyperlinks.push({ slide: deck.slides.items.indexOf(s), url, x, y, w, h });
  return box;
}
async function image(s, file, position, alt) {
  s.images.add({ blob: await fs.readFile(path.join(here, file)), contentType: 'image/jpeg',
    fit: 'contain', alt, position });
}
function estimate(family, task, method, budget) {
  const value = data[family].groups.find(g => g.task === task && g.method === method && g.budget === budget);
  if (!value) throw new Error(`Missing measured result: ${family}/${task}/${method}/${budget}`);
  return value;
}
// Preserve full precision in study.json. Six decimals in pp fit Excel's precision.
const chartNumber = value => Number(value.toFixed(6));
const axisText = size => ({ typeface: style.font, fontSize: size, fill: style.grey });
function table(s, values, y, widths, size = 22, height = 220) {
  const t = s.tables.add({ rows: values.length, columns: values[0].length,
    left: style.visualX, top: y, width: style.visualWidth, height,
    columnWidths: widths, values });
  t.borders.assign({ fill: '#D7DEDD', width: 0.5, style: 'solid' });
  t.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({
    fill: '#FFFFFF', textStyle: { typeface: style.font, fontSize: size, color: style.ink },
    margins: { left: 10, right: 10, top: 8, bottom: 8 } });
  t.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: values[0].length }).assign({
    fill: '#F4F6F6', textStyle: { typeface: style.font, fontSize: size, color: style.turquoise, bold: true } });
  return t;
}
function plot(s, type, config) {
  return s.charts.add(type, { hasLegend: false, chartFill: '#FFFFFF', plotAreaFill: '#FFFFFF', ...config });
}

// 1. Title and personal details stay on the left, with the illustration on the right.
{
  const s = slide();
  const title = text(s, 'Every Bit\nof the Brain', 64, 145, 550, 200, 64, true);
  title.text.color = style.turquoise;
  text(s, 'How much EEG data\ncan we afford to lose?', 64, 371, 530, 115, 32);
  text(s, 'Debarghya Das\n240150049', 64, 521, 500, 75, 25);
  text(s, 'DSAI, IIT Guwahati\n25 November 2026', 64, 611, 500, 60, 20);
  await image(s, 'images/eeg-cap-white.jpg', {left: 710, top: 140, width: 390, height: 440},
    'Generic EEG cap illustration by CIV / The Noun Project, CC0');
}

// 2. Selected published estimates and a clearly distinguished forecast.
{
  const s = slide('A world generating more data');
  heading(s, 'Data across modalities');
  bullets(s, [
    'Video, speech, images and sensors generate growing streams of data.',
    'LLMs and robotics depend on large collections of these recordings.',
    '1 zettabyte equals a trillion gigabytes.',
  ], 216, 270);
  heading(s, 'The value of data', 490);
  body(s, '“abundant, but worth little\nunless you refine it”', 544, 76);
  text(s, 'Ginni Rometty, former IBM CEO', 64, 615, 452, 32, 19);
  heading(s, 'Annual global datasphere (ZB)', 147, style.visualX, style.visualWidth);
  plot(s, 'bar', {
    position: {left: 585, top: 225, width: 615, height: 335},
    categories: ['2018\nestimate', '2020\nestimate', '2028\nforecast'],
    series: [{ name: 'Annual data created / replicated', values: [33,64.2,393.9],
      fill: '#7C9290', points: [{idx:2,fill:'#B9DBD7',line:{style:'solid',fill:style.turquoise,width:2}}] }],
    barOptions: {direction:'column',gapWidth:110},
    dataLabels: {showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:axisText(23)},
    xAxis: {textStyle:axisText(21),majorGridlines:null,line:{fill:'#AAAAAA',width:1}},
    yAxis: {min:0,max:450,majorUnit:100,textStyle:axisText(18),majorGridlines:{fill:'#E3E3E3',width:1}},
  });
  text(s, 'Selected IDC report editions. 2028 is a forecast,\nnot an observed total or stored capacity.', 590, 586, 610, 59, 19);
  caption(s, 'Sources: IDC / Seagate (2018, 2024), UNCTAD (2021). Quote: Ginni Rometty, as quoted by IBM Digital Analytics.');
}

// 3. A measured toy ZIP example supports the general motivation, not an EEG result.
{
  const s = slide('Compression: fewer bits to store and send');
  heading(s, 'Why it is necessary');
  bullets(s, [
    'Large recordings take storage space and time to transmit.',
    'Compression exploits structure to represent data with fewer bits.',
    'Lossless methods recover every value. Lossy methods trade precision for space.',
    'For EEG, the useful information must survive that trade-off.',
  ], 216, 390);
  heading(s, 'A simple lossless ZIP example', 147, style.visualX, style.visualWidth);
  plot(s, 'bar', {
    position:{left:585,top:234,width:615,height:295},
    categories:['Original text','ZIP archive'],
    series:[{name:'Bytes',values:[zipExample.raw_bytes,zipExample.zip_bytes],fill:'#8A9B9A',
      points:[{idx:1,fill:'#73B6AF'}]}], barOptions:{direction:'column',gapWidth:140},
    dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'#,##0',textStyle:axisText(23)},
    xAxis:{textStyle:axisText(22),majorGridlines:null},
    yAxis:{min:0,max:75000,majorUnit:25000,textStyle:axisText(18),title:{text:'Bytes',textStyle:axisText(19)},majorGridlines:{fill:'#E3E3E3',width:1}},
  });
  text(s, `Repeated text: ${zipExample.raw_bytes.toLocaleString('en-US')} bytes\nZIP archive: ${zipExample.zip_bytes.toLocaleString('en-US')} bytes\nExact recovery verified`, 595, 551, 595, 89, 23);
  caption(s, 'Illustrative demo: one repeated sentence, DEFLATE level 6, archive overhead included. This is not an EEG benchmark result.');
}

// 4. Seven numbered methods, plus a clearly labelled quantization demonstration.
{
  const s = slide('Compression across modalities');
  const families = [
    ['1. Huffman coding','Shorter codes for frequent symbols'],
    ['2. ZIP / DEFLATE','Repeated strings and entropy coding'],
    ['3. PNG','Pixel prediction and lossless coding'],
    ['4. MP3','Precision guided by human hearing'],
    ['5. Uniform / μ-law quantization','Fewer amplitude levels'],
    ['6. JPEG','Transform and quantize image detail'],
    ['7. Thresholding / dithering','Reduce pixel precision differently'],
  ];
  families.forEach(([name,detail],i)=>{
    const y=136+i*71;
    const h=text(s,name,64,y,480,36,24,true);h.text.color=style.turquoise;
    text(s,detail,64,y+36,480,31,20);
  });
  heading(s, 'What quantization changes',147,style.visualX,style.visualWidth);
  const values=Array.from({length:65},(_,i)=>0.7*Math.sin(2*Math.PI*i/64));
  plot(s,'line',{
    position:{left:580,top:241,width:625,height:285},
    categories:values.map((_,i)=>String(i)),
    series:[
      {name:'Original',values:values.map(chartNumber),line:{fill:'#777777',width:2},smooth:false,marker:{symbol:'none'}},
      {name:'2-bit uniform',values:values.map(v=>chartNumber(Math.round((v+1)*1.5)/1.5-1)),line:{fill:style.turquoise,width:3},smooth:false,marker:{symbol:'none'}},
    ],lineOptions:{smooth:false},
    xAxis:{visible:false,majorGridlines:null},
    yAxis:{min:-1,max:1,majorUnit:0.5,textStyle:axisText(18),majorGridlines:{fill:'#E3E3E3',width:1}},
  });
  text(s,'Grey: original sine wave\nTurquoise: four possible amplitude levels',590,553,600,85,23);
  caption(s,'Illustrative signal, not EEG data. Quantization discards precision. Entropy coding packs what remains.');
}

// 5. The trace is an illustration from the supplied reference, not study evidence.
{
  const s = slide('Neural signal capture: EEG');
  heading(s,'Recording electrical activity');
  bullets(s,[
    'Scalp electrodes measure voltage differences over time.',
    'Each channel produces a time series.',
    'The recording combines neural activity, noise and artifacts.',
    'Different tasks rely on frequency, spatial patterns or brief responses.',
  ],216,370);
  heading(s,'Many channels, recorded together',147,style.visualX,style.visualWidth);
  await image(s,'images/eeg-traces-reference.jpg',{left:690,top:221,width:387,height:396},
    'Illustrative multichannel traces from page 172 of the supplied neural signal capture reference');
  caption(s,'Trace illustration: supplied neural signal capture reference, p. 172. This is not a recording from our experiment.');
}

// 6. Reproducible arithmetic, explicitly distinct from the benchmark representation.
{
  const s = slide('Why EEG especially needs compression');
  heading(s,'Continuous recording');
  bullets(s,[
    'Many channels and long recordings make storage accumulate.',
    'Wireless links have limited bandwidth.',
    'Wearable devices also have limited energy.',
  ],222,255);
  heading(s,'An illustrative recording',505);
  body(s,'64 channels × 256 samples/s\n× 16 bits per sample',562,77);
  heading(s,'Raw data accumulated over time',147,style.visualX,style.visualWidth);
  plot(s,'bar',{
    position:{left:585,top:241,width:615,height:300},
    categories:['1 hour','6 hours','12 hours','24 hours'],
    series:[{name:'Raw GB',values:[1,6,12,24].map(h=>chartNumber(64*256*16*3600*h/8/1e9)),fill:'#73AAA5'}],
    barOptions:{direction:'column',gapWidth:90},
    xAxis:{textStyle:axisText(20),majorGridlines:null},
    yAxis:{min:0,max:3,majorUnit:1,title:{text:'GB',textStyle:axisText(19)},textStyle:axisText(18),majorGridlines:{fill:'#E3E3E3',width:1}},
  });
  text(s,'2.83 GB per day before compression',590,574,610,66,29,true);
  caption(s,'Illustrative raw 16-bit recording, decimal GB, metadata excluded. Our experiment uses 12 channels and float32 samples.');
}

// 7. Literature on reversible coding and waveform distortion.
{
  const s = slide('Existing research: lossless and lossy EEG');
  heading(s,'Reducing storage and distortion');
  bullets(s,[
    'Lossless predictors encode the difference between a sample and its prediction.',
    'Lossy methods transform the signal, then reduce coefficient precision.',
    'Compression ratio measures storage. PRD or NRMSE measure waveform error.',
    'Published ratios depend on the recording and how distortion is defined.',
  ],218,385);
  heading(s,'Representative work',147,style.visualX,style.visualWidth);
  table(s,[
    ['Study','Approach'],
    ['Memon et al. (1999)','Context-based lossless and near-lossless coding'],
    ['Higgins et al. (2013)','Wavelet coefficient quantization and thresholding'],
    ['Dao et al. (2015)','Survey of lossy methods and storage–distortion trade-offs'],
  ],249,[240,406],23,310);
  caption(s,'These papers use different data and measurement conventions. Their compression ratios are not a common leaderboard.');
}

// 8. Established task-aware work leads to our narrower controlled comparison.
{
  const s = slide('Existing research: preserving the task');
  heading(s,'Preserving useful information');
  bullets(s,[
    'A close-looking waveform may still lead to different decisions.',
    'Existing work evaluates recognition or jointly optimizes coding and inference.',
    'We keep each reader fixed after calibration, then vary the compressor and budget.',
  ],218,340);
  body(s,'Our question is about the tested\ntask-and-reader combinations.',565,74);
  heading(s,'Task performance enters the evaluation',147,style.visualX,style.visualWidth);
  table(s,[
    ['Study','Task-related evaluation'],
    ['Zhang et al. (2022)','Personalized SSVEP compression and recognition'],
    ['Strypsteen & Bertrand (2023)','Jointly learned source coding and inference'],
    ['Carzaniga et al. (2025)','BrainCodec: reconstruction and downstream evaluations'],
  ],249,[253,393],23,310);
  caption(s,'Task preservation is established research. Our project compares simple compressors under a fixed-reader protocol.');
}

// 9. The three tasks rely on meaningfully different features.
{
  const s = slide('Our central question');
  heading(s,'Equal storage allowance');
  body(s,'Which EEG tasks lose useful\nperformance fastest?',222,115);
  bullets(s,[
    'Compare three task families.',
    'Give several compressors the same maximum byte allowance.',
    'Check whether the ordering changes with the reader.',
  ],376,260);
  heading(s,'Different tasks use different features',147,style.visualX,style.visualWidth);
  table(s,[
    ['Task','Decision','Main feature'],
    ['SSVEP','Which flickering target?','A sustained rhythm'],
    ['Motor imagery','Left or right hand?','Spatial power patterns'],
    ['P300','Target or non-target?','A brief event response'],
  ],253,[175,236,235],23,300);
  caption(s,'The eventual conclusion must stay local to the recordings, methods, budgets and readers tested.');
}

// 10. The protocol and baseline table introduce the controlled benchmark.
{
  const s = slide('Experimental setup');
  heading(s,'A paired comparison');
  bullets(s,[
    '20 new participants, 3 tasks, 12 channels and 128 samples/s.',
    'Earlier 60% of events calibrate the readers. Later events test them.',
    'Readers stay frozen. Compression settings do not use task labels.',
    'Uniform, μ-law or DCT, then packing and ZIP.',
  ],216,385);
  heading(s,'Readers and original balanced accuracy',147,style.visualX,style.visualWidth);
  const baseline=task=>(100*data.primary.baselines.find(g=>g.task===task).mean).toFixed(1)+'%';
  table(s,[
    ['Task','Primary / alternative reader','Original BA'],
    ['SSVEP','CCA / spectral peaks',baseline('SSVEP')],
    ['Motor imagery','CSP + LDA / band power + LDA',baseline('MI')],
    ['P300','Time bins + LDA / logistic regression',baseline('ERP')],
  ],248,[152,357,137],22,280);
  text(s,'Caps: 32, 64, 128, 256 B/s/channel\nRaw selected float32: 512 B/s/channel',584,563,625,73,24);
  caption(s,'OpenBMI, first recording day only. Caps include reconstruction metadata. BA = balanced accuracy. A 2-second guard surrounds the split.');
}

// 11. Three plots share the right column, with the same scales and color mapping.
{
  const s=slide('Storage allowance and recognition loss');
  heading(s,'How to read the plots');
  bullets(s,[
    'The score loss is original balanced accuracy minus compressed-data accuracy.',
    'Lower loss is better. A small negative value means a slightly higher score.',
    'Losses shrink as the byte allowance increases.',
    'The DCT curve is especially low for this P300 reader.',
  ],216,355);
  text(s,'SSVEP     Motor imagery     P300\nTurquoise      Orange              Blue',64,579,465,63,19);
  methods.forEach(([method,label],i)=>{
    const y=134+i*164;
    heading(s,label,y,style.visualX,style.visualWidth);
    plot(s,'line',{
      position:{left:585,top:y+45,width:615,height:116},
      categories:budgets.map(String),
      series:tasks.map(([task,name])=>({name,values:budgets.map(b=>chartNumber(100*estimate('primary',task,method,b).mean)),
        smooth:false,line:{fill:taskColors[task],width:2.5},marker:{symbol:'circle',size:4,fill:taskColors[task]}})),
      lineOptions:{smooth:false},
      xAxis:{textStyle:axisText(17),majorGridlines:null,line:{fill:'#AAAAAA',width:1}},
      yAxis:{min:-5,max:15,majorUnit:5,textStyle:axisText(16),majorGridlines:{fill:'#E3E3E3',width:1}},
    });
  });
  caption(s,'Primary readers, mean of 20 participants. x: B/s/channel. y: percentage-point loss. Lines join tested settings. Intervals are on the site.');
}

// 12. Preserve every table value without squeezing the curves.
{
  const s=slide('The tightest budget: does the reader matter?');
  heading(s,'32 bytes per second per channel');
  bullets(s,[
    'Each cell shows loss for the primary / alternative reader.',
    'Primary readers put SSVEP highest in mean loss for all three compressors.',
    'Alternative readers put P300 highest for uniform and μ-law.',
    'Changing the reader can change the task ordering.',
  ],216,385);
  heading(s,'Balanced accuracy loss (percentage points)',147,style.visualX,style.visualWidth);
  const values=[['Task','Uniform','μ-law','DCT']];
  for(const [task,label] of tasks) values.push([label,...methods.map(([method])=>
    ['primary','alternative'].map(f=>(100*estimate(f,task,method,32).mean).toFixed(2)).join(' / '))]);
  table(s,values,253,[182,155,155,154],22,260);
  text(s,'Primary / alternative reader\nLower values mean less performance lost.',585,557,615,77,24);
  caption(s,'Every loss uses that reader’s own original-data baseline. These are sensitivities of the tested pipelines, not a universal ranking.');
}

// 13. Paired intervals preserve the strongest repeated finding and its limits.
{
  const s=slide('Summary and findings');
  heading(s,'No single task ranking');
  bullets(s,[
    'The reader changes which task appears most affected.',
    'Primary SSVEP versus motor imagery has no clear separation at the tightest cap.',
    'P300 loses fewer points with DCT than uniform for both readers and all 20 people.',
  ],216,345);
  body(s,'This is evidence about these pipelines,\nnot an intrinsic ranking of EEG tasks.',570,69);
  heading(s,'P300: DCT advantage over uniform',147,style.visualX,style.visualWidth);
  const advantages=['primary','alternative'].map(f=>data[f].method_differences.find(
    g=>g.task==='ERP'&&g.budget===32&&g.first==='uniform'&&g.second==='dct'));
  plot(s,'scatter',{
    position:{left:750,top:259,width:450,height:261},categories:[],
    series:[...advantages.map((v,i)=>({name:['Primary interval','Alternative interval'][i],
      xValues:v.ci95.map(x=>chartNumber(x*100)),values:[1-i,1-i],line:{fill:style.turquoise,width:2},marker:{symbol:'none'}})),
      {name:'Paired mean',xValues:advantages.map(v=>chartNumber(v.mean*100)),values:[1,0],line:{fill:'none',width:0},marker:{symbol:'circle',size:8,fill:style.turquoise}}],
    scatterOptions:{style:'lineWithMarkers'},
    xAxis:{min:0,max:12.5,majorUnit:5,textStyle:axisText(20),majorGridlines:{fill:'#DDDDDD',width:1},line:{fill:'#AAAAAA',width:1}},
    yAxis:{visible:false,min:-0.5,max:1.5,majorGridlines:null},
  });
  text(s,'Primary',584,321,150,40,25);
  text(s,'Alternative',584,416,160,40,25);
  text(s,'8.87 pp / 10.05 pp\nPaired means and 95% intervals',584,557,630,80,25);
  caption(s,'32 B/s/channel. Both P300 readers use the same low-frequency features. Participant-bootstrap intervals describe these data only.');
}

// 14. Body text remains neutral on both sides. The right table is a visual map
// from each limitation to its corresponding next experiment.
{
  const s=slide('Limitations and future work');
  heading(s,'Limits of this study');
  bullets(s,[
    '20 people from one acquisition study do not represent every EEG setting.',
    'Two readers per task leave many feature choices unexplored.',
    'Equal maximum caps do not give exactly equal achieved file sizes.',
    'We did not measure device energy, latency or clinical usefulness.',
  ],216,385);
  heading(s,'The next checks',147,style.visualX,style.visualWidth);
  table(s,[
    ['Current limit','Next step'],
    ['One dataset','More datasets and task families'],
    ['Few readers and features','Independent feature extractors and stronger EEG codecs'],
    ['Equal maximum caps','Match achieved storage rates more closely'],
    ['Offline evaluation','Measure streaming latency and device energy'],
  ],238,[230,416],22,365);
  caption(s,'The goal is to preserve information needed for the intended use. Offline filtering and shared P300 features remain important limitations.');
}

// 15. Compact references stay on the left. Project links and an evidence summary
// form the right-hand visual rather than a second column of bibliography text.
{
  const s=slide('References');
  const refs=[
    ['IDC / Seagate (2018): Global DataSphere','https://www.seagate.com/files/www-content/our-story/trends/files/idc-seagate-dataage-whitepaper.pdf'],
    ['UNCTAD (2021): Digital Economy Report','https://unctad.org/system/files/official-document/der2021_en.pdf'],
    ['IDC / Seagate (2024): 2024–2028 forecast','https://www.seagate.com/content/dam/seagate/assets/promos/ai-storage-in-computex-2024/file/computex-forum-deck_Final.pdf'],
    ['IBM: Ginni Rometty quotation','https://www.ibm.com/support/pages/fueling-your-insights-natural-resource-our-generation-big-data'],
    ['Deutsch (1996): DEFLATE, RFC 1951','https://www.rfc-editor.org/rfc/rfc1951'],
    ['Memon et al. (1999): Context-based coding','https://doi.org/10.1109/4233.788586'],
    ['Higgins et al. (2013): Wavelet quantization','https://doi.org/10.1016/j.compbiomed.2013.02.011'],
    ['Dao et al. (2015): Lossy EEG compression','https://doi.org/10.1109/ATC.2015.7388309'],
    ['Zhang et al. (2022): Personalized SSVEP','https://doi.org/10.3390/info13040186'],
    ['Strypsteen & Bertrand (2023): Neural coding','https://homes.esat.kuleuven.be/~abertran/reports/Strypsteen_ICASSP2023.pdf'],
    ['Carzaniga et al. (2025): BrainCodec','https://proceedings.iclr.cc/paper_files/paper/2025/file/28c9ce39a89c03f0bdd9725907d5abbc-Paper-Conference.pdf'],
    ['Lee et al. (2019): OpenBMI dataset','https://doi.org/10.1093/gigascience/giz002'],
    ['OpenAI (2026): ChatGPT 6, AI assistance','https://chatgpt.com/'],
  ];
  refs.forEach(([label,url],i)=>link(s,label,url,64,139+i*38,478,19,34));
  heading(s,'Explore the project',147,style.visualX,style.visualWidth);
  table(s,[
    ['On the website','In the repository'],
    ['Interactive explanations','Compression and decoding code'],
    ['Plots and individual results','Measured exports and protocol'],
    ['Study limitations','Reproducible presentation sources'],
  ],249,[323,323],23,285);
  link(s,'Open the project website','https://da3021-compression-lab-deb044.solidflask.chatgpt.site/',584,568,600,25,42);
  link(s,'github.com/Deb044/DataCompression','https://github.com/Deb044/DataCompression',584,621,600,21,40);
}

if(deck.slides.items.length!==notes.length) throw new Error('Slide and presenter-note counts differ.');
await fs.mkdir(out,{recursive:true});
await (await PresentationFile.exportPptx(deck)).save(path.join(out,'candidate.pptx'));
// High-resolution PDF companion. The PPTX retains native editable evidence.
const pdf=await PDFDocument.create();
pdf.setTitle('Every Bit of the Brain');
pdf.setSubject('How much EEG data can we afford to lose?');
pdf.setAuthor('Debarghya Das (240150049)');
for(const [index,s] of deck.slides.items.entries()){
  const render=await deck.export({slide:s,format:'png',scale:2});
  const bytes=new Uint8Array(await render.arrayBuffer());
  await fs.writeFile(path.join(out,`slide-${String(index+1).padStart(2,'0')}.png`),bytes);
  const page=pdf.addPage([960,540]);
  page.drawImage(await pdf.embedPng(bytes),{x:0,y:0,width:960,height:540});
  const annotations=hyperlinks.filter(l=>l.slide===index).map(l=>pdf.context.register(pdf.context.obj({
    Type:'Annot',Subtype:'Link',Rect:[l.x*.75,(720-l.y-l.h)*.75,(l.x+l.w)*.75,(720-l.y)*.75],Border:[0,0,0],
    A:{Type:'Action',S:'URI',URI:PDFString.of(l.url)},
  })));
  if(annotations.length) page.node.set(PDFName.of('Annots'),pdf.context.obj(annotations));
}
await fs.writeFile(path.join(out,'candidate.pdf'),await pdf.save());
await fs.writeFile(path.join(out,'deck.json'),JSON.stringify(deck.toProto()));
console.log(`Built ${deck.slides.items.length} slides in ${out}`);
