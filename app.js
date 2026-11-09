import { makeZip, measureNestedZip, supportsZipLab } from './zip.js';
import { DEFAULT_SEED, SAMPLE_SIZE, findTokens, makeHuffmanCodes, makeSamples, randomGenerator, shuffle } from './samples.js';

const byId = id => document.getElementById(id);
const number = new Intl.NumberFormat('en');
const percent = new Intl.NumberFormat('en', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const bytes = size => `${number.format(size)} B`;
const maxPasses = 8;
const canRun = supportsZipLab();
const initialSamples = makeSamples();
const sampleLabels = {
  zeros: 'All zeros',
  repeat: 'Repeated block',
  shuffled: 'Same bytes, shuffled',
  noise: 'Random bytes',
};

function drawOverview() {
  const palette = ['#ff9666', '#e56f50', '#a54e48', '#8ed2c8', '#519a9a', '#526a8c', '#e4c794', '#324359'];
  const motif = [0, 0, 1, 2, 3, 4, 5, 7, 0, 1, 2, 7, 3, 3, 4, 6];
  const ordered = Array.from({ length: 64 }, (_, i) => motif[i % motif.length]);
  const mixed = shuffle([...ordered], randomGenerator(42));
  for (const [id, values] of [['hero-order', ordered], ['hero-shuffle', mixed]]) {
    byId(id).replaceChildren(...values.map(value => {
      const cell = document.createElement('span');
      cell.style.setProperty('--cell', palette[value]);
      return cell;
    }));
  }
}

function setUpHuffman() {
  const sample = byId('huffman-sample');
  const messages = { skewed: 'AAABAACAAABAAAAD', balanced: 'ABCDABCDABCDABCD' };

  function drawCodebook() {
    const message = messages[sample.value];
    const codes = makeHuffmanCodes(Array.from(message, symbol => ({ symbol })));
    const bySymbol = new Map(codes.map(({ symbol, bits }) => [symbol, bits]));
    const byCode = new Map(codes.map(({ symbol, bits }) => [bits, symbol]));
    const words = Array.from(message, symbol => bySymbol.get(symbol));
    const encoded = words.join('');
    let prefix = '';
    let decoded = '';
    for (const bit of encoded) {
      prefix += bit;
      if (byCode.has(prefix)) {
        decoded += byCode.get(prefix);
        prefix = '';
      }
    }

    byId('huffman-input').textContent = message;
    byId('huffman-rows').replaceChildren(...[...codes].sort((a, b) => a.symbol.localeCompare(b.symbol)).map(({ symbol, count, bits }, index) => {
      const row = document.createElement('tr');
      const label = document.createElement('th');
      label.scope = 'row';
      label.textContent = symbol;
      row.append(label);
      for (const value of [count, index.toString(2).padStart(2, '0'), bits]) row.insertCell().textContent = value;
      return row;
    }));
    byId('huffman-summary').textContent = `Fixed-length: ${message.length * 2} bits. Huffman: ${encoded.length} bits.`;
    byId('huffman-stream').textContent = words.join(' ');
    byId('huffman-decoded').textContent = `Decoded from the unspaced bit stream: ${decoded}`;
  }

  sample.addEventListener('change', drawCodebook);
  drawCodebook();
}

function setUpTheory() {
  const sample = byId('theory-sample');
  const prev = byId('theory-prev');
  const next = byId('theory-next');
  let step = 0;
  let tokens;

  function drawStep() {
    const input = sample.selectedOptions[0].textContent;
    tokens = findTokens(input);
    const { start, length, distance, symbol } = tokens[step];
    const last = step === tokens.length - 1;
    byId('theory-bytes').replaceChildren(...Array.from(input, (value, index) => {
      const tile = document.createElement('span');
      tile.textContent = value;
      if (index >= start && index < start + length) tile.className = 'current';
      if (distance && index >= start - distance && index < Math.min(start, start - distance + length)) {
        tile.className = 'source';
      }
      return tile;
    }));
    byId('theory-message').textContent = distance
      ? `“${input.slice(start, start + length)}” can be reconstructed by copying ${length} bytes from ${distance} bytes back.`
      : `Write “${symbol}” as a literal. There’s no match of at least three bytes starting here.`;
    byId('theory-tokens').textContent = tokens.slice(0, step + 1).map(token => token.symbol).join('  ·  ');
    byId('theory-count').textContent = `${step + 1} / ${tokens.length} symbols`;
    byId('theory-codes').replaceChildren(...makeHuffmanCodes(tokens).map(({ symbol, bits, count }) => {
      const code = document.createElement('span');
      code.textContent = `${symbol} → ${bits} (×${count})`;
      return code;
    }));
    prev.disabled = step === 0;
    next.textContent = last ? 'Start over ↻' : 'Next symbol →';
  }

  sample.addEventListener('change', () => { step = 0; drawStep(); });
  prev.addEventListener('click', () => { step--; drawStep(); });
  next.addEventListener('click', () => {
    step = (step + 1) % tokens.length;
    drawStep();
  });
  drawStep();
}

// Labels come only from the fixed sample names and pass numbers above.
function drawChart(target, rows, label, baseline) {
  const largest = Math.max(baseline, ...rows.map(row => row.size));
  target.innerHTML = `<table class="chart" aria-label="${label}">
    <thead><tr><th scope="col">${label}</th><th scope="col">Size (linear)</th><th scope="col">Bytes</th></tr></thead>
    <tbody>${rows.map(row => `<tr class="${row.highlight ?? ''}">
      <th scope="row">${row.label}</th>
      <td><div class="bar-track" aria-hidden="true"><div class="bar" style="width:${100 * row.size / largest}%"></div></div></td>
      <td>${bytes(row.size)}${row.note ? `<span class="delta">${row.note}</span>` : ''}</td>
    </tr>`).join('')}</tbody></table>`;
}

function sizeChange(previous, current) {
  if (current === previous) return 'No change';
  const sign = current > previous ? '+' : '−';
  return `${sign}${bytes(Math.abs(current - previous))}`;
}

async function runExperiment(prefix, work) {
  const results = byId(`${prefix}-results`);
  const summary = byId(`${prefix}-summary`);
  const button = byId(`${prefix}-run`);
  const chart = byId(`${prefix}-chart`);
  button.disabled = true;
  chart.replaceChildren();
  if (!canRun) {
    summary.textContent = 'This browser can’t run raw DEFLATE. Open the lab in an up-to-date browser to measure ZIP sizes.';
    return;
  }
  summary.textContent = 'Measuring ZIP archives…';
  results.setAttribute('aria-busy', 'true');
  try {
    await work(summary, chart);
  } catch (error) {
    console.error(error);
    summary.textContent = 'The experiment could not finish. Try running it again.';
  } finally {
    results.setAttribute('aria-busy', 'false');
    button.disabled = false;
  }
}

function runNesting() {
  const sample = byId('nest-sample');
  const download = byId('nest-download');
  const check = byId('nest-check');
  download.hidden = true;
  check.textContent = '';
  sample.disabled = true;
  return runExperiment('nest', async (summary, chart) => {
    const input = initialSamples[sample.value];
    const { archive, sizes, stopped } = await measureNestedZip(input, maxPasses);
    const last = sizes.length - 1;
    const smallest = Math.min(...sizes);
    summary.textContent = stopped
      ? `Pass ${last} was the first with no further savings. Smallest measured size: ${bytes(smallest)}.`
      : `All ${maxPasses} passes saved bytes. Smallest measured size: ${bytes(smallest)}.`;
    drawChart(chart, sizes.map((size, pass) => ({
      label: pass ? `Pass ${pass}` : 'Original', size,
      highlight: stopped && pass === last ? 'focus-row' : size === smallest ? 'best-row' : '',
      note: pass ? sizeChange(sizes[pass - 1], size) : '',
    })), 'ZIP pass', input.length);
    check.textContent = `Unpacked all ${last} ${last === 1 ? 'layer' : 'layers'} and matched every original byte. Changes are relative to the previous row.`;
    download.onclick = () => {
      const url = URL.createObjectURL(new Blob([archive], { type: 'application/zip' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `zip-lab-pass-${last}.zip`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    download.hidden = false;
  }).finally(() => { sample.disabled = !canRun; });
}

function runStructure(seed, samples) {
  byId('structure-size').textContent = `256 KiB each · seed ${seed}`;
  return runExperiment('structure', async (summary, chart) => {
    const rows = await Promise.all(Object.entries(samples).map(async ([key, input]) => {
      const size = (await makeZip(input)).length;
      const saving = (input.length - size) / input.length;
      return {
        key, label: sampleLabels[key], size,
        note: saving > 0 ? `${percent(saving)} saved` : saving < 0 ? `${percent(-saving)} larger` : 'No change',
        highlight: key === 'shuffled' ? 'focus-row' : '',
      };
    }));
    const repeat = rows.find(row => row.key === 'repeat');
    const mixed = rows.find(row => row.key === 'shuffled');
    summary.textContent = `Same byte counts, different order: ${bytes(repeat.size)} repeated versus ${bytes(mixed.size)} shuffled.`;
    drawChart(chart, [{ label: 'Original (each)', size: SAMPLE_SIZE }, ...rows], 'Input', SAMPLE_SIZE);
  });
}

let startedZip = false;
let activePage;
function showPage(focusHeading = false) {
  const fragment = location.hash.slice(1);
  const page = fragment === 'mp3' ? 'mp3' : fragment === 'zip' || fragment.startsWith('zip-') ? 'zip' : 'overview';
  const changed = page !== activePage;
  activePage = page;
  for (const panel of document.querySelectorAll('[data-page]')) panel.hidden = panel.id !== page;
  for (const link of document.querySelectorAll('[data-nav]')) {
    if (link.dataset.nav === page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  document.title = page === 'overview' ? 'Compression Lab · DA3021' : `${page.toUpperCase()} · Compression Lab`;
  if (fragment.startsWith('zip-')) byId(fragment)?.scrollIntoView();
  else if (changed) {
    window.scrollTo(0, 0);
    if (focusHeading) byId(`${page}-title`).focus({ preventScroll: true });
  }
  if (page === 'zip' && !startedZip) {
    startedZip = true;
    runNesting();
    runStructure(DEFAULT_SEED, initialSamples);
  }
}

drawOverview();
setUpHuffman();
setUpTheory();
document.querySelector('.skip').addEventListener('click', event => {
  event.preventDefault();
  byId('main').focus();
});
byId('nest-run').addEventListener('click', runNesting);
byId('nest-sample').addEventListener('change', runNesting);
byId('structure-run').addEventListener('click', () => {
  const [seed] = crypto.getRandomValues(new Uint32Array(1));
  runStructure(seed, makeSamples(seed));
});
window.addEventListener('hashchange', () => showPage(true));
showPage();
