"use strict";

const CONFIG = {
  pyodideVersion: "0.27.2",
  repo: "jpeckenpaugh/nexttext",
  sourceRef: "main",
};

const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${CONFIG.pyodideVersion}/full/`;
const PACKAGE_ROOT = "/nexttext";
const SOURCE_FILES = [
  "__init__.py",
  "bias.py",
  "core.py",
  "data/__init__.py",
  "data/gender_terms.py",
  "data/associative_terms.py",
];

const SCENARIOS = [
  {
    id: "debias",
    title: "Debias basics",
    op: "debias",
    text: [
      "A man seated at a table talking to a young girl.",
      "A girl kneeling to receive communion. Her hands are folded in prayer.",
      "A doctor speaking with his patient while a nurse takes her vitals.",
    ].join("\n"),
  },
  {
    id: "rebias-default",
    title: "Rebias (default)",
    op: "rebias_default",
    text: "A person working on a car.",
  },
  {
    id: "rebias-male",
    title: "Rebias contextual \u2014 male cues",
    op: "rebias_contextual",
    text: "A person working on a car with their tools.",
  },
  {
    id: "rebias-female",
    title: "Rebias contextual \u2014 female cues",
    op: "rebias_contextual",
    text: "A person holding a baby with their flowers.",
  },
  {
    id: "round-trip",
    title: "Round trip",
    op: "round_trip",
    text: "A woman holding a baby.",
  },
];

const BRIDGE_SOURCE = `
import json

from nexttext import debias, rebias, normalize_whitespace, word_frequencies
from nexttext.data.associative_terms import get_dominant_gender_from_text


def _demo_run(request_json):
    request = json.loads(request_json)
    op = request.get("op", "debias")
    text = request.get("text", "")
    labels = [line for line in text.splitlines() if line.strip()]

    diagnostics = {}
    if op == "debias":
        output = debias(labels)
    elif op == "rebias_default":
        output = rebias(labels, strategy="default")
    elif op == "rebias_contextual":
        output = rebias(labels, strategy="contextual")
        diagnostics["gender"] = [get_dominant_gender_from_text(line) for line in labels]
    elif op == "round_trip":
        output = rebias(debias(labels), strategy="contextual")
        diagnostics["gender"] = [get_dominant_gender_from_text(line) for line in labels]
    elif op == "normalize":
        output = [normalize_whitespace(text)]
    elif op == "word_frequencies":
        output = [word_frequencies(text)]
    else:
        raise ValueError("unknown operation: %s" % op)

    return json.dumps({"output": output, "diagnostics": diagnostics})
`;

const els = {
  status: document.getElementById("runtime-status"),
  statusText: document.getElementById("runtime-status-text"),
  scenarios: document.getElementById("scenarios"),
  form: document.getElementById("playground"),
  input: document.getElementById("input-text"),
  operation: document.getElementById("operation"),
  runButton: document.getElementById("run-button"),
  output: document.getElementById("output"),
  diagnostics: document.getElementById("diagnostics"),
  repoLink: document.getElementById("repo-link"),
  version: document.getElementById("meta-version"),
  python: document.getElementById("meta-python"),
  sourceRefLabel: document.getElementById("source-ref-label"),
};

let pyodide = null;
let demoRun = null;
let activeScenario = null;

function setStatus(state, text) {
  els.status.dataset.state = state;
  els.statusText.textContent = text;
}

function sourceUrl(file) {
  return `https://cdn.jsdelivr.net/gh/${CONFIG.repo}@${CONFIG.sourceRef}/src/nexttext/${file}`;
}

function sourceUrlFallback(file) {
  return `https://raw.githubusercontent.com/${CONFIG.repo}/${CONFIG.sourceRef}/src/nexttext/${file}`;
}

async function fetchText(file) {
  for (const url of [sourceUrl(file), sourceUrlFallback(file)]) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.text();
      }
    } catch (error) {
      /* try the next mirror */
    }
  }
  throw new Error(`Could not load source file: ${file}`);
}

async function readProjectMetadata() {
  try {
    const response = await fetch(
      `https://cdn.jsdelivr.net/gh/${CONFIG.repo}@${CONFIG.sourceRef}/pyproject.toml`
    );
    if (!response.ok) return;
    const toml = await response.text();
    const version = toml.match(/^version\s*=\s*"([^"]+)"/m);
    const pythonReq = toml.match(/^requires-python\s*=\s*"([^"]+)"/m);
    if (version) els.version.textContent = version[1];
    if (pythonReq) els.python.textContent = pythonReq[1].replace(/>=?\s*/, "\u2265 ");
  } catch (error) {
    /* metadata is decorative; keep defaults */
  }
}

async function initPyodide() {
  setStatus("loading", "Loading Python runtime\u2026");
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

  setStatus("loading", "Fetching nexttext sources\u2026");
  const sources = await Promise.all(SOURCE_FILES.map(fetchText));

  pyodide.FS.mkdirTree(`${PACKAGE_ROOT}/data`);
  SOURCE_FILES.forEach((file, index) => {
    pyodide.FS.writeFile(`${PACKAGE_ROOT}/${file}`, sources[index], { encoding: "utf8" });
  });

  pyodide.runPython("import sys; sys.path.insert(0, '/')");
  pyodide.runPython(BRIDGE_SOURCE);
  demoRun = pyodide.globals.get("_demo_run");

  setStatus("ready", `Ready \u2014 loaded from ${CONFIG.sourceRef}`);
  els.runButton.disabled = false;
}

function renderOutput(result) {
  const { output, diagnostics } = result;
  if (Array.isArray(output) && output.every((item) => typeof item === "string")) {
    els.output.textContent = output.join("\n") || "(no output)";
  } else {
    els.output.textContent = JSON.stringify(output, null, 2);
  }

  const genders = diagnostics && diagnostics.gender;
  els.diagnostics.textContent =
    genders && genders.length ? `detected: ${genders.join(", ")}` : "";
}

function showError(error) {
  els.output.textContent = String(error && error.message ? error.message : error);
  els.output.classList.add("has-error");
  els.diagnostics.textContent = "";
}

function runPlayground() {
  if (!demoRun) return;
  els.diagnostics.textContent = "";
  try {
    const payload = JSON.stringify({
      op: els.operation.value,
      text: els.input.value,
    });
    const response = demoRun(payload);
    renderOutput(JSON.parse(response));
  } catch (error) {
    showError(error);
  }
}

function buildScenarioCards() {
  SCENARIOS.forEach((scenario) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "scenario";
    button.dataset.scenario = scenario.id;
    button.setAttribute("aria-pressed", "false");

    const title = document.createElement("span");
    title.className = "scenario-title";
    title.textContent = scenario.title;

    const op = document.createElement("span");
    op.className = "scenario-op";
    op.textContent = `op: ${scenario.op}`;

    button.append(title, op);
    button.addEventListener("click", () => selectScenario(scenario.id));
    els.scenarios.appendChild(button);
  });
}

function selectScenario(id) {
  const scenario = SCENARIOS.find((item) => item.id === id);
  if (!scenario) return;

  activeScenario = id;
  els.input.value = scenario.text;
  els.operation.value = scenario.op;

  els.scenarios.querySelectorAll(".scenario").forEach((card) => {
    card.setAttribute("aria-pressed", String(card.dataset.scenario === id));
  });

  const url = new URL(window.location.href);
  url.searchParams.set("demo", id);
  history.replaceState(null, "", url);

  if (demoRun) {
    runPlayground();
  } else {
    els.output.textContent = "Waiting for the Python runtime to finish loading\u2026";
  }
}

function handleSubmit(event) {
  event.preventDefault();
  activeScenario = null;
  els.scenarios.querySelectorAll(".scenario").forEach((card) => {
    card.setAttribute("aria-pressed", "false");
  });
  runPlayground();
}

function init() {
  els.repoLink.href = `https://github.com/${CONFIG.repo}`;
  els.sourceRefLabel.textContent = CONFIG.sourceRef;
  buildScenarioCards();
  els.form.addEventListener("submit", handleSubmit);

  const requested = new URLSearchParams(window.location.search).get("demo");
  const initial = SCENARIOS.find((item) => item.id === requested) || SCENARIOS[0];
  els.input.value = initial.text;
  els.operation.value = initial.op;
  activeScenario = initial.id;
  els.scenarios.querySelector(`[data-scenario="${initial.id}"]`)
    ?.setAttribute("aria-pressed", "true");

  readProjectMetadata();

  initPyodide()
    .then(() => {
      if (activeScenario) selectScenario(activeScenario);
      else runPlayground();
    })
    .catch((error) => {
      setStatus("error", "Failed to initialize");
      showError(error);
    });
}

document.addEventListener("DOMContentLoaded", init);
