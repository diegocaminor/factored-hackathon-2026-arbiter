// Demo UI: consumes only the public HTTP API (same origin). No ML code, no artifacts.

const PRESETS = [
  { id: "CLI-P21780PQ8D9W", label: "ACTION" },
  { id: "CLI-S5RL0QD6GG1U", label: "ACTION" },
  { id: "CLI-P8F6JG7TN8YN", label: "NO CONSENT" },
  { id: "CLI-QHXK2HCRNFBI", label: "NO CONSENT" },
];

// The only API endpoints this page may call.
const endpoints = {
  recommendation: (id) => `/customers/${encodeURIComponent(id)}/next-best-action?include_candidates=true`,
  confirm: (id) => `/customers/${encodeURIComponent(id)}/confirm`,
  handoff: (id) => `/customers/${encodeURIComponent(id)}/handoff`,
  agentRun: () => `/agent/run`,
};

// Workflow path per /agent/run status; node names mirror the vendored LangGraph graph.
const AGENT_PATHS = {
  COMPLETED: ["load_customer", "recommend", "prepare_offer", "execute_offer"],
  HANDOFF: ["load_customer", "recommend", "prepare_offer", "handoff"],
  NO_ACTION: ["load_customer", "recommend", "no_action"],
};

const $ = (id) => document.getElementById(id);
const state = { customerId: null, decision: null, country: null };

// ---------- API client ----------

async function api(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { kind: "network" };
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (response.ok) return { kind: "ok", data: payload };
  return { kind: "http", status: response.status, detail: describeDetail(payload) };
}

function describeDetail(payload) {
  const detail = payload && payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  return "Unexpected response from the API.";
}

function showError(result) {
  const banner = $("error-banner");
  const titles = { 404: "Not found", 409: "Not allowed", 422: "Invalid request" };
  if (result.kind === "network") {
    banner.textContent = "Connection error: the API could not be reached. Is the server running?";
  } else {
    const title = titles[result.status] || `Error ${result.status}`;
    banner.textContent = `${title}: ${result.detail}`;
  }
  banner.hidden = false;
}

function clearError() {
  $("error-banner").hidden = true;
}

async function withBusy(button, task) {
  button.disabled = true;
  button.classList.add("loading");
  try {
    await task();
  } finally {
    button.classList.remove("loading");
    syncControls();
  }
}

// ---------- formatting ----------

const DASH = "—";
const isMissing = (v) => v === null || v === undefined;
const fmtPropensity = (v) => (isMissing(v) ? DASH : v.toFixed(4));
const fmtInt = (v) => (isMissing(v) ? DASH : v.toLocaleString("en-US"));
const fmtText = (v) => (isMissing(v) || v === "" ? DASH : v);

function fmtMoney(v, country) {
  if (isMissing(v)) return DASH;
  const amount = v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return country ? `${amount} (${country})` : amount;
}

function setBadge(element, text, tone) {
  element.textContent = text;
  element.className = `badge badge-${tone}`;
}

function decisionTone(decision) {
  if (decision === "ACTION" || decision === "COMPLETED") return "success";
  if (decision === "HANDOFF") return "info";
  return "warning";
}

function renderFields(container, fields) {
  const list = document.createElement("dl");
  for (const [label, value] of fields) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = fmtText(value);
    list.append(dt, dd);
  }
  container.replaceChildren(list);
  container.classList.remove("muted");
}

// ---------- rendering ----------

function renderRecommendation(rec) {
  setBadge($("decision-badge"), rec.decision, decisionTone(rec.decision));
  $("m-customer").textContent = rec.customer_id;
  $("m-country").textContent = fmtText(rec.country);
  $("m-product").textContent = fmtText(rec.product);
  $("m-channel").textContent = fmtText(rec.channel);
  $("m-propensity").textContent = fmtPropensity(rec.propensity);
  $("m-expected-value").textContent = fmtMoney(rec.expected_value, rec.country);
  $("m-support").textContent = fmtInt(rec.historical_support);
  renderCandidates(rec.candidates || [], rec.country);
}

function renderCandidates(candidates, country) {
  const body = $("candidates-body");
  if (candidates.length === 0) {
    body.innerHTML = '<tr class="empty"><td colspan="6">No scored actions for this decision.</td></tr>';
    return;
  }
  body.replaceChildren(
    ...candidates.map((c) => {
      const row = document.createElement("tr");
      if (c.rank === 1) row.className = "top";
      const cells = [
        [c.rank, ""],
        [fmtText(c.product), ""],
        [fmtText(c.channel), ""],
        [fmtPropensity(c.propensity), "num"],
        [fmtMoney(c.expected_value, country), "num"],
        [fmtInt(c.historical_support), "num"],
      ];
      for (const [value, cls] of cells) {
        const td = document.createElement("td");
        td.textContent = value;
        if (cls) td.className = cls;
        row.append(td);
      }
      return row;
    }),
  );
}

function renderExecution(result) {
  const fields =
    result.status === "SIMULATED_SENT"
      ? [
          ["Status", result.status],
          ["Customer", result.customer_id],
          ["Product", result.product],
          ["Channel", result.channel],
          ["Provider message ID", result.provider_message_id],
        ]
      : [
          ["Status", result.status],
          ["Customer", result.customer_id],
          ["Reason", result.reason],
          ["Queue", result.queue],
        ];
  renderFields($("execution-result"), fields);
}

function highlightPath(status) {
  const path = AGENT_PATHS[status] || (status.startsWith("NO_ACTION") ? AGENT_PATHS.NO_ACTION : []);
  for (const node of document.querySelectorAll("#agent-path li")) {
    node.classList.toggle("active", path.includes(node.dataset.node));
  }
}

function renderAgent(run) {
  setBadge($("agent-status"), run.status, decisionTone(run.status));
  highlightPath(run.status);
  $("agent-message").textContent = run.assistant_message;
  $("agent-message").classList.remove("muted");
  const result = run.execution_result;
  if (result) {
    renderExecution(result);
    renderFields($("agent-result"), [
      ["Decision", run.recommendation.decision],
      ["Execution", result.status],
      ["Detail", result.provider_message_id || result.queue],
    ]);
  } else {
    renderFields($("agent-result"), [
      ["Decision", run.recommendation.decision],
      ["Execution", "None (workflow ended without execution)"],
    ]);
  }
}

function resetPanels() {
  $("execution-result").textContent = "No action executed yet.";
  $("execution-result").classList.add("muted");
  setBadge($("agent-status"), "Not run", "muted");
  highlightPath("");
  $("agent-message").textContent = "Path is derived from the status returned by POST /agent/run.";
  $("agent-message").classList.add("muted");
  $("agent-result").replaceChildren();
}

function syncControls() {
  const loaded = state.customerId !== null;
  const actionable = state.decision === "ACTION";
  $("load-button").disabled = false;
  $("confirm-button").disabled = !actionable;
  $("handoff-button").disabled = !loaded;
  $("agent-button").disabled = !loaded;
  $("confirm-hint").textContent = !loaded
    ? "Load a customer first."
    : actionable
      ? "Simulates sending the recommended offer."
      : "Only ACTION recommendations can be confirmed.";
}

// ---------- actions ----------

async function loadCustomer(customerId) {
  const id = customerId.trim();
  if (!id) return;
  clearError();
  await withBusy($("load-button"), async () => {
    const result = await api("GET", endpoints.recommendation(id));
    if (result.kind !== "ok") {
      showError(result);
      return;
    }
    Object.assign(state, {
      customerId: id,
      decision: result.data.decision,
      country: result.data.country,
    });
    renderRecommendation(result.data);
    resetPanels();
  });
}

async function confirmOffer() {
  clearError();
  await withBusy($("confirm-button"), async () => {
    const result = await api("POST", endpoints.confirm(state.customerId));
    if (result.kind === "ok") renderExecution(result.data);
    else showError(result);
  });
}

async function handOff() {
  clearError();
  const reason = $("handoff-reason").value.trim();
  await withBusy($("handoff-button"), async () => {
    const result = await api("POST", endpoints.handoff(state.customerId), reason ? { reason } : undefined);
    if (result.kind === "ok") renderExecution(result.data);
    else showError(result);
  });
}

async function runAgent() {
  clearError();
  await withBusy($("agent-button"), async () => {
    const result = await api("POST", endpoints.agentRun(), {
      customer_id: state.customerId,
      user_confirmed: $("user-confirmed").checked,
    });
    if (result.kind === "ok") renderAgent(result.data);
    else showError(result);
  });
}

// ---------- wiring ----------

function renderPresets() {
  $("presets").replaceChildren(
    ...PRESETS.map((preset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "preset";
      const code = document.createElement("code");
      code.textContent = preset.id;
      const badge = document.createElement("span");
      badge.className = `badge badge-${preset.label === "ACTION" ? "success" : "warning"}`;
      badge.textContent = preset.label;
      button.append(code, badge);
      button.addEventListener("click", () => {
        $("customer-id").value = preset.id;
        loadCustomer(preset.id);
      });
      return button;
    }),
  );
}

$("customer-form").addEventListener("submit", (event) => {
  event.preventDefault();
  loadCustomer($("customer-id").value);
});
$("confirm-button").addEventListener("click", confirmOffer);
$("handoff-button").addEventListener("click", handOff);
$("agent-button").addEventListener("click", runAgent);

renderPresets();
syncControls();
