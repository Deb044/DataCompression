// Render only recorded experiment exports. No research metrics are invented here.
import { makeTable } from './table.js';

const byId = id => document.getElementById(id);
const percent = value => value === null ? 'Undefined' : `${(100 * value).toFixed(2)}%`;
const fixed = (value, digits = 3) => value === null ? 'Undefined' : value.toFixed(digits);
const methodName = method => method === 'mulaw' ? 'μ-law' : method === 'float32' ? 'Float32 + ZIP' : 'Uniform';

function figure(path, alt) {
  const link = document.createElement('a');
  link.className = 'figure-download';
  link.href = path;
  const image = document.createElement('img');
  image.src = path; image.alt = alt; image.loading = 'lazy';
  link.append(image);
  return link;
}

function metrics(values) {
  const element = document.createElement('div');
  element.className = 'metric-grid';
  for (const [value, label] of values) {
    const box = document.createElement('div'); box.className = 'metric';
    const number = document.createElement('strong'); number.textContent = value;
    const caption = document.createElement('span'); caption.textContent = label;
    box.append(number, caption); element.append(box);
  }
  return element;
}

function svg(tag, attributes, text) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  if (text !== undefined) element.textContent = text;
  return element;
}

function drawWaveform(target, original, reconstruction, sampleRate) {
  const width = 1000, height = 290, left = 62, right = 18, top = 24, bottom = 44;
  const limit = Math.max(...original.map(Math.abs), ...reconstruction.map(Math.abs), 1e-9) * 1.08;
  const yPosition = value => top + (1 - value / limit) / 2 * (height - top - bottom);
  target.replaceChildren();
  for (const value of [-limit, 0, limit]) {
    const y = yPosition(value);
    target.append(svg('line', {x1:left, x2:width-right, y1:y, y2:y, class:'grid'}));
    target.append(svg('text', {x:left-10, y:y+4, 'text-anchor':'end'}, value.toFixed(1)));
  }
  for (let second = 0; second <= 4; second++) {
    const x = left + second / 4 * (width - left - right);
    target.append(svg('text', {x, y:height-23, 'text-anchor':'middle'}, second));
  }
  for (const [values, name] of [[original,'original'],[reconstruction,'reconstructed']]) {
    const path = values.map((value, i) => `${i ? 'L' : 'M'}${(left + i / sampleRate / 4 * (width-left-right)).toFixed(2)},${yPosition(value).toFixed(2)}`).join(' ');
    target.append(svg('path', {d:path, class:name}));
  }
  target.append(svg('text', {x:width/2,y:height-2,'text-anchor':'middle'}, 'Time within stored segment (seconds) · amplitude in dataset units'));
}

function setUpExample(examples) {
  const target = byId('example-view');
  target.innerHTML = `<div class="controls"><label for="example-trial">Recorded example</label><select id="example-trial"></select><label for="example-method">Quantizer</label><select id="example-method"><option value="uniform">Uniform</option><option value="mulaw">μ-law</option></select><label for="example-bits">Precision</label><select id="example-bits"></select></div><svg id="recorded-waveform" class="plot" viewBox="0 0 1000 290" role="img" aria-label="Recorded Oz waveform and archived reconstruction"></svg><div class="legend"><span><i class="key"></i>Original Oz</span><span><i class="key coral"></i>Reconstructed Oz</span></div><p id="example-decision" class="result-callout" aria-live="polite"></p><div id="example-scores"></div><p class="small">Four predetermined examples: all targets from the first evaluation participant's first block. They were not selected for a striking effect. Waveforms are rounded for display; metrics use full arrays.</p><a id="example-archive" class="source-note">Download this trial's actual ZIP archive</a>`;
  for (const trial of examples.trials) byId('example-trial').add(new Option(`${trial.id} · target ${trial.target_hz} Hz`, trial.id));
  for (const bits of [16,12,8,6,4,2]) byId('example-bits').add(new Option(`${bits} bits`, bits));
  byId('example-bits').value = '2';
  function update() {
    const trial = examples.trials.find(row => row.id === byId('example-trial').value);
    const condition = trial.conditions.find(row => row.method === byId('example-method').value && row.bits === Number(byId('example-bits').value));
    drawWaveform(byId('recorded-waveform'), trial.original, condition.reconstruction, examples.sample_rate_hz);
    byId('example-decision').textContent = `Target: ${trial.target_hz} Hz. Original decision: ${trial.original_prediction_hz} Hz. Reconstructed decision: ${condition.prediction_hz} Hz. Archive: ${condition.archive_bytes} B. NRMSE: ${fixed(condition.nrmse)}.`;
    byId('example-scores').replaceChildren(makeTable(['Candidate target','Original FFT score','Reconstructed FFT score'], examples.target_frequencies_hz.map((f,i) => [`${f} Hz`,trial.original_scores[i].toExponential(3),condition.scores[i].toExponential(3)])));
    const archive = byId('example-archive');
    archive.hidden = trial !== examples.trials[0];
    archive.href = `results/archives/${trial.id}-${condition.method}-${condition.bits}.zip`;
    archive.download = '';
  }
  for (const id of ['example-trial','example-method','example-bits']) byId(id).addEventListener('change', update);
  update();
}

function renderPrecision(summary) {
  const conditions = summary.conditions.filter(row => row.split === 'evaluation');
  const baseline = conditions.find(row => row.method === 'float32');
  const target = byId('precision-results');
  target.innerHTML = `<div class="controls"><label for="result-method">Quantizer</label><select id="result-method"><option value="uniform">Uniform</option><option value="mulaw">μ-law</option></select><label for="result-bits">Precision</label><select id="result-bits"></select></div><div id="condition-metrics" aria-live="polite"></div><p id="transition-summary" class="takeaway"></p><details><summary>Participant-level results for this condition</summary><div id="participant-results"></div></details>`;
  for (const bits of summary.provenance.configuration.bit_depths) byId('result-bits').add(new Option(`${bits} bits`, bits));
  byId('result-bits').value = String(summary.provenance.configuration.primary_bit_depth);
  function update() {
    const row = conditions.find(row => row.method === byId('result-method').value && row.bits === Number(byId('result-bits').value));
    const delta = 100 * (row.accuracy - baseline.accuracy);
    byId('condition-metrics').replaceChildren(metrics([
      [`${fixed(row.archive_bytes_per_second_channel,2)} B/s/ch`,'Actual ZIP storage, including reconstruction metadata'],
      [percent(row.accuracy),`Recognition accuracy; original ${percent(baseline.accuracy)}`],
      [`${delta >= 0 ? '+' : ''}${fixed(delta,2)} pp`,`Accuracy change; mean NRMSE ${fixed(row.mean_nrmse)}`],
    ]));
    const t = row.transitions;
    const flips = Math.round(row.flip_rate * row.n);
    byId('transition-summary').textContent = `${flips}/${row.n} predictions changed. ${t.correct_to_wrong} originally correct decisions became wrong; ${t.wrong_to_correct} wrong decisions became correct. Accuracy alone does not describe all these transitions. The archive is ${percent(row.archive_fraction_of_float32)} of the centered float32 payload.`;
    byId('participant-results').replaceChildren(makeTable(['Participant','Trials','Original accuracy','Reconstructed accuracy','Prediction flips'], row.participants.map(p => [`S${String(p.subject).padStart(2,'0')}`,p.n,percent(p.original_accuracy),percent(p.accuracy),`${Math.round(p.flip_rate*p.n)}/${p.n}`])));
  }
  for (const id of ['result-method','result-bits']) byId(id).addEventListener('change',update);
  update();
  target.append(figure('results/precision.png','Measured recognition accuracy and normalized waveform error versus actual ZIP bytes per second per channel'));
  const notes = document.createElement('p'); notes.className = 'small';
  notes.textContent = `Lossless float32 + ZIP: ${fixed(baseline.archive_bytes_per_second_channel,2)} B/s/channel, with byte-for-byte recovery. The uncompressed float32 payload is 1,000 B/s/channel. Each trial is archived separately; totals sum independent archives. The four-class chance level is 25%. No clinical safety is implied.`;
  target.append(notes);
  const details = document.createElement('details');
  details.innerHTML = '<summary>All measured evaluation conditions</summary>';
  details.append(makeTable(['Method','Bits','ZIP B/s/ch','Payload B','Archive B','Accuracy','NRMSE','Flips'], conditions.map(row => [methodName(row.method),row.bits,fixed(row.archive_bytes_per_second_channel,2),row.payload_bytes_total,row.archive_bytes_total,percent(row.accuracy),fixed(row.mean_nrmse),Math.round(row.flip_rate*row.n)])));
  target.append(details);
  const heading = document.createElement('h3'); heading.textContent = 'Inspect a real reconstructed trial'; heading.style.marginTop = '32px';
  const example = document.createElement('div'); example.id = 'example-view'; example.className = 'lab-panel';
  target.append(heading,example);
}

function renderGap(summary) {
  const target = byId('gap-results');
  target.innerHTML = `<div class="controls"><label for="gap-bits">Uniform quantization</label><select id="gap-bits"></select></div><p id="gap-status" class="result-callout" aria-live="polite"></p><div id="gap-groups"></div><p id="gap-thresholds" class="small"></p><div id="gap-predictors"></div><p id="gap-control" class="small"></p>`;
  for (const bits of summary.provenance.configuration.bit_depths) byId('gap-bits').add(new Option(`${bits} bits`,bits));
  byId('gap-bits').value = String(summary.provenance.configuration.primary_bit_depth);
  function update() {
    const row = summary.gap_analysis.find(row => row.bits === Number(byId('gap-bits').value));
    const primary = row.bits === summary.provenance.configuration.primary_bit_depth;
    byId('gap-status').textContent = `${row.failures}/${row.n} predictions changed. ${primary ? 'Prespecified primary condition.' : 'Exploratory precision; primary condition is 2 bits.'}`;
    byId('gap-groups').replaceChildren(makeTable(['Original score gap','Trials','Prediction flip rate','Correct → wrong / originally correct'], ['low','middle','high'].map(group => {
      const g = row.groups[group];
      return [group,g.n,percent(g.flip_rate),`${g.transitions?.correct_to_wrong ?? 0}/${g.original_correct_count ?? 0} (${percent(g.correct_to_wrong_rate)})`];
    })));
    const [low,high] = summary.gap_thresholds;
    byId('gap-thresholds').textContent = `Development thresholds: ${fixed(low,4)} and ${fixed(high,4)}. These were fixed using 48 trials from S1–S2. Evaluation groups need not have equal sizes. Gap = (best score − runner-up score) / (best score + runner-up score + ε).`;
    byId('gap-predictors').replaceChildren(makeTable(['Prediction-flip predictor','ROC AUC'], [['Low original score gap',fixed(row.predictor_auc.low_gap)],['Amplitude range / RMS',fixed(row.predictor_auc.range_over_rms)],['Low spectral concentration',fixed(row.predictor_auc.low_spectral_concentration)],['Shuffled gap: null mean',fixed(row.shuffled_auc_mean)]]));
    byId('gap-control').textContent = row.predictor_auc.low_gap === null
      ? 'AUC and the permutation test are undefined because this condition has only one outcome class. Zero observed flips does not establish universal safety.'
      : `500 shuffles within participant and true-target groups: null AUC range ${row.shuffled_auc_95_range.map(v=>fixed(v)).join('–')} (central 95%); one-sided permutation p = ${fixed(row.permutation_p_one_sided,4)}. The null mean need not be 0.5 because between-participant and target differences remain. This is a null range, not a confidence interval. Other precisions are exploratory; p values are not multiplicity-corrected.`;
  }
  byId('gap-bits').addEventListener('change',update); update();
  target.append(figure('results/gap.png','Measured prediction flip rates by original score gap and bit depth'));
  target.append(figure('results/predictors.png','Primary two-bit predictor comparison with a stratified shuffled-gap null control'));
  const limitation = document.createElement('p'); limitation.className = 'takeaway';
  limitation.textContent = 'The relationship is descriptive for this cohort, quantizer and frozen decoder. A prediction flip can correct an error or create one. Six evaluation participants are too limited to establish a general rule for EEG compression.';
  target.append(limitation);
}

export async function loadExperimentResults() {
  try {
    const response = await fetch('results/summary.json');
    if (!response.ok) throw new Error('No recorded run is available.');
    const summary = await response.json();
    if (summary.status !== 'measured' || summary.schema_version !== 1) throw new Error('Unsupported result format.');
    const config = summary.provenance.configuration;
    const status = byId('experiment-status');
    status.replaceChildren();
    const text = document.createElement('p');
    text.textContent = `Measured public EEG: ${summary.development_trials} development trials (S1–S2), ${summary.evaluation_trials} evaluation trials (S3–S8). All eight participants are experienced SSVEP users. Four targets (9, 11, 13, 15 Hz), three occipital channels, four seconds per trial at 250 Hz. No artifact rejection; no classifier training or evaluation-set tuning.`;
    const links = document.createElement('p'); links.className = 'inline-links';
    for (const [href,label] of [['results/trials.csv','Trial-level CSV'],['results/provenance.json','Run settings & provenance'],['results/original_trials.csv','Original decisions CSV']]) {
      const a = document.createElement('a'); a.href=href; a.textContent=label; links.append(a);
    }
    status.append(text,links);
    const details = document.createElement('details'); details.innerHTML = '<summary>Representation, timing and reproducibility</summary>';
    for (const note of summary.provenance.notes) { const p = document.createElement('p'); p.className='small'; p.textContent=note; details.append(p); }
    const p = document.createElement('p'); p.className='small';
    p.textContent = `Stored window: samples ${config.start_sample}:${config.stop_sample}; 0.14–4.14 s after stimulus onset. Channels: ${config.channels.join(', ')}. Run generated ${summary.provenance.generated_at_utc}. Source commit: ${summary.provenance.code_commit}.`;
    details.append(p); status.append(details);
    renderPrecision(summary); renderGap(summary);
    const examplesResponse = await fetch('results/examples.json');
    if (!examplesResponse.ok) throw new Error('The result summary loaded but example waveforms could not load.');
    setUpExample(await examplesResponse.json());
  } catch (error) {
    byId('experiment-status').textContent = `${error.message} Run the experiment command in the repository to generate the exports; no placeholder numbers are shown.`;
  }
}
