// Display recorded exports only. No simulated research metrics.
import { makeTable } from "./table.js";
const byId = (id) => document.getElementById(id);
const tasks = { SSVEP: "SSVEP", MI: "Motor imagery", ERP: "P300 detection" };
const methods = {
  uniform: "Uniform + ZIP",
  mulaw: "μ-law + ZIP",
  dct: "DCT + ZIP",
};
const colors = { SSVEP: "#86dbce", MI: "#ffac8f", ERP: "#9ebbf9" };
const percent = (n) => `${(100 * n).toFixed(1)}%`;
const loss = (n) => `${(100 * n).toFixed(2)} pp`;
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

function retainedAboveChance(group) {
  if (!group.complete) return "Unavailable";
  const chance = group.task === "SSVEP" ? 0.25 : 0.5;
  const original = group.original_balanced_accuracy - chance;
  return original > 0.05
    ? percent((group.balanced_accuracy - chance) / original)
    : "Original baseline too weak";
}

function svg(tag, attributes, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes))
    node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function curves(groups, config) {
  const chart = svg("svg", {
    viewBox: "0 0 1000 400",
    role: "img",
    class: "plot benchmark-plot",
    "aria-label":
      "Mean balanced-accuracy loss at tested byte caps for three EEG applications",
  });
  const values = groups
    .filter((g) => g.complete)
    .map((g) => g.balanced_accuracy_drop * 100);
  const low = Math.min(-2, Math.floor(Math.min(...values) / 5) * 5);
  const high = Math.max(5, Math.ceil(Math.max(...values) / 5) * 5);
  const budgets = config.budgets_bytes_per_second_channel;
  const x = (b) =>
    90 +
    (870 * Math.log2(b / budgets[0])) / Math.log2(budgets.at(-1) / budgets[0]);
  const y = (v) => 36 + (282 * (high - v)) / (high - low);
  for (let i = 0; i <= 5; i++) {
    const v = low + (i * (high - low)) / 5;
    chart.append(
      svg("line", { x1: 90, x2: 960, y1: y(v), y2: y(v), class: "grid" }),
    );
    chart.append(
      svg("text", { x: 78, y: y(v) + 4, "text-anchor": "end" }, v.toFixed(1)),
    );
  }
  chart.append(
    svg("line", {
      x1: 90,
      x2: 960,
      y1: y(0),
      y2: y(0),
      stroke: "#b1c0ca",
      "stroke-dasharray": "5 5",
    }),
  );
  for (const budget of budgets)
    chart.append(
      svg("text", { x: x(budget), y: 346, "text-anchor": "middle" }, budget),
    );
  for (const task of config.tasks) {
    const selected = groups
      .filter((g) => g.task === task && g.complete)
      .sort((a, b) => a.budget - b.budget);
    if (selected.length === budgets.length)
      chart.append(
        svg("polyline", {
          points: selected
            .map((g) => `${x(g.budget)},${y(100 * g.balanced_accuracy_drop)}`)
            .join(" "),
          fill: "none",
          stroke: colors[task],
          "stroke-width": 2,
        }),
      );
    for (const g of selected) {
      const point = svg("circle", {
        cx: x(g.budget),
        cy: y(100 * g.balanced_accuracy_drop),
        r: 5,
        fill: colors[task],
      });
      point.append(
        svg(
          "title",
          {},
          `${tasks[task]}: cap ${g.budget}, loss ${loss(g.balanced_accuracy_drop)}, actual ${g.rate.toFixed(1)} B/s/ch`,
        ),
      );
      chart.append(point);
    }
  }
  chart.append(
    svg(
      "text",
      { x: 520, y: 380, "text-anchor": "middle" },
      "Assigned cap (bytes/s/channel, logarithmic spacing)",
    ),
  );
  chart.append(
    svg(
      "text",
      { x: 90, y: 20 },
      "Balanced-accuracy loss (percentage points); lower is better",
    ),
  );
  return chart;
}

function baselines(data) {
  const rows = data.config.tasks.map((task) => {
    const subjects = data.baselines.filter(
      (b) => b.task === task && b.split === "evaluation",
    );
    const chance = task === "SSVEP" ? 0.25 : 0.5;
    return [
      tasks[task],
      percent(mean(subjects.map((b) => b.balanced_accuracy))),
      percent(chance),
      subjects
        .map(
          (b) =>
            `S${String(b.subject).padStart(2, "0")}: ${percent(b.balanced_accuracy)}${b.balanced_accuracy <= chance + 0.05 ? " (weak baseline)" : ""}`,
        )
        .join(" · "),
    ];
  });
  byId("baseline-results").replaceChildren(
    makeTable(
      [
        "Application",
        "Original balanced accuracy",
        "Chance",
        "Participant baselines",
      ],
      rows,
    ),
  );
}

function renderTask(data) {
  const groups = data.groups.filter(
    (g) => g.method === byId("benchmark-method").value,
  );
  const legend = document.createElement("p");
  legend.className = "benchmark-legend";
  for (const task of data.config.tasks) {
    const label = document.createElement("span");
    label.textContent = tasks[task];
    label.style.color = colors[task];
    legend.append(label);
  }
  const rows = groups.map((g) => [
    tasks[g.task],
    g.budget,
    g.complete ? g.rate.toFixed(1) : "Unavailable",
    g.complete ? percent(g.balanced_accuracy) : "Unavailable",
    g.complete ? loss(g.balanced_accuracy_drop) : "Unavailable",
    retainedAboveChance(g),
    g.complete
      ? g.balanced_accuracy_drop_range.map(loss).join(" to ")
      : "Unavailable",
    g.complete ? g.nrmse.toFixed(3) : "Unavailable",
  ]);
  byId("task-results").replaceChildren(
    legend,
    curves(groups, data.config),
    makeTable(
      [
        "Application",
        "Cap B/s/ch",
        "Actual mean B/s/ch",
        "Balanced accuracy",
        "Mean loss",
        "Above-chance performance retained",
        "Participant loss range",
        "NRMSE",
      ],
      rows,
    ),
  );
}

function renderRanking(data) {
  const budget = Number(byId("benchmark-budget").value);
  const groups = data.groups.filter((g) => g.budget === budget);
  const rows = data.config.tasks.map((task) => [
    tasks[task],
    ...data.config.methods.map((method) => {
      const g = groups.find((g) => g.task === task && g.method === method);
      return g?.complete ? loss(g.balanced_accuracy_drop) : "Unavailable";
    }),
  ]);
  const findings = document.createElement("p");
  findings.className = "note";
  findings.textContent =
    data.config.methods
      .map((method) => {
        const selected = groups
          .filter((g) => g.method === method && g.complete)
          .sort((a, b) => b.balanced_accuracy_drop - a.balanced_accuracy_drop);
        if (selected.length !== 3)
          return `${methods[method]}: incomplete comparison`;
        const max = selected[0].balanced_accuracy_drop;
        const tied = selected.filter(
          (g) => Math.abs(g.balanced_accuracy_drop - max) < 1e-10,
        );
        return `${methods[method]}: ${tied.map((g) => tasks[g.task]).join(" / ")}${tied.length > 1 ? " tied" : " had the largest mean loss"} (${loss(max)})`;
      })
      .join(". ") +
    ". These are descriptive orders in four evaluation participants, not a statistically established general ranking.";
  byId("ranking-results").replaceChildren(
    makeTable(
      [
        "Mean balanced-accuracy loss",
        ...data.config.methods.map((m) => methods[m]),
      ],
      rows,
    ),
    findings,
  );
  const individual = data.points
    .filter((p) => p.split === "evaluation" && p.budget === budget)
    .map((p) => [
      `S${String(p.subject).padStart(2, "0")}`,
      tasks[p.task],
      methods[p.method],
      p.feasible ? percent(p.balanced_accuracy) : "Unavailable",
      p.feasible ? loss(p.balanced_accuracy_drop) : "Unavailable",
      p.feasible ? p.rate.toFixed(1) : "Unavailable",
      p.feasible ? percent(p.flip_rate) : "Unavailable",
    ]);
  byId("participant-results").replaceChildren(
    makeTable(
      [
        "Participant",
        "Application",
        "Codec",
        "Balanced accuracy",
        "Loss",
        "Actual B/s/ch",
        "Prediction changes",
      ],
      individual,
    ),
  );
}

export async function loadExperimentResults() {
  try {
    const response = await fetch("results/benchmark/summary.json");
    if (!response.ok)
      throw new Error("The benchmark exports are not available yet.");
    const data = await response.json();
    if (!data.complete)
      throw new Error(
        "The benchmark is still incomplete. No final cross-task ranking is shown.",
      );
    baselines(data);
    renderTask(data);
    renderRanking(data);
    byId("benchmark-method").addEventListener("change", () => renderTask(data));
    byId("benchmark-budget").addEventListener("change", () =>
      renderRanking(data),
    );
    byId("experiment-status").textContent =
      `Measured OpenBMI benchmark: ${data.config.evaluation_subjects.length} evaluation participants, three applications, three compression pipelines and four storage caps. Exact float32 recovery was verified with the lossless control. Development participants are excluded from these means.`;
  } catch (error) {
    byId("experiment-status").textContent =
      `${error.message} The protocol and implementation are available in the repository; no placeholder results are displayed.`;
  }
}
