// Cohort uncertainty, pilot replication and alternative-decoder views.
import { makeTable } from "./table.js";

const byId = (id) => document.getElementById(id);
const tasks = { SSVEP: "SSVEP", MI: "Motor imagery", ERP: "P300 detection" };
const methods = {
  uniform: "Uniform + ZIP",
  mulaw: "μ-law + ZIP",
  dct: "DCT + ZIP",
};
const percent = (n) => `${(100 * n).toFixed(1)}%`;
const loss = (n) => `${(100 * n).toFixed(2)} pp`;

export function interval(estimate) {
  const bounds = estimate.ci95.map((n) => (100 * n).toFixed(2)).join(" to ");
  return `${loss(estimate.mean)} [${bounds}]`;
}

function group(data, task, method, budget = 32) {
  return data.groups.find(
    (g) => g.task === task && g.method === method && g.budget === budget,
  );
}

function largestTasks(data, method) {
  const selected = data.groups.filter(
    (g) => g.method === method && g.budget === 32,
  );
  const maximum = Math.max(...selected.map((g) => g.balanced_accuracy_drop));
  return selected
    .filter((g) => Math.abs(g.balanced_accuracy_drop - maximum) < 1e-10)
    .map((g) => tasks[g.task])
    .join(" / ");
}

export function renderPairedTables(data, statistics) {
  const budget = Number(byId("benchmark-budget").value);
  const estimates = statistics.primary.groups.filter(
    (g) => g.budget === budget,
  );
  byId("winner-results").replaceChildren(
    makeTable(
      [
        "Method",
        ...data.config.tasks.map((t) => `${tasks[t]} largest-loss share`),
      ],
      data.config.methods.map((method) => [
        methods[method],
        ...data.config.tasks.map((task) =>
          percent(
            estimates.find((g) => g.task === task && g.method === method)
              .largest_loss_share,
          ),
        ),
      ]),
    ),
  );
  byId("paired-results").replaceChildren(
    makeTable(
      [
        "Method",
        "First task minus second task",
        "Difference in loss [95% interval]",
      ],
      statistics.primary.task_differences
        .filter((g) => g.budget === budget)
        .map((g) => [
          methods[g.method],
          `${tasks[g.first]} minus ${tasks[g.second]}`,
          interval(g),
        ]),
    ),
  );
}

function renderRobustness(primary, statistics) {
  const budget = Number(byId("robustness-budget").value);
  const rows = primary.config.tasks.flatMap((task) =>
    [
      ["Primary", "primary"],
      ["Alternative", "alternative"],
    ].map(([label, family]) => {
      const baseline = statistics[family].baselines.find(
        (g) => g.task === task,
      );
      return [
        tasks[task],
        label,
        percent(baseline.mean),
        ...primary.config.methods.map((method) =>
          interval(
            statistics[family].groups.find(
              (g) =>
                g.task === task && g.method === method && g.budget === budget,
            ),
          ),
        ),
      ];
    }),
  );
  byId("robustness-results").replaceChildren(
    makeTable(
      [
        "Task",
        "Decoder",
        "Original score",
        "Uniform loss [95% interval]",
        "μ-law loss [95% interval]",
        "DCT loss [95% interval]",
      ],
      rows,
    ),
  );
}

export function renderExtension(
  primary,
  alternative,
  statistics,
  pilot,
  verification,
  alternateVerification,
) {
  const config = primary.config;
  const original = (task) =>
    statistics.primary.baselines.find((g) => g.task === task).mean;
  byId("baseline-story").textContent =
    `The starting points differ: ${config.tasks
      .map((t) => `${tasks[t]} starts at ${percent(original(t))}`)
      .join(
        ", ",
      )}. A loss of a few points need not have the same practical meaning for each task. The individual baselines remain visible, including weak ones.`;
  for (const method of config.methods) {
    byId(`${method}-story`).textContent =
      `At the tightest allowance, 32 bytes/s/channel, ${config.tasks
        .map(
          (task) =>
            `${tasks[task]} loses ${loss(group(primary, task, method).balanced_accuracy_drop)}`,
        )
        .join(
          ", ",
        )}. At 256 bytes/s/channel, the respective losses are ${config.tasks
        .map((task) =>
          loss(group(primary, task, method, 256).balanced_accuracy_drop),
        )
        .join(
          ", ",
        )}. These are means across people; the bands and intervals show how precisely this cohort estimates them.`;
  }
  const replicationRows = config.methods.flatMap((method) =>
    config.tasks.map((task) => [
      methods[method],
      tasks[task],
      loss(group(pilot, task, method).balanced_accuracy_drop),
      interval(
        statistics.primary.groups.find(
          (g) => g.task === task && g.method === method && g.budget === 32,
        ),
      ),
    ]),
  );
  byId("replication-results").replaceChildren(
    makeTable(
      [
        "Method",
        "Task",
        "Pilot loss (4 people)",
        "New loss (20 people) [95% interval]",
      ],
      replicationRows,
    ),
  );
  byId("replication-story").textContent =
    `The pilot's largest mean losses at 32 bytes/s/channel were ${config.methods
      .map((method) => `${largestTasks(pilot, method)} with ${methods[method]}`)
      .join("; ")}. In the new cohort they are ${config.methods
      .map(
        (method) => `${largestTasks(primary, method)} with ${methods[method]}`,
      )
      .join(
        "; ",
      )}. A change in this descriptive order is worth reporting, rather than choosing only the people who reproduce the pilot.`;
  byId("robustness-story").textContent =
    `With the alternative decoders at the tightest allowance, the largest mean losses belong to ${config.methods
      .map(
        (method) =>
          `${largestTasks(alternative, method)} under ${methods[method]}`,
      )
      .join(
        "; ",
      )}. Compare these with the primary results above and check the original scores: changing the decoder can also change how much useful performance exists before compression.`;
  const p300 = group(primary, "ERP", "dct");
  byId("prediction-story").textContent =
    `For P300 with DCT at the tightest allowance, the mean score loss is ${loss(p300.balanced_accuracy_drop)}, while ${percent(p300.flip_rate)} of individual decisions change on average. Some changes correct original mistakes and others introduce new ones. A similar total score need not mean the same decision on each flash.`;
  byId("extension-findings").textContent =
    `At the tightest allowance with the primary decoders, the largest mean loss belongs to ${config.methods
      .map(
        (method) => `${largestTasks(primary, method)} under ${methods[method]}`,
      )
      .join(
        "; ",
      )}. The individual results and second-decoder check show why an average ordering must be read together with the analysis system and its starting performance. The question is which task–decoder combinations survive these compressors, rather than which brain task is intrinsically hardest.`;
  byId("verification-story").textContent =
    `All ${verification.measured_points} primary conditions, including development runs, and ${alternateVerification.measured_points} alternative-decoder conditions fit their byte caps. The lossless control recovers the selected float32 samples exactly. Independent checks recomputed metrics from exported predictions and replayed ${verification.evaluation_reconstructions + alternateVerification.evaluation_reconstructions} evaluation reconstructions through their frozen decoders. No clinical, real-time or battery-life claim is made.`;
  renderPairedTables(primary, statistics);
  renderRobustness(primary, statistics);
  byId("robustness-budget").addEventListener("change", () =>
    renderRobustness(primary, statistics),
  );
}

export async function readResults(path) {
  const response = await fetch(`${path}?v=openbmi-extension-1`);
  if (!response.ok) throw new Error("A measured-result export is unavailable.");
  return response.json();
}
