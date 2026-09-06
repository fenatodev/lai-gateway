const READ_ONLY_MODES = new Set(["diagnose", "plan", "release", "review", "security"]);
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled", "canceled", "timed_out"]);
const runHistory = [];
let lastRunPayload = null;
let runPollTimer = null;
let gatewayAccessToken = "";
let gatewayTokenKind = "none";
let pairExpiresAt = null;
let pairCountdownTimer = null;

function pretty(payload) {
  return JSON.stringify(payload, null, 2);
}

function byId(id) {
  return document.getElementById(id);
}

function show(targetId, payload) {
  byId(targetId).textContent = typeof payload === "string" ? payload : pretty(payload);
}

function setPill(id, text, state = "muted") {
  const pill = byId(id);
  pill.textContent = text;
  pill.className = `pill ${state}`;
}

function gatewayAuthHeaders() {
  if (!gatewayAccessToken) return {};
  return { "Authorization": `${"Bear"}er ${gatewayAccessToken}` };
}

async function requestJson(path, options = {}) {
  const headers = { "Accept": "application/json", ...gatewayAuthHeaders(), ...(options.headers || {}) };
  const response = await fetch(path, {
    cache: "no-store",
    headers,
    ...options,
  });
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (_err) {
    payload = { error: "invalid_json", body: text };
  }
  updateGatewayAuthState(response.status, response.ok);
  if (!response.ok) {
    throw new Error(pretty({ status: response.status, payload }));
  }
  return payload;
}

function updateGatewayAuthState(status, ok) {
  if (!gatewayAccessToken) {
    byId("gateway-access-state").textContent = "No gateway token loaded in page memory.";
    return;
  }
  if (ok) {
    const label = gatewayTokenKind === "pair" ? "Pair token authenticated." : "Gateway token authenticated.";
    byId("gateway-access-state").textContent = `${label} Token remains only in page memory.`;
    return;
  }
  if (status === 401) {
    byId("gateway-access-state").textContent = "Private API requires a gateway or pair token.";
  } else if (status === 403) {
    byId("gateway-access-state").textContent = "Loaded token was rejected by the gateway.";
  } else if (status === 429) {
    byId("gateway-access-state").textContent = "Too many failed token attempts. Wait before retrying.";
  }
}

function parsePairExpiresAt(raw) {
  const value = raw.trim();
  if (!value) return null;
  const instant = Date.parse(value);
  if (Number.isNaN(instant)) throw new Error("pair token expiration must be an ISO timestamp");
  return instant;
}

function renderPairCountdown() {
  const target = byId("pairing-state");
  if (gatewayTokenKind !== "pair" || pairExpiresAt === null) {
    target.textContent = "No pairing token timer loaded.";
    target.className = "muted";
    return;
  }
  const remainingSeconds = Math.max(0, Math.floor((pairExpiresAt - Date.now()) / 1000));
  if (remainingSeconds <= 0) {
    target.textContent = "Pair token timer expired. Forget it and create a new pair token.";
    target.className = "danger-text";
    return;
  }
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  target.textContent = `Pair token timer: ${minutes}m ${String(seconds).padStart(2, "0")}s remaining.`;
  target.className = remainingSeconds < 60 ? "warn-text" : "muted";
}

function startPairCountdown() {
  stopPairCountdown();
  renderPairCountdown();
  if (gatewayTokenKind === "pair" && pairExpiresAt !== null) {
    pairCountdownTimer = window.setInterval(renderPairCountdown, 1000);
  }
}

function stopPairCountdown() {
  if (pairCountdownTimer !== null) {
    window.clearInterval(pairCountdownTimer);
    pairCountdownTimer = null;
  }
}

function setSessionFromPayload(payload) {
  const session = payload.session || (payload.sessions && payload.sessions[0]);
  if (session && session.session_id) {
    byId("session-id").value = session.session_id;
    setPill("active-session-pill", `session ${session.session_id}`, "ready");
  }
}

function summarizeRun(run) {
  const id = run.control_run_id || "unknown";
  const status = run.status || "unknown";
  const mode = run.mode || "unknown";
  return `${id} · ${mode} · ${status}`;
}

function recordRun(run) {
  if (!run || !run.control_run_id) return;
  const existing = runHistory.findIndex((item) => item.control_run_id === run.control_run_id);
  if (existing >= 0) runHistory.splice(existing, 1);
  runHistory.unshift({
    control_run_id: run.control_run_id,
    mode: run.mode || "unknown",
    status: run.status || "unknown",
    finished_at: run.finished_at || "",
  });
  runHistory.splice(8);
  renderRunHistory();
}

function renderRunHistory() {
  const list = byId("run-history");
  list.replaceChildren();
  for (const item of runHistory) {
    const li = document.createElement("li");
    li.textContent = `${item.control_run_id} · ${item.mode} · ${item.status}${item.finished_at ? ` · ${item.finished_at}` : ""}`;
    li.addEventListener("click", () => {
      byId("run-id").value = item.control_run_id;
      runAction("get-run");
    });
    list.appendChild(li);
  }
}

function setRunFromPayload(payload) {
  const run = payload.run || (payload.runs && payload.runs[0]);
  if (run && run.control_run_id) {
    byId("run-id").value = run.control_run_id;
    lastRunPayload = payload;
    const state = TERMINAL_STATUSES.has(run.status) ? (run.status === "succeeded" ? "ready" : "danger") : "running";
    setPill("active-run-pill", summarizeRun(run), state);
    recordRun(run);
  }
}

async function pollSelectedRun() {
  const runId = byId("run-id").value.trim();
  if (!runId) throw new Error("run id is required");
  const payload = await requestJson(`/v1/harness/runs/${encodeURIComponent(runId)}`);
  setRunFromPayload(payload);
  show("runs-output", payload);
  const status = payload.run && payload.run.status;
  if (TERMINAL_STATUSES.has(status)) stopRunPolling();
  return payload;
}

function startRunPolling() {
  stopRunPolling();
  setPill("active-run-pill", "polling selected run", "running");
  runPollTimer = window.setInterval(() => {
    pollSelectedRun().catch((err) => {
      stopRunPolling();
      show("runs-output", String(err.message || err));
    });
  }, 1200);
}

function stopRunPolling() {
  if (runPollTimer !== null) {
    window.clearInterval(runPollTimer);
    runPollTimer = null;
  }
}

async function copyRunOutput() {
  const run = lastRunPayload && lastRunPayload.run;
  const text = run && typeof run.stdout === "string" ? run.stdout : byId("runs-output").textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text || "");
    setPill("active-run-pill", "output copied", "ready");
  } else {
    show("runs-output", `${text}\n\nClipboard API unavailable.`);
  }
}

async function runAction(action) {
  try {
    if (action === "use-gateway-token") {
      gatewayAccessToken = byId("gateway-token").value.trim();
      gatewayTokenKind = byId("gateway-token-kind").value === "permanent" ? "permanent" : "pair";
      pairExpiresAt = gatewayTokenKind === "pair" ? parsePairExpiresAt(byId("pair-expires-at").value) : null;
      byId("gateway-token").value = "";
      byId("gateway-access-state").textContent = gatewayAccessToken ? `${gatewayTokenKind === "pair" ? "Pair" : "Gateway"} token loaded in page memory.` : "No gateway token loaded in page memory.";
      startPairCountdown();
    } else if (action === "forget-gateway-token") {
      gatewayAccessToken = "";
      gatewayTokenKind = "none";
      pairExpiresAt = null;
      stopPairCountdown();
      byId("gateway-token").value = "";
      byId("pair-expires-at").value = "";
      byId("gateway-access-state").textContent = "No gateway token loaded in page memory.";
      renderPairCountdown();
    } else if (action === "refresh-token-countdown") {
      pairExpiresAt = parsePairExpiresAt(byId("pair-expires-at").value);
      if (pairExpiresAt !== null) gatewayTokenKind = "pair";
      startPairCountdown();
    } else if (action === "refresh-status") {
      show("status-output", await requestJson("/v1/harness/status"));
    } else if (action === "refresh-readiness") {
      const payload = await requestJson("/v1/harness/readiness");
      const overall = payload.overall || "unknown";
      setPill("readiness-pill", `readiness ${overall}`, overall === "ready" ? "ready" : "danger");
      show("status-output", payload);
    } else if (action === "list-sessions") {
      const payload = await requestJson("/v1/harness/sessions?limit=10");
      setSessionFromPayload(payload);
      show("sessions-output", payload);
    } else if (action === "create-session") {
      const payload = await requestJson("/v1/harness/sessions", { method: "POST" });
      setSessionFromPayload(payload);
      show("sessions-output", payload);
    } else if (action === "get-session") {
      const sessionId = byId("session-id").value.trim();
      if (!sessionId) throw new Error("session id is required");
      const payload = await requestJson(`/v1/harness/sessions/${encodeURIComponent(sessionId)}`);
      setSessionFromPayload(payload);
      show("sessions-output", payload);
    } else if (action === "list-runs") {
      const payload = await requestJson("/v1/harness/runs?limit=10");
      setRunFromPayload(payload);
      show("runs-output", payload);
    } else if (action === "create-run") {
      const mode = byId("run-mode").value;
      const task = byId("run-task").value.trim();
      const sessionId = byId("session-id").value.trim();
      if (!READ_ONLY_MODES.has(mode)) throw new Error("mode must be read-only");
      if (!task) throw new Error("task is required");
      const body = { mode, task };
      if (sessionId) body.session_id = sessionId;
      const payload = await requestJson("/v1/harness/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(body),
      });
      setRunFromPayload(payload);
      show("runs-output", payload);
      startRunPolling();
    } else if (action === "get-run") {
      await pollSelectedRun();
    } else if (action === "poll-run") {
      await pollSelectedRun();
      startRunPolling();
    } else if (action === "copy-run-output") {
      await copyRunOutput();
    }
  } catch (err) {
    stopRunPolling();
    const target = action.includes("session") ? "sessions-output" : action.includes("run") || action.includes("copy") ? "runs-output" : "status-output";
    show(target, String(err.message || err));
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  runAction(button.dataset.action);
});

document.addEventListener("DOMContentLoaded", () => {
  runAction("refresh-readiness");
});
