const READ_ONLY_MODES = new Set(["diagnose", "plan", "release", "review", "security"]);
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled", "canceled", "timed_out"]);
const runHistory = [];
let lastRunPayload = null;
let runPollTimer = null;
let gatewayAccessToken = "";
let gatewayTokenKind = "none";
let sessionExpiresAt = null;
let sessionCountdownTimer = null;
let lastMobileUrl = "";
const TASK_PRESETS = {
  plan: "Plan the next safe, high-impact step from the current project state.",
  review: "Review the current state and identify issues, risks, and quick wins.",
  diagnose: "Diagnose the current problem and suggest read-only verification steps.",
  security: "Perform a security-focused review of the current state and boundaries.",
  release: "Check release readiness and identify blockers before publication.",
};

function pretty(payload) {
  return JSON.stringify(payload, null, 2);
}

function byId(id) {
  return document.getElementById(id);
}

function show(targetId, payload) {
  const target = byId(targetId);
  if (!target) return;
  target.textContent = typeof payload === "string" ? payload : pretty(payload);
}

function setCallout(id, text, state = "warn") {
  const item = byId(id);
  if (!item) return;
  item.textContent = text;
  item.className = `callout ${state}`;
}

function setAuthBanner(text, state = "warn") {
  setCallout("auth-banner", text, state);
}

function isLoopbackHost() {
  const host = window.location.hostname;
  return host === "127.0.0.1" || host === "localhost" || host === "::1";
}

function showPairRequiredOutputs() {
  const message = "Pair this phone first, then refresh this panel.";
  for (const id of ["ops-output", "status-output", "model-output", "sessions-output", "runs-output"]) {
    show(id, message);
    const target = byId(id);
    if (target) target.classList.add("output-pair-required");
  }
}

function clearPairRequiredOutput(targetId) {
  const target = byId(targetId);
  if (target) target.classList.remove("output-pair-required");
}


function setMobileQr(svg) {
  const image = byId("mobile-access-qr");
  if (!svg) {
    image.removeAttribute("src");
    return;
  }
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function currentBrowserUrl() {
  if (isLoopbackHost()) return "";
  return `${window.location.protocol}//${window.location.host}/`;
}

function setMobileAccess(payload) {
  const browserUrl = currentBrowserUrl();
  lastMobileUrl = browserUrl || payload.recommended_url || "";
  byId("mobile-access-url").textContent = lastMobileUrl || "No mobile URL detected.";
  const label = browserUrl ? "mobile current browser URL" : (payload.recommended_kind ? `mobile ${payload.recommended_kind}` : "mobile URL unavailable");
  setPill("mobile-access-kind", label, lastMobileUrl ? "ready" : "danger");
  setMobileQr(payload.qr_svg || "");
  show("mobile-access-output", browserUrl ? { ...payload, active_phone_url: browserUrl } : payload);
}


function setModelStatus(payload) {
  const overall = payload.overall || "unknown";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  show("model-output", payload);
  setCheck("check-model", `Model ${overall}.`, state);
}

function setOpsStatus(payload) {
  const overall = payload.overall || "unknown";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  setPill("ops-pill", `ops ${overall}`, state);
  const doctor = payload.doctor && payload.doctor.overall ? payload.doctor.overall : "unknown";
  const mobileSession = payload.mobile_session && payload.mobile_session.overall === "ready" ? "session ready" : "";
  const mobile = mobileSession || (payload.mobile && payload.mobile.overall ? payload.mobile.overall : "unknown");
  const telegram = payload.telegram && payload.telegram.overall ? payload.telegram.overall : "unknown";
  setCheck("check-access", `Ops: doctor ${doctor}, mobile ${mobile}, telegram ${telegram}.`, state);
  clearPairRequiredOutput("ops-output");
  show("ops-output", payload);
}

async function copyMobileUrl() {
  const text = lastMobileUrl || byId("mobile-access-url").textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text || "");
    setPill("mobile-access-kind", "mobile URL copied", "ready");
  } else {
    show("mobile-access-output", `${text}\n\nClipboard API unavailable.`);
  }
}

function setCheck(id, text, state = "muted") {
  const item = byId(id);
  if (!item) return;
  item.textContent = text;
  item.className = `check ${state}`;
}

function updateTaskCounter() {
  const task = byId("run-task");
  const counter = byId("task-counter");
  if (!task || !counter) return;
  counter.textContent = `${task.value.length} / ${task.maxLength || 12000}`;
}

function applyPreset(mode) {
  if (!TASK_PRESETS[mode]) return;
  byId("run-mode").value = mode;
  byId("run-task").value = TASK_PRESETS[mode];
  updateTaskCounter();
}

function setPill(id, text, state = "muted") {
  const pill = byId(id);
  if (!pill) return;
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
    setCheck("check-access", "Pair token not loaded yet.", "muted");
    return;
  }
  if (ok) {
    const label = `${tokenKindLabel()} authenticated.`;
    byId("gateway-access-state").textContent = `${label} Token remains only in page memory.`;
    setCheck("check-access", `${tokenKindLabel()} authenticated in memory.`, "ready");
    return;
  }
  if (status === 401) {
    byId("gateway-access-state").textContent = "Loaded token is missing, invalid, or expired.";
    setCallout("gateway-auth-result", "Token was not accepted or the mobile session expired. Generate a fresh pair token and try again.", "danger");
    setAuthBanner("Pairing failed or mobile session expired. Generate a fresh pair token and try again.", "danger");
    setCheck("check-access", "Pair token missing, invalid, or expired.", "danger");
  } else if (status === 403) {
    byId("gateway-access-state").textContent = "Loaded token was rejected by the gateway.";
    setCallout("gateway-auth-result", "Token rejected by gateway.", "danger");
    setAuthBanner("Token rejected by gateway.", "danger");
    setCheck("check-access", "Loaded token rejected.", "danger");
  } else if (status === 429) {
    byId("gateway-access-state").textContent = "Too many failed token attempts. Wait before retrying.";
    setCallout("gateway-auth-result", "Too many failed token attempts. Wait before retrying.", "danger");
    setAuthBanner("Too many failed token attempts. Wait before retrying.", "danger");
    setCheck("check-access", "Token attempts rate limited.", "danger");
  }
}

function parseSessionExpiresAt(raw) {
  const value = (raw || "").trim();
  if (!value) return null;
  const instant = Date.parse(value);
  if (Number.isNaN(instant)) throw new Error("session expiration must be an ISO timestamp");
  return instant;
}

function tokenKindLabel() {
  if (gatewayTokenKind === "session") return "Mobile session";
  if (gatewayTokenKind === "pair") return "Pair token";
  if (gatewayTokenKind === "permanent") return "Gateway token";
  return "No token";
}

async function exchangeMobileSession(pairToken) {
  gatewayAccessToken = pairToken;
  gatewayTokenKind = "pair";
  const payload = await requestJson("/v1/gateway/mobile-session", { method: "POST" });
  if (payload && payload.session_token) {
    gatewayAccessToken = payload.session_token;
    gatewayTokenKind = "session";
    sessionExpiresAt = parseSessionExpiresAt(payload.expires_at || "");
    startSessionCountdown();
    return payload;
  }
  throw new Error("gateway did not return a mobile session token");
}

function renderSessionCountdown() {
  const target = byId("pairing-state");
  if (gatewayTokenKind !== "session" || sessionExpiresAt === null) {
    target.textContent = "No mobile session timer loaded.";
    target.className = "muted";
    return;
  }
  const remainingSeconds = Math.max(0, Math.floor((sessionExpiresAt - Date.now()) / 1000));
  if (remainingSeconds <= 0) {
    target.textContent = "Mobile session expired. Forget it and pair again with a fresh token.";
    target.className = "danger-text";
    return;
  }
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  target.textContent = `Mobile session: ${minutes}m ${String(seconds).padStart(2, "0")}s remaining.`;
  target.className = remainingSeconds < 60 ? "warn-text" : "muted";
}

function startSessionCountdown() {
  stopSessionCountdown();
  renderSessionCountdown();
  if (gatewayTokenKind === "session" && sessionExpiresAt !== null) {
    sessionCountdownTimer = window.setInterval(renderSessionCountdown, 1000);
  }
}

function stopSessionCountdown() {
  if (sessionCountdownTimer !== null) {
    window.clearInterval(sessionCountdownTimer);
    sessionCountdownTimer = null;
  }
}

function setSessionFromPayload(payload) {
  const session = payload.session || (payload.sessions && payload.sessions[0]);
  if (session && session.session_id) {
    byId("session-id").value = session.session_id;
    setPill("active-session-pill", `session ${session.session_id}`, "ready");
    setCheck("check-session", `Session selected: ${session.session_id}`, "ready");
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
    setCheck("check-run", summarizeRun(run), state);
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

function clearSession() {
  byId("session-id").value = "";
  setPill("active-session-pill", "no active session", "muted");
  setCheck("check-session", "No active session selected.", "muted");
}

async function revokeMobileSessionIfLoaded() {
  if (gatewayTokenKind !== "session" || !gatewayAccessToken) return;
  try {
    await requestJson("/v1/gateway/mobile-session", { method: "DELETE" });
  } catch (_err) {
    // Forgetting the page token must still work even if the server session already expired.
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
      const selectedTokenKind = byId("gateway-token-kind").value === "permanent" ? "permanent" : "pair";
      gatewayTokenKind = selectedTokenKind;
      sessionExpiresAt = null;
      byId("gateway-token").value = "";
      if (!gatewayAccessToken) {
        byId("gateway-access-state").textContent = "No gateway token loaded in page memory.";
        setCallout("gateway-auth-result", "Paste a pair token before pairing this phone.", "danger");
        setAuthBanner("Paste a pair token before using private controls.", "warn");
        setCheck("check-access", "Pair token not loaded yet.", "muted");
        return;
      }
      byId("gateway-access-state").textContent = `${selectedTokenKind === "pair" ? "Pair" : "Gateway"} token loaded in page memory. Validating now...`;
      setCallout("gateway-auth-result", "Validating token with the gateway...", "warn");
      setAuthBanner("Validating phone pairing...", "warn");
      setCheck("check-access", `${selectedTokenKind === "pair" ? "Pair" : "Gateway"} token validating.`, "running");
      let sessionPayload = null;
      if (selectedTokenKind === "pair") {
        sessionPayload = await exchangeMobileSession(gatewayAccessToken);
        setCallout("gateway-auth-result", "Paired successfully. Mobile session unlocked for this page.", "ready");
        setAuthBanner("Phone paired. Temporary mobile session is active in this page only.", "ready");
      } else {
        startSessionCountdown();
        setCallout("gateway-auth-result", "Gateway token accepted. Private controls are unlocked for this page.", "ready");
        setAuthBanner("Gateway token accepted. Private controls are unlocked in this page only.", "ready");
      }
      const payload = await requestJson("/v1/gateway/ops-status");
      setOpsStatus(payload);
      if (sessionPayload && sessionPayload.expires_at) {
        setCallout("gateway-auth-result", `Paired successfully. Mobile session expires at ${sessionPayload.expires_at}.`, "ready");
      }
      await runAction("refresh-readiness");
    } else if (action === "forget-gateway-token") {
      await revokeMobileSessionIfLoaded();
      gatewayAccessToken = "";
      gatewayTokenKind = "none";
      sessionExpiresAt = null;
      stopSessionCountdown();
      byId("gateway-token").value = "";
      byId("pair-expires-at").value = "";
      byId("gateway-access-state").textContent = "No gateway token loaded in page memory.";
      setCallout("gateway-auth-result", "Token forgotten. Paste a new pair token to unlock this phone.", "warn");
      setAuthBanner("Phone is not paired. Private controls are locked.", "warn");
      setCheck("check-access", "Pair token not loaded yet.", "muted");
      renderSessionCountdown();
      if (!isLoopbackHost()) showPairRequiredOutputs();
    } else if (action === "refresh-token-countdown") {
      startSessionCountdown();
    } else if (action === "refresh-mobile-access") {
      setMobileAccess(await requestJson("/v1/gateway/mobile-access"));
    } else if (action === "copy-mobile-url") {
      await copyMobileUrl();
    } else if (action === "refresh-ops-status") {
      clearPairRequiredOutput("ops-output");
      setOpsStatus(await requestJson("/v1/gateway/ops-status"));
    } else if (action === "refresh-model-status") {
      setModelStatus(await requestJson("/v1/gateway/model-status"));
    } else if (action === "refresh-model-plan") {
      const payload = await requestJson("/v1/gateway/model-plan");
      setPill("model-pill", `model plan ${payload.overall || "unknown"}`, payload.overall === "ready_to_prepare" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-model-files") {
      const payload = await requestJson("/v1/gateway/model-files?max_results=10");
      setPill("model-pill", `model files ${payload.models_found || 0}`, payload.recommended ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "run-model-task") {
      const payload = await requestJson("/v1/gateway/model-task?task=code-mini&timeout_seconds=60");
      setPill("model-pill", `model task ${payload.overall || "unknown"}`, payload.overall === "ready" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "run-model-eval") {
      const payload = await requestJson("/v1/gateway/model-eval?timeout_seconds=60");
      setPill("model-pill", `model eval ${payload.overall || "unknown"}`, payload.overall === "ready" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-model-runs") {
      const payload = await requestJson("/v1/gateway/model-runs?limit=20");
      setPill("model-pill", `model runs ${payload.count || 0}`, payload.count ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-status") {
      clearPairRequiredOutput("status-output");
      show("status-output", await requestJson("/v1/harness/status"));
    } else if (action === "refresh-readiness") {
      clearPairRequiredOutput("status-output");
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
    } else if (action === "clear-session") {
      clearSession();
      show("sessions-output", "Session selection cleared. Existing harness sessions were not changed.");
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
    } else if (action === "stop-polling") {
      stopRunPolling();
      setPill("active-run-pill", "polling stopped", "muted");
    } else if (action === "copy-run-output") {
      await copyRunOutput();
    }
  } catch (err) {
    stopRunPolling();
    if (action === "use-gateway-token") {
      gatewayAccessToken = "";
      gatewayTokenKind = "none";
      sessionExpiresAt = null;
      stopSessionCountdown();
      renderSessionCountdown();
    }
    const target = action.includes("session")
      ? "sessions-output"
      : action.includes("run") || action === "copy-run-output"
        ? "runs-output"
        : action.includes("ops")
          ? "ops-output"
        : action.includes("model")
          ? "model-output"
          : "status-output";
    show(target, String(err.message || err));
  }
}

document.addEventListener("click", (event) => {
  const actionButton = event.target.closest("button[data-action]");
  if (actionButton) {
    runAction(actionButton.dataset.action);
    return;
  }
  const presetButton = event.target.closest("button[data-preset]");
  if (presetButton) applyPreset(presetButton.dataset.preset);
});

document.addEventListener("DOMContentLoaded", () => {
  updateTaskCounter();
  const taskBox = byId("run-task");
  if (taskBox) taskBox.addEventListener("input", updateTaskCounter);
  const tokenBox = byId("gateway-token");
  if (tokenBox) {
    tokenBox.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runAction("use-gateway-token");
    });
  }
  runAction("refresh-mobile-access");
  if (isLoopbackHost()) {
    setAuthBanner("Loopback access does not need phone pairing.", "ready");
    runAction("refresh-model-status");
    runAction("refresh-readiness");
    runAction("refresh-ops-status");
  } else {
    setAuthBanner("Paste a fresh pair token to unlock private controls on this phone.", "warn");
    showPairRequiredOutputs();
  }
});
