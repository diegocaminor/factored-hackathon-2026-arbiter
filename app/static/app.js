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
  chat: () => `/agent/chat`,
};

// /agent/chat is stateless and accepts at most this many messages per request.
const CHAT_WINDOW = 20;

// Workflow path per /agent/run status; node names mirror the vendored LangGraph graph.
const AGENT_PATHS = {
  COMPLETED: ["load_customer", "recommend", "prepare_offer", "execute_offer"],
  HANDOFF: ["load_customer", "recommend", "prepare_offer", "handoff"],
  NO_ACTION: ["load_customer", "recommend", "no_action"],
};

const $ = (id) => document.getElementById(id);
const state = {
  customerId: null,
  decision: null,
  country: null,
  chat: { messages: [], pending: false },
};

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
  const titles = {
    404: "Not found",
    409: "Not allowed",
    422: "Invalid request",
    502: "Chat agent error",
    503: "Unavailable",
  };
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
  const chatReady = loaded && !state.chat.pending;
  $("chat-input").disabled = !chatReady;
  $("chat-send").disabled = !chatReady;
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
    const customerChanged = id !== state.customerId;
    Object.assign(state, {
      customerId: id,
      decision: result.data.decision,
      country: result.data.country,
    });
    renderRecommendation(result.data);
    resetPanels();
    // A conversation belongs to one customer; reloading the same customer keeps it.
    if (customerChanged) resetChat();
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

// ---------- customer agent ----------

function resetChat() {
  state.chat.messages = [];
  $("chat-debug").textContent = "No turn yet.";
  $("chat-debug").classList.add("muted");
  renderChat();
}

// Text-only rendering: replies and customer messages are never parsed as HTML.
function renderChat() {
  const transcript = $("chat-transcript");
  const { messages } = state.chat;
  setBadge(
    $("chat-customer"),
    state.customerId ?? "No customer loaded",
    state.customerId ? "info" : "muted",
  );
  if (messages.length === 0) {
    const empty = document.createElement("p");
    empty.className = "chat-empty muted";
    empty.textContent = state.customerId
      ? "Send a message to start the conversation."
      : "Load a customer above to start a conversation.";
    transcript.replaceChildren(empty);
    return;
  }
  transcript.replaceChildren(
    ...messages.map(({ role, content }) => {
      const bubble = document.createElement("div");
      bubble.className = `bubble bubble-${role}`;
      bubble.textContent = content;
      return bubble;
    }),
  );
  transcript.scrollTop = transcript.scrollHeight;
}

function renderChatDebug(turn) {
  const result = turn.execution_result;
  renderFields($("chat-debug"), [
    ["Intent", turn.intent],
    ["Action taken", turn.action_taken],
    ["Execution", result ? result.status : null],
    ["Detail", result ? result.provider_message_id || result.queue : null],
  ]);
}

function setChatPending(pending) {
  state.chat.pending = pending;
  $("chat-typing").hidden = !pending;
  syncControls();
}

// The backend decides everything; this only sends the message and shows the reply.
async function sendChat(event) {
  event.preventDefault();
  const input = $("chat-input");
  const content = input.value.trim();
  if (!content || state.customerId === null || state.chat.pending) return;

  clearError();
  const customerId = state.customerId;
  state.chat.messages.push({ role: "user", content });
  input.value = "";
  renderChat();
  setChatPending(true);
  try {
    const result = await api("POST", endpoints.chat(), {
      customer_id: customerId,
      messages: state.chat.messages.slice(-CHAT_WINDOW),
    });
    // Ignore a late reply if the customer changed while it was pending.
    if (customerId !== state.customerId) return;
    if (result.kind === "ok") {
      state.chat.messages.push({ role: "assistant", content: result.data.reply });
      renderChatDebug(result.data);
    } else {
      // Never keep a customer message the backend did not answer.
      state.chat.messages.pop();
      input.value = content;
      showError(result);
    }
    renderChat();
  } finally {
    setChatPending(false);
  }
}

// ---------- tabs ----------

// Switching only toggles visibility; no tab reloads data or clears its content.
function selectTab(selected) {
  for (const tab of document.querySelectorAll('[role="tab"]')) {
    const active = tab === selected;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    $(tab.getAttribute("aria-controls")).hidden = !active;
  }
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
for (const tab of document.querySelectorAll('[role="tab"]')) {
  tab.addEventListener("click", () => selectTab(tab));
}
$("chat-form").addEventListener("submit", sendChat);

renderPresets();
renderChat();
syncControls();
