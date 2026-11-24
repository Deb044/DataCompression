import { makeHuffmanCodes, makeSamples } from "./samples.js";
import { makeZip, supportsZipLab } from "./zip.js";
import { quantize, signalPath, syntheticSignal } from "./signal.js";
import { papers } from "./literature.js";
import { makeTable } from "./table.js";
import { loadExperimentResults } from "./experiment-view.js";

const byId = (id) => document.getElementById(id);
const format = new Intl.NumberFormat("en", { maximumFractionDigits: 2 });
const svgNS = "http://www.w3.org/2000/svg";

function svgElement(tag, attributes) {
  const element = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attributes))
    element.setAttribute(key, value);
  return element;
}
function drawSignals(
  target,
  original,
  reconstruction,
  width = 1000,
  height = 260,
) {
  target.replaceChildren();
  const margin = { left: 42, right: 14, top: 16, bottom: 30 };
  for (const value of [-1, -0.5, 0, 0.5, 1]) {
    const y =
      margin.top + ((1 - value) / 2) * (height - margin.top - margin.bottom);
    target.append(
      svgElement("line", {
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y,
        class: "grid",
      }),
    );
    const label = svgElement("text", {
      x: margin.left - 9,
      y: y + 4,
      "text-anchor": "end",
    });
    label.textContent = value;
    target.append(label);
  }
  for (const [values, className] of [
    [original, "original"],
    [reconstruction, "reconstructed"],
  ])
    target.append(
      svgElement("path", {
        d: signalPath(values, width, height, margin),
        class: className,
      }),
    );
  const label = svgElement("text", {
    x: width / 2,
    y: height - 3,
    "text-anchor": "middle",
  });
  label.textContent = "Sample position (illustrative signal)";
  target.append(label);
}
function setUpBudget() {
  function update() {
    const channels = Number(byId("budget-channels").value);
    const minutes = Number(byId("budget-minutes").value);
    const bits = Number(byId("budget-bits").value);
    byId("budget-channels-value").textContent = channels;
    byId("budget-minutes-value").textContent = `${minutes} min`;
    byId("budget-size").textContent =
      `${format.format((channels * minutes * 60 * 250 * bits) / 8e6)} MB`;
    byId("budget-formula").textContent =
      `${channels} channels × ${minutes * 60} seconds × 250 samples/s × ${bits} bits ÷ 8`;
  }
  for (const id of ["budget-channels", "budget-minutes", "budget-bits"])
    byId(id).addEventListener("input", update);
  update();
}
function setUpHuffman() {
  const messages = { skewed: "AAABAACAAABAAAAD", balanced: "ABCDABCDABCDABCD" };
  function update() {
    const message = messages[byId("huffman-sample").value];
    const codes = makeHuffmanCodes(
      Array.from(message, (symbol) => ({ symbol })),
    );
    let length = 0;
    byId("huffman-rows").replaceChildren(
      ...codes
        .sort((a, b) => a.symbol.localeCompare(b.symbol))
        .map(({ symbol, count, bits }, index) => {
          length += count * bits.length;
          const row = document.createElement("tr");
          for (const [i, value] of [
            symbol,
            count,
            index.toString(2).padStart(2, "0"),
            bits,
          ].entries()) {
            const cell = document.createElement(i ? "td" : "th");
            if (!i) cell.scope = "row";
            cell.textContent = value;
            row.append(cell);
          }
          return row;
        }),
    );
    byId("huffman-input").textContent = message;
    byId("huffman-summary").textContent =
      `Fixed: ${message.length * 2} bits. Huffman: ${length} bits.`;
  }
  byId("huffman-sample").addEventListener("change", update);
  update();
}
function setUpQuantization() {
  const original = syntheticSignal(320);
  function update() {
    const bits = Number(byId("quant-bits").value);
    const reconstruction = original.map((value) =>
      quantize(value, bits, byId("quant-method").value),
    );
    const mse =
      original.reduce(
        (sum, value, i) => sum + (value - reconstruction[i]) ** 2,
        0,
      ) / original.length;
    byId("quant-bits-value").textContent = `${bits} bits · ${2 ** bits} levels`;
    byId("quant-error").textContent =
      `Computed RMSE: ${Math.sqrt(mse).toFixed(5)} in normalized amplitude units.`;
    drawSignals(byId("quant-chart"), original, reconstruction);
  }
  byId("quant-bits").addEventListener("input", update);
  byId("quant-method").addEventListener("change", update);
  update();
  drawSignals(
    byId("hero-signal"),
    original,
    original.map((value) => quantize(value, 4)),
    520,
    255,
  );
}
async function runZipDemo() {
  const button = byId("zip-run");
  const target = byId("zip-output");
  if (!supportsZipLab()) {
    target.textContent =
      "Raw DEFLATE streams are unavailable in this browser. The EEG experiments run separately in Python.";
    return;
  }
  button.disabled = true;
  target.textContent = "Measuring the actual ZIP archives…";
  try {
    const samples = makeSamples();
    const rows = [];
    for (const [key, label] of [
      ["repeat", "Repeated block"],
      ["shuffled", "Same bytes, shuffled"],
      ["noise", "Random bytes"],
    ]) {
      const size = (await makeZip(samples[key])).length;
      rows.push([
        label,
        `${format.format(size)} B`,
        `${format.format((100 * size) / samples[key].length)}%`,
      ]);
    }
    target.replaceChildren(
      makeTable(["Input", "ZIP bytes", "% of input"], rows),
    );
  } catch (error) {
    target.textContent = `The demonstration could not finish: ${error.message}`;
  } finally {
    button.disabled = false;
  }
}
function setUpLiterature() {
  function update() {
    const selected = byId("paper-filter").value;
    byId("paper-list").replaceChildren(
      ...papers
        .filter((paper) => selected === "all" || paper.family === selected)
        .map((paper) => {
          const article = document.createElement("article");
          article.className = "paper";
          // Curated local content only; no user input is interpolated.
          article.innerHTML = `<div><span class="year">${paper.year}</span><p class="small">${paper.status}</p></div><div><h3><a href="${paper.url}">${paper.title}</a></h3><p>${paper.authors}</p><p class="evidence">${paper.finding}</p></div><div class="paper-lesson"><strong>WHAT IT MEANS FOR US</strong><p>${paper.lesson}</p></div>`;
          return article;
        }),
    );
  }
  byId("paper-filter").addEventListener("change", update);
  update();
  fetch("content/references.json")
    .then((response) => {
      if (!response.ok) throw new Error("Reference list could not load.");
      return response.json();
    })
    .then((references) => {
      byId("reference-list").replaceChildren(
        ...references.map((reference, i) => {
          const item = document.createElement("div");
          const title = document.createElement("strong");
          title.textContent = `[${i + 1}] ${reference.title}`;
          const detail = document.createElement("p");
          detail.textContent = `${reference.authors}. ${reference.venue}. ${reference.note}`;
          const link = document.createElement("a");
          link.href = reference.url;
          link.textContent = "Open source";
          item.append(title, detail, link);
          return item;
        }),
      );
    })
    .catch((error) => {
      byId("reference-list").textContent =
        `${error.message} The complete list is also in the review PDF.`;
    });
}
const pages = ["overview", "techniques", "eeg", "literature", "experiments"];
let activePage;
function showPage(focus = false) {
  const requested = location.hash.slice(1);
  const page = pages.includes(requested) ? requested : "overview";
  const changed = page !== activePage;
  activePage = page;
  for (const element of document.querySelectorAll("[data-page]"))
    element.hidden = element.id !== page;
  for (const link of document.querySelectorAll("[data-nav]")) {
    if (link.dataset.nav === page) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  document.title =
    page === "overview"
      ? "EEG Compresion"
      : `${page[0].toUpperCase() + page.slice(1)} · EEG Compresion`;
  if (changed) {
    window.scrollTo(0, 0);
    if (focus) byId(`${page}-title`).focus({ preventScroll: true });
  }
}
setUpBudget();
setUpHuffman();
setUpQuantization();
setUpLiterature();
loadExperimentResults();
byId("zip-run").addEventListener("click", runZipDemo);
document.querySelector(".skip").addEventListener("click", (event) => {
  event.preventDefault();
  byId("main").focus();
});
window.addEventListener("hashchange", () => showPage(true));
showPage();
