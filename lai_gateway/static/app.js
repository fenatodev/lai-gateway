const READ_ONLY_MODES = new Set(["diagnose", "plan", "release", "review", "security"]);
const LOCAL_CHAT_MODES = new Set(["ci-fix", "diagnose", "fix", "implement", "plan", "refactor", "release", "review", "security"]);
const LOCAL_CHAT_WORK_MODES = new Set(["ci-fix", "fix", "implement", "refactor"]);
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled", "canceled", "timed_out"]);
const runHistory = [];
let lastRunPayload = null;
let lastRunEventsPayload = null;
let runPollTimer = null;
let gatewayAccessToken = "";
let gatewayTokenKind = "none";
let sessionExpiresAt = null;
let sessionCountdownTimer = null;
let lastMobileUrl = "";
let localChatPollTimer = null;
let lastLocalChatCursor = 0;
let activeLocalRunId = "";
let activeLocalRunTerminal = true;
let lastLocalMode = "diagnose";
let currentLocalReview = null;
const localChatRenderedRuns = new Set();
const TASK_PRESETS = {
  plan: "Plan the next safe, high-impact step from the current project state.",
  review: "Review the current state and identify issues, risks, and quick wins.",
  diagnose: "Diagnose the current problem and suggest read-only verification steps.",
  security: "Perform a security-focused review of the current state and boundaries.",
  release: "Check release readiness and identify blockers before publication.",
};
const LOCAL_MODE_PRESETS = {
  observe: {
    mode: "diagnose",
    task: "Diagnose the current repository state using read-only evidence. Identify blockers, missing setup, and the next safe verification step.",
  },
  work: {
    mode: "implement",
    task: "Implement one bounded change in the isolated sandbox workspace. Keep the source checkout unchanged, validate the result, and leave promotion for review.",
  },
  promote: {
    mode: "review",
    task: "Review the selected isolated work-run diff. Verify the patch hash and list promotion risks before using the Promote reviewed patch button.",
  },
};

function pretty(payload) {
  return JSON.stringify(payload, null, 2);
}

function byId(id) {
  return document.getElementById(id);
}

function setText(id, text) {
  const item = byId(id);
  if (!item) return;
  item.textContent = text;
}

function setButtonState(id, disabled, text = "") {
  const button = byId(id);
  if (!button) return;
  button.disabled = disabled;
  if (text) button.textContent = text;
}

function updateLocalExecutionControls(status = "idle") {
  const running = !TERMINAL_STATUSES.has(status) && status !== "idle" && Boolean(activeLocalRunId);
  setButtonState("local-send-button", running, running ? "Run active" : "Send to LAI");
  setButtonState("local-cancel-button", !running, running ? "Cancel active run" : "No active run");
}

function clearLocalReviewState(reason = "") {
  byId("local-run-id").value = "";
  byId("local-patch-sha").value = "";
  activeLocalRunId = "";
  activeLocalRunTerminal = true;
  lastLocalChatCursor = 0;
  resetLocalReviewPanel(reason || "No review loaded.");
  updateLocalExecutionControls("idle");
  if (reason) setLocalNextStep(reason, "warn");
}


function appendLocalChatTurn(kind, title, text) {
  const thread = byId("local-chat-thread");
  if (!thread) return;
  const anchor = byId("local-chat-live-anchor");
  const row = document.createElement("div");
  row.className = kind === "user" ? "message-row user-row" : "message-row assistant-row";
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = kind === "user" ? "U" : "L";
  const bubble = document.createElement("article");
  bubble.className = kind === "user" ? "message-bubble user-bubble" : "message-bubble assistant-bubble";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const strong = document.createElement("strong");
  strong.textContent = title;
  meta.appendChild(strong);
  const body = document.createElement("p");
  body.textContent = text;
  bubble.appendChild(meta);
  bubble.appendChild(body);
  if (kind === "user") {
    row.appendChild(document.createElement("span"));
    row.appendChild(bubble);
  } else {
    row.appendChild(avatar);
    row.appendChild(bubble);
  }
  thread.insertBefore(row, anchor || null);
  row.scrollIntoView({ block: "nearest" });
}

function appendLocalToolMessage(title, text, state = "running") {
  const thread = byId("local-chat-thread");
  if (!thread) return;
  const anchor = byId("local-chat-live-anchor");
  const card = document.createElement("article");
  card.className = "tool-card transient-tool-card";
  const header = document.createElement("div");
  header.className = "tool-card-header";
  const icon = document.createElement("span");
  icon.className = "tool-icon";
  icon.textContent = "⚙";
  const copy = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = title;
  const p = document.createElement("p");
  p.textContent = text;
  copy.appendChild(strong);
  copy.appendChild(p);
  const pill = document.createElement("span");
  pill.className = `pill ${state}`;
  pill.textContent = state;
  header.appendChild(icon);
  header.appendChild(copy);
  header.appendChild(pill);
  card.appendChild(header);
  thread.insertBefore(card, anchor || null);
  card.scrollIntoView({ block: "nearest" });
}

function updateLocalRunCard(title, summary, status, state = "muted") {
  setText("local-run-card-title", title);
  setText("local-run-card-summary", summary);
  const pill = byId("local-run-card-status");
  if (pill) {
    pill.textContent = status;
    pill.className = `pill ${state}`;
  }
  setText("local-conversation-mode", byId("local-mode-label")?.textContent || "Observe");
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
  for (const id of ["health-output", "ops-output", "status-output", "model-output", "mcp-output", "sessions-output", "runs-output", "run-events-output"]) {
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

function setMcpStatus(payload) {
  const overall = payload.overall || payload.mcp_overall || "unknown";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  const serverCount = Number.isInteger(payload.server_count) ? payload.server_count : 0;
  const executionEnabled = Boolean(
    payload.execution_enabled || (payload.security && payload.security.executes_tools)
  );
  setPill("mcp-pill", `mcp ${overall}${serverCount ? ` · ${serverCount}` : ""}`, executionEnabled ? "danger" : state);
  setCheck(
    "check-mcp",
    executionEnabled ? "MCP tool execution is enabled." : `MCP ${overall}; tool execution denied.`,
    executionEnabled ? "danger" : state,
  );
  clearPairRequiredOutput("mcp-output");
  show("mcp-output", payload);
}

function mcpPolicyBody() {
  const server = byId("mcp-server").value.trim() || "desktop-commander";
  const tool = byId("mcp-tool").value.trim() || "start_process";
  return { operation: "call-tool", server, tool };
}

function compactHealthText(payload) {
  const checks = payload.checks || {};
  const mobile = payload.mobile || {};
  const telegram = payload.telegram || {};
  const mcp = payload.mcp || {};
  const network = payload.network_calls || {};
  const security = payload.security || {};
  const lines = [
    `lai-gateway health-report: ${payload.overall || "unknown"}`,
    `version: ${payload.version || "unknown"}`,
    "scope: read-only daily operations snapshot",
    `doctor: ${checks.doctor || "unknown"}`,
    `harness_model: ${checks.harness_model || "unknown"}`,
    `mobile: ${checks.mobile || "unknown"} listener_active=${Boolean(mobile.listener_active)}`,
    `telegram: ${checks.telegram || "unknown"} send_enabled=${Boolean(telegram.send_enabled)}`,
    `model: ${checks.gateway_model_probe || "unknown"} runs=${checks.model_runs || 0}`,
    `mcp_broker: ${checks.mcp_broker || "unknown"} servers=${mcp.server_count || 0} execution_enabled=${Boolean(mcp.execution_enabled)}`,
    `network_calls: harness_local=${Boolean(network.harness_local)} model_local=${Boolean(network.model_local)} telegram=false`,
    `security: tokens=${Boolean(security.prints_tokens)} pairing_secret=${Boolean(security.prints_pairing_secret)} writes=${Boolean(security.modifies_files)} starts_server=${Boolean(security.starts_server)}`,
  ];
  const steps = Array.isArray(payload.next_steps) ? payload.next_steps.slice(0, 6) : [];
  if (steps.length) {
    lines.push("next_steps:");
    for (const step of steps) lines.push(`  ${step}`);
  }
  return lines.join("\n");
}

function healthSummaryText(payload) {
  const overall = payload.overall || "unknown";
  const checks = payload.checks || {};
  const nextSteps = Array.isArray(payload.next_steps) ? payload.next_steps.length : 0;
  const mobile = checks.mobile || "unknown";
  const telegram = checks.telegram || "unknown";
  const model = checks.gateway_model_probe || "unknown";
  const mcp = checks.mcp_broker || "unknown";
  if (overall === "ready" && nextSteps === 0) {
    return "All systems ready. Mobile, Telegram, model, and MCP checks are ready.";
  }
  if (overall === "blocked") {
    return `Health blocked. Review ${nextSteps || "the"} next step${nextSteps === 1 ? "" : "s"} before using remote controls.`;
  }
  return `Health ${overall}; ${nextSteps} next step${nextSteps === 1 ? "" : "s"}. Mobile ${mobile}, Telegram ${telegram}, model ${model}, MCP ${mcp}.`;
}

function setHealthReport(payload) {
  const overall = payload.overall || "unknown";
  const nextSteps = Array.isArray(payload.next_steps) ? payload.next_steps.length : 0;
  const state = overall === "ready" && nextSteps === 0 ? "ready" : overall === "blocked" ? "danger" : "warn";
  setPill("ops-pill", `health ${overall}`, state);
  const checks = payload.checks || {};
  const mobile = checks.mobile || "unknown";
  const telegram = checks.telegram || "unknown";
  const mcp = checks.mcp_broker || "unknown";
  setCallout("health-summary", healthSummaryText(payload), state);
  setCheck("check-access", `Health: mobile ${mobile}, telegram ${telegram}, MCP ${mcp}.`, state);
  clearPairRequiredOutput("health-output");
  show("health-output", compactHealthText(payload));
}

function setOpsStatus(payload) {
  const overall = payload.overall || "unknown";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
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

function updateLocalTaskCounter() {
  const task = byId("local-run-task");
  const counter = byId("local-task-counter");
  if (!task || !counter) return;
  counter.textContent = `${task.value.length} / ${task.maxLength || 12000}`;
}

function applyPreset(mode) {
  if (!TASK_PRESETS[mode]) return;
  byId("run-mode").value = mode;
  byId("run-task").value = TASK_PRESETS[mode];
  updateTaskCounter();
}

function localModeLabel(mode) {
  if (LOCAL_CHAT_WORK_MODES.has(mode)) return "Work";
  if (mode === "review") return "Apply";
  return "Observe";
}

function applyLocalModePreset(presetName) {
  const preset = LOCAL_MODE_PRESETS[presetName];
  if (!preset) return;
  if (!activeLocalRunTerminal) {
    setLocalNextStep("A run is active. Cancel or wait before changing mode.", "warn");
    return;
  }
  byId("local-run-mode").value = preset.mode;
  lastLocalMode = preset.mode;
  byId("local-run-task").value = preset.task;
  updateLocalTaskCounter();
  const state = presetName === "work" ? "running" : "ready";
  updateLocalModeFlow(presetName, state);
  setText("local-mode-label", localModeLabel(preset.mode));
  setText("local-status-label", "ready");
  const nextSteps = {
    observe: "Observe is read-only. Use it for diagnosis, planning, review, security, and release checks.",
    work: "Work writes only inside the isolated sandbox. Review is required before promotion.",
    promote: "Apply starts with review. Promotion still requires the reviewed patch hash.",
  };
  setLocalNextStep(nextSteps[presetName], state);
  setLocalChatSummary(`${localModeLabel(preset.mode)} selected · ${preset.mode}`, state);
}

function setPill(id, text, state = "muted") {
  const pill = byId(id);
  if (!pill) return;
  pill.textContent = text;
  pill.className = `pill ${state}`;
}


function setLocalChatSummary(text, state = "warn") {
  setCallout("local-chat-summary", text, state);
  setPill("workbench-pill", text.length > 54 ? `${text.slice(0, 51)}...` : text, state);
}

function localWorkspaceLabel(workspace) {
  if (!workspace) return "not loaded";
  const name = workspace.display_name || workspace.repository_name || workspace.workspace_id;
  const branch = workspace.branch ? ` · ${workspace.branch}` : "";
  const clean = workspace.git_clean === false ? " · dirty" : " · clean";
  return `${name}${branch}${clean}`;
}

function localModePhaseForMode(mode) {
  if (LOCAL_CHAT_WORK_MODES.has(mode)) return "work";
  if (mode === "review") return "promote";
  return "observe";
}

function setLocalNextStep(text, state = "warn") {
  setCallout("local-next-step", text, state);
}

function updateLocalModeFlow(phase = "observe", state = "warn") {
  const order = ["observe", "work", "promote"];
  if (!order.includes(phase)) phase = "observe";
  let reachedActive = false;
  for (const item of order) {
    const step = byId(`local-flow-${item}`);
    if (!step) continue;
    if (item === phase) {
      reachedActive = true;
      step.className = `flow-step ${state}`;
    } else if (!reachedActive && order.indexOf(item) < order.indexOf(phase)) {
      step.className = "flow-step ready";
    } else {
      step.className = "flow-step muted";
    }
  }
}

function summarizeLocalChildTelemetry(run) {
  const child = run.workspace_child_summary || {};
  const validation = run.workspace_last_validation || {};
  const lines = [
    `run: ${run.control_run_id || run.run_id || "unknown"}`,
    `mode: ${run.mode || "unknown"}`,
    `status: ${run.status || "unknown"}${run.timed_out ? " · timed out" : ""}`,
  ];
  if (child.tool_call_count !== undefined || child.write_call_count !== undefined || child.validation_call_count !== undefined) {
    lines.push(`telemetry: tools=${child.tool_call_count || 0} writes=${child.write_call_count || 0} validations=${child.validation_call_count || 0}`);
    lines.push(`paths: modified=${child.modified_path_count || 0} recent=${child.recent_path_count || 0}`);
  }
  if (child.last_phase || child.last_tool) {
    lines.push(`last: ${child.last_phase || "unknown"} via ${child.last_tool || "unknown"}`);
  }
  if (validation.status || child.last_validation_status) {
    lines.push(`validation: ${validation.status || child.last_validation_status} exit=${validation.exit_code ?? child.last_validation_exit_code ?? "unknown"}`);
  }
  return lines.join("\n");
}

function localNextStepForRun(run) {
  const status = run.status || "unknown";
  if (LOCAL_CHAT_WORK_MODES.has(run.mode || "") && status === "succeeded") {
    return ["Work run succeeded. Review the diff, verify the patch hash, then promote only if the result is expected.", "ready", "promote"];
  }
  if (status === "failed" || status === "timed_out") {
    return ["Run failed. Inspect the telemetry summary and events before retrying or changing the task.", "danger", localModePhaseForMode(run.mode || "")];
  }
  if (status === "cancelled" || status === "canceled") {
    return ["Run cancelled. Start a new bounded task when ready.", "warn", localModePhaseForMode(run.mode || "")];
  }
  if (!TERMINAL_STATUSES.has(status)) {
    return ["Run is active. Wait for terminal status before review or promotion.", "running", localModePhaseForMode(run.mode || "")];
  }
  return ["Read-only run finished. Use Work for isolated changes or Promote after a reviewed patch.", "ready", localModePhaseForMode(run.mode || "")];
}

function selectValue(id) {
  const item = byId(id);
  return item ? item.value.trim() : "";
}

function shortSha(value) {
  return value ? value.slice(0, 12) : "not available";
}

function setListItems(id, values, emptyText) {
  const list = byId(id);
  if (!list) return;
  list.replaceChildren();
  const safeValues = values.filter(Boolean);
  if (!safeValues.length) {
    const item = document.createElement("li");
    item.textContent = emptyText;
    list.appendChild(item);
    return;
  }
  for (const value of safeValues) {
    const item = document.createElement("li");
    item.textContent = value;
    list.appendChild(item);
  }
}

function reviewPayloadRoot(payload) {
  return payload.review || payload.promotion || payload || {};
}

function changedPathsFromReview(payload) {
  const review = reviewPayloadRoot(payload);
  if (Array.isArray(review.changed_paths)) return review.changed_paths.filter(Boolean);
  if (Array.isArray(payload.changed_paths)) return payload.changed_paths.filter(Boolean);
  const files = Array.isArray(review.files) ? review.files : Array.isArray(payload.files) ? payload.files : [];
  return files.map((file) => file.path || file.relative_path || file.name || "").filter(Boolean);
}

function validationStatusFromReview(payload) {
  const review = reviewPayloadRoot(payload);
  const validation = review.validation || payload.validation || review.validation_summary || {};
  return review.validation_status || payload.validation_status || validation.status || validation.overall || "Missing";
}

function diffInfoFromReview(payload) {
  const review = reviewPayloadRoot(payload);
  const files = Array.isArray(review.files) ? review.files : Array.isArray(payload.files) ? payload.files : [];
  const fileDiffs = files
    .map((file) => {
      const path = file.path || file.relative_path || file.name || "file";
      const diff = file.diff || file.patch || file.unified_diff || "";
      return diff ? `--- ${path}\n${diff}` : "";
    })
    .filter(Boolean);
  const parts = [];
  if (typeof review.diff === "string" && review.diff) parts.push(review.diff);
  if (typeof payload.diff === "string" && payload.diff) parts.push(payload.diff);
  if (typeof review.patch === "string" && review.patch) parts.push(review.patch);
  parts.push(...fileDiffs);
  const truncated = Boolean(review.diff_truncated || payload.diff_truncated || review.truncated || payload.truncated);
  const text = parts.join("\n\n").trim();
  return {
    text,
    state: text ? (truncated ? "Truncated" : "Available") : "Missing",
    truncated,
  };
}

function telemetryTextFromReview(payload) {
  const review = reviewPayloadRoot(payload);
  const telemetry = review.telemetry || payload.telemetry || review.metrics || payload.metrics || {};
  const lines = [];
  for (const [key, value] of Object.entries(telemetry)) {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      lines.push(`${key}: ${value}`);
    }
  }
  if (review.validation || payload.validation) lines.push(`validation: ${validationStatusFromReview(payload)}`);
  if (review.status) lines.push(`review_status: ${review.status}`);
  if (payload.status) lines.push(`payload_status: ${payload.status}`);
  return lines.length ? lines.join("\n") : "No telemetry available.";
}

function reviewEvidenceFromPayload(payload) {
  const review = reviewPayloadRoot(payload);
  const patchSha = review.patch_sha256 || payload.patch_sha256 || "";
  const runId = payload.control_run_id || review.control_run_id || selectValue("local-run-id");
  const workspaceId = payload.workspace_id || review.workspace_id || selectValue("local-workspace");
  const changedPaths = changedPathsFromReview(payload);
  const validationStatus = validationStatusFromReview(payload);
  const diffInfo = diffInfoFromReview(payload);
  const stale = Boolean(review.stale || payload.stale || review.review_stale || payload.review_stale);
  return { review, patchSha, runId, workspaceId, changedPaths, validationStatus, diffInfo, stale };
}

function validationPassed(status) {
  return ["passed", "pass", "ok", "ready", "succeeded", "success"].includes(String(status || "").toLowerCase());
}

function applyBlockersForReview(evidence) {
  const blockers = [];
  if (!evidence.runId) blockers.push("run identity missing");
  if (!evidence.workspaceId) blockers.push("workspace identity missing");
  if (!/^[0-9a-f]{64}$/.test(evidence.patchSha)) blockers.push("patch hash missing");
  if (!evidence.changedPaths.length) blockers.push("changed files missing");
  if (!validationPassed(evidence.validationStatus)) blockers.push(`validation ${evidence.validationStatus || "missing"}`);
  if (evidence.diffInfo.state !== "Available") blockers.push(`diff ${evidence.diffInfo.state.toLowerCase()}`);
  if (evidence.diffInfo.truncated) blockers.push("diff truncated");
  if (evidence.stale) blockers.push("review stale");
  return blockers;
}

function resetLocalReviewPanel(reason = "No review loaded.") {
  currentLocalReview = null;
  const panel = byId("local-review-panel");
  if (panel) panel.hidden = true;
  setText("local-review-title", "No review loaded");
  setPill("local-review-status", "review unavailable", "muted");
  setCallout("local-review-summary", reason, "warn");
  setText("local-review-validation", "Missing");
  setText("local-review-files-count", "0");
  setText("local-review-patch", "not available");
  setText("local-review-diff-state", "Missing");
  setListItems("local-review-files", [], "No changed files.");
  show("local-review-telemetry", "No telemetry available.");
  show("local-review-diff", "No diff loaded.");
  setButtonState("local-review-apply-button", true, "Apply reviewed change");
  setText("local-review-result", "No review decision yet.");
}

function renderReviewPanel(payload) {
  const evidence = reviewEvidenceFromPayload(payload);
  const blockers = applyBlockersForReview(evidence);
  const applyReady = blockers.length === 0;
  const panel = byId("local-review-panel");
  if (panel) panel.hidden = false;
  currentLocalReview = {
    payload,
    runId: evidence.runId,
    workspaceId: evidence.workspaceId,
    patchSha: evidence.patchSha,
    changedCount: evidence.changedPaths.length,
    validationStatus: evidence.validationStatus,
    diffState: evidence.diffInfo.state,
    blockers,
  };
  setText("local-review-title", evidence.changedPaths.length ? "Reviewed change proposal" : "Review loaded without changed files");
  setPill("local-review-status", applyReady ? "ready to apply" : "apply blocked", applyReady ? "ready" : "warn");
  setCallout(
    "local-review-summary",
    applyReady
      ? "Review is complete. Apply will use the workspace, run id, and patch hash from this review payload."
      : `Apply disabled: ${blockers.join(", ") || "review incomplete"}.`,
    applyReady ? "ready" : "warn",
  );
  setText("local-review-validation", evidence.validationStatus || "Missing");
  setText("local-review-files-count", String(evidence.changedPaths.length));
  setText("local-review-patch", shortSha(evidence.patchSha));
  setText("local-review-diff-state", evidence.diffInfo.state);
  setListItems("local-review-files", evidence.changedPaths, "No changed files.");
  show("local-review-telemetry", telemetryTextFromReview(payload));
  show("local-review-diff", evidence.diffInfo.text || "No displayable diff in review payload. Open Advanced / Debug for raw metadata.");
  setButtonState("local-review-apply-button", !applyReady, applyReady ? "Apply reviewed change" : "Apply blocked");
  setText("local-review-result", applyReady ? "Awaiting explicit confirmation." : "Fix the blocked review state or load a fresh review before applying.");
  return currentLocalReview;
}

async function loadLocalReviewForCurrentRun() {
  const runId = selectValue("local-run-id");
  const workspaceId = selectValue("local-workspace");
  if (!runId) throw new Error("local run id is required");
  if (!workspaceId) throw new Error("workspace is required");
  const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/review?workspace_id=${encodeURIComponent(workspaceId)}`);
  setLocalReview(payload);
  return payload;
}

async function maybeLoadReviewAfterTerminalRun(payload) {
  const runId = payload.control_run_id || payload.run_id || selectValue("local-run-id");
  const mode = payload.mode || selectValue("local-run-mode");
  if (!payload.terminal || payload.status !== "succeeded" || !LOCAL_CHAT_WORK_MODES.has(mode) || !runId) return;
  if (currentLocalReview && currentLocalReview.runId === runId) return;
  try {
    await loadLocalReviewForCurrentRun();
  } catch (err) {
    setLocalNextStep("Work run finished, but review could not be loaded. Open Advanced / Debug for raw events.", "warn");
    show("local-review-output", String(err.message || err));
  }
}

function setOptions(selectId, items, valueKey, labelFn) {
  const select = byId(selectId);
  if (!select) return "";
  const previous = select.value;
  select.replaceChildren();
  for (const item of items) {
    const value = item[valueKey];
    if (!value) continue;
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labelFn(item);
    select.appendChild(option);
  }
  if (previous && Array.from(select.options).some((option) => option.value === previous)) {
    select.value = previous;
  }
  return select.value;
}

function setLocalChatContract(payload) {
  const capabilities = payload.capabilities || {};
  const work = Boolean(capabilities.local_chat_work_runs || capabilities.work_runs);
  const state = payload.negotiated ? "ready" : "warn";
  setLocalChatSummary(`workbench ${payload.negotiated ? "negotiated" : "not negotiated"}; work_runs=${work}`, state);
  updateLocalRunCard("Contract", `local-chat negotiated=${Boolean(payload.negotiated)}; work_runs=${work}`, payload.negotiated ? "ready" : "warn", state);
  show("local-chat-output", payload);
}

function setLocalWorkspaces(payload) {
  const workspaces = Array.isArray(payload.workspaces) ? payload.workspaces : [];
  const selected = setOptions("local-workspace", workspaces, "workspace_id", localWorkspaceLabel);
  const selectedWorkspace = workspaces.find((workspace) => workspace.workspace_id === selected);
  setText("local-project-label", localWorkspaceLabel(selectedWorkspace));
  setLocalChatSummary(workspaces.length ? `Project selected · ${localWorkspaceLabel(selectedWorkspace)}` : "no local-chat workspace", workspaces.length ? "ready" : "danger");
  updateLocalRunCard("Project", workspaces.length ? `Selected ${localWorkspaceLabel(selectedWorkspace)}` : "No local-chat workspace found", workspaces.length ? "ready" : "missing", workspaces.length ? "ready" : "danger");
  show("local-chat-output", payload);
}

function setLocalModels(payload) {
  const models = Array.isArray(payload.models) ? payload.models : [];
  const selected = setOptions("local-model", models, "model_id", (model) => {
    const label = model.label || model.model_id;
    const available = model.available === false ? " · unavailable" : " · available";
    return `${label}${available}`;
  });
  setLocalChatSummary(models.length ? `model selected ${selected}` : "no local-chat model", models.length ? "ready" : "danger");
  show("local-chat-output", payload);
}

function setLocalRunFromPayload(payload) {
  const run = payload.run || payload;
  const runId = run.control_run_id || run.run_id || payload.control_run_id;
  if (runId) byId("local-run-id").value = runId;
  const status = run.status || payload.status || "unknown";
  const mode = run.mode || payload.mode || selectValue("local-run-mode") || "unknown";
  const state = TERMINAL_STATUSES.has(status) ? (status === "succeeded" ? "ready" : "danger") : "running";
  if (runId) activeLocalRunId = runId;
  activeLocalRunTerminal = TERMINAL_STATUSES.has(status);
  updateLocalExecutionControls(status);
  setText("local-mode-label", localModeLabel(mode));
  setText("local-status-label", status);
  setText("local-conversation-title", runId ? `Run ${runId}` : "LAI run");
  setText("local-conversation-mode", localModeLabel(mode));
  const [nextStep, nextState, phase] = localNextStepForRun({ ...run, status, mode });
  updateLocalModeFlow(phase, nextState);
  setLocalNextStep(nextStep, nextState);
  const childSummary = summarizeLocalChildTelemetry({ ...run, status, mode });
  show("local-run-summary", childSummary);
  updateLocalRunCard(`${localModeLabel(mode)} run`, `Status ${status}${runId ? ` · ${runId}` : ""}`, status, state);
  if (runId && TERMINAL_STATUSES.has(status) && !localChatRenderedRuns.has(`${runId}:${status}`)) {
    localChatRenderedRuns.add(`${runId}:${status}`);
    appendLocalToolMessage("Run finished", `${localModeLabel(mode)} ended with ${status}. Review appears when a patch is eligible.`, state);
  }
  setLocalChatSummary(`local ${mode} ${status}`, state);
  show("local-chat-output", payload);
}

function setLocalReview(payload) {
  const review = payload.review || payload.promotion || payload;
  const patchSha = review.patch_sha256 || payload.patch_sha256 || "";
  if (patchSha) byId("local-patch-sha").value = patchSha;
  const status = review.status || payload.status || "review loaded";
  const reviewState = renderReviewPanel(payload);
  const state = reviewState && reviewState.blockers.length === 0 ? "ready" : "warn";
  setText("local-mode-label", "Apply");
  setText("local-status-label", status);
  updateLocalModeFlow("promote", state);
  setLocalNextStep(
    state === "ready"
      ? "Review loaded. Apply is bound to this workspace, run, and patch hash."
      : "Review loaded but Apply is blocked until validation, diff, workspace, run, and patch evidence are complete.",
    state,
  );
  updateLocalRunCard("Review", state === "ready" ? "Review is eligible for explicit Apply." : "Review loaded with blockers.", status, state);
  appendLocalToolMessage("Review loaded", state === "ready" ? "Apply is available in the right rail." : "Apply is blocked until review evidence is complete.", state);
  setLocalChatSummary(`review ${status}`, state);
  show("local-review-output", payload);
}

async function loadLocalChatModelsForSelectedWorkspace() {
  const workspaceId = selectValue("local-workspace");
  if (!workspaceId) throw new Error("workspace is required");
  return requestJson(`/v1/local-chat/models?workspace_id=${encodeURIComponent(workspaceId)}`);
}

async function fetchLocalChatEvents() {
  const runId = selectValue("local-run-id");
  if (!runId) throw new Error("local run id is required");
  const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/events?cursor=${lastLocalChatCursor}`);
  const events = Array.isArray(payload.events) ? payload.events : [];
  if (Number.isInteger(payload.next_cursor)) lastLocalChatCursor = payload.next_cursor;
  setLocalRunFromPayload(payload);
  show("local-chat-output", payload);
  if (payload.terminal) {
    stopLocalChatPolling();
    await maybeLoadReviewAfterTerminalRun(payload);
  }
  return payload;
}

function startLocalChatPolling() {
  stopLocalChatPolling();
  activeLocalRunTerminal = false;
  updateLocalExecutionControls(selectValue("local-run-id") ? "running" : "idle");
  setLocalChatSummary("polling local run", "running");
  localChatPollTimer = window.setInterval(() => {
    fetchLocalChatEvents().catch((err) => {
      stopLocalChatPolling();
      show("local-chat-output", String(err.message || err));
    });
  }, 1400);
}

function stopLocalChatPolling() {
  if (localChatPollTimer !== null) {
    window.clearInterval(localChatPollTimer);
    localChatPollTimer = null;
  }
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
  const id = run.control_run_id || run.run_id || "unknown";
  const status = run.status || "unknown";
  const mode = run.mode || "unknown";
  return `${id} · ${mode} · ${status}`;
}

function recordRun(run) {
  const runId = run && (run.control_run_id || run.run_id);
  if (!runId) return;
  const existing = runHistory.findIndex((item) => item.control_run_id === runId);
  if (existing >= 0) runHistory.splice(existing, 1);
  runHistory.unshift({
    control_run_id: runId,
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
  const runId = run && (run.control_run_id || run.run_id);
  if (runId) {
    byId("run-id").value = runId;
    lastRunPayload = payload;
    const state = TERMINAL_STATUSES.has(run.status) ? (run.status === "succeeded" ? "ready" : "danger") : "running";
    setPill("active-run-pill", summarizeRun(run), state);
    setCheck("check-run", summarizeRun(run), state);
    recordRun(run);
  }
}

function renderRunEvents(payload) {
  const events = Array.isArray(payload.events) ? payload.events : [];
  const runId = payload.control_run_id || "unknown run";
  const status = payload.status || "unknown";
  const lines = [`${runId} · ${status}${payload.terminal ? " · terminal" : ""}`];
  if (!events.length) {
    lines.push("No timeline events reported yet.");
    return lines.join("\n");
  }
  for (const event of events) {
    const label = event.event || event.name || "event";
    const eventStatus = event.status ? ` · ${event.status}` : "";
    const at = event.at || "time unknown";
    const details = event.details && Object.keys(event.details).length
      ? ` · ${JSON.stringify(event.details)}`
      : "";
    lines.push(`${at} · ${label}${eventStatus}${details}`);
  }
  return lines.join("\n");
}

function setRunEventsFromPayload(payload) {
  lastRunEventsPayload = payload;
  const events = Array.isArray(payload.events) ? payload.events : [];
  const status = payload.status || "unknown";
  const state = payload.terminal ? (status === "succeeded" ? "ready" : "danger") : "running";
  show("run-events-output", renderRunEvents(payload));
  setPill("active-run-pill", `run events ${events.length} · ${status}`, state);
}

async function fetchSelectedRunEvents() {
  const runId = byId("run-id").value.trim();
  if (!runId) throw new Error("run id is required");
  const payload = await requestJson(`/v1/harness/runs/${encodeURIComponent(runId)}/events`);
  setRunEventsFromPayload(payload);
  return payload;
}

async function pollSelectedRun() {
  const runId = byId("run-id").value.trim();
  if (!runId) throw new Error("run id is required");
  const payload = await requestJson(`/v1/harness/runs/${encodeURIComponent(runId)}`);
  setRunFromPayload(payload);
  show("runs-output", payload);
  await fetchSelectedRunEvents();
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
      const payload = await requestJson("/v1/gateway/health-report");
      setHealthReport(payload);
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
    } else if (action === "refresh-health-report") {
      clearPairRequiredOutput("health-output");
      setHealthReport(await requestJson("/v1/gateway/health-report"));
    } else if (action === "send-health-report-telegram") {
      clearPairRequiredOutput("health-output");
      setCallout("health-telegram-result", "Sending health report to Telegram...", "warn");
      const payload = await requestJson("/v1/gateway/health-report/telegram", { method: "POST" });
      setHealthReport(payload.health_report || payload);
      const notify = payload.telegram_notify || {};
      setCallout("health-telegram-result", notify.sent ? `Health report sent to Telegram. message_id=${notify.message_id || "unknown"}` : "Telegram delivery did not report success.", notify.sent ? "ready" : "danger");
    } else if (action === "refresh-ops-status") {
      clearPairRequiredOutput("ops-output");
      setOpsStatus(await requestJson("/v1/gateway/ops-status"));
    } else if (action === "refresh-mcp-status") {
      setMcpStatus(await requestJson("/v1/harness/mcp/status"));
    } else if (action === "refresh-mcp-tools") {
      setMcpStatus(await requestJson("/v1/harness/mcp/tools"));
    } else if (action === "check-mcp-call-tool") {
      const payload = await requestJson("/v1/harness/mcp/policy-check", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(mcpPolicyBody()),
      });
      setMcpStatus(payload);
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
    } else if (action === "refresh-local-chat-contract") {
      setLocalChatContract(await requestJson("/v1/local-chat/contract"));
    } else if (action === "load-local-chat-workspaces") {
      const payload = await requestJson("/v1/local-chat/workspaces");
      setLocalWorkspaces(payload);
      if (selectValue("local-workspace")) setLocalModels(await loadLocalChatModelsForSelectedWorkspace());
    } else if (action === "load-local-chat-models") {
      setLocalModels(await loadLocalChatModelsForSelectedWorkspace());
    } else if (action === "create-local-chat-run") {
      const mode = selectValue("local-run-mode");
      const task = byId("local-run-task").value.trim();
      const workspaceId = selectValue("local-workspace");
      const modelId = selectValue("local-model") || "default";
      const sessionId = selectValue("session-id");
      if (!LOCAL_CHAT_MODES.has(mode)) throw new Error("unsupported local-chat mode");
      if (!task) throw new Error("task is required");
      if (!workspaceId) throw new Error("workspace is required");
      if (!activeLocalRunTerminal && activeLocalRunId) throw new Error("local run already active");
      resetLocalReviewPanel("New run started. Previous review was cleared.");
      activeLocalRunTerminal = false;
      updateLocalExecutionControls("running");
      const body = { mode, task, workspace_id: workspaceId, model_id: modelId };
      if (sessionId) body.session_id = sessionId;
      lastLocalChatCursor = 0;
      appendLocalChatTurn("user", "You", task);
      appendLocalToolMessage("Starting LAI run", `${localModeLabel(mode)} request queued through Gateway.`, "running");
      const payload = await requestJson("/v1/local-chat/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(body),
      });
      setLocalRunFromPayload(payload);
      if (LOCAL_CHAT_WORK_MODES.has(mode)) setLocalChatSummary(`local ${mode} queued; review before promotion`, "running");
      startLocalChatPolling();
    } else if (action === "get-local-chat-events") {
      await fetchLocalChatEvents();
    } else if (action === "poll-local-chat-run") {
      await fetchLocalChatEvents();
      startLocalChatPolling();
    } else if (action === "stop-local-chat-polling") {
      stopLocalChatPolling();
      setLocalChatSummary("local polling stopped", "warn");
    } else if (action === "get-local-chat-review") {
      await loadLocalReviewForCurrentRun();
    } else if (action === "apply-current-local-review") {
      if (!currentLocalReview) throw new Error("no current review is loaded");
      if (currentLocalReview.blockers.length) throw new Error(`apply blocked: ${currentLocalReview.blockers.join(", ")}`);
      const projectLabel = byId("local-project-label").textContent || currentLocalReview.workspaceId;
      const confirmation = [
        "Apply this reviewed change?",
        `Project: ${projectLabel}`,
        `Files changed: ${currentLocalReview.changedCount}`,
        `Validation: ${currentLocalReview.validationStatus}`,
        `Patch: ${shortSha(currentLocalReview.patchSha)}`,
        "",
        "This applies the reviewed patch through Harness promotion gates.",
      ].join("\n");
      if (!window.confirm(confirmation)) return;
      setButtonState("local-review-apply-button", true, "Applying...");
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(currentLocalReview.runId)}/promotion`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ workspace_id: currentLocalReview.workspaceId, patch_sha256: currentLocalReview.patchSha }),
      });
      const promotion = payload.promotion || payload;
      const result = promotion.status || payload.status || "unknown";
      show("local-review-output", payload);
      if (["applied", "promoted", "succeeded", "success"].includes(String(result).toLowerCase())) {
        currentLocalReview = null;
        setPill("local-review-status", "applied", "ready");
        setCallout("local-review-summary", "Backend confirmed the reviewed change was applied through promotion gates.", "ready");
        setButtonState("local-review-apply-button", true, "Applied");
        setText("local-review-result", "Applied. Active review cleared; source checkout state remains governed by Harness promotion output.");
        setLocalNextStep("Promotion applied. Check the reported destination before any Git push or PR.", "ready");
      } else if (["drift", "stale"].includes(String(result).toLowerCase())) {
        setPill("local-review-status", "drift", "danger");
        setCallout("local-review-summary", "Promotion reported drift. Load a fresh review before retrying.", "danger");
        setButtonState("local-review-apply-button", true, "Fresh review required");
      } else if (["rejected", "denied", "blocked", "failed"].includes(String(result).toLowerCase())) {
        setPill("local-review-status", "rejected", "danger");
        setCallout("local-review-summary", "Promotion was not applied. Review remains visible for inspection.", "danger");
        setButtonState("local-review-apply-button", false, "Apply reviewed change");
      } else {
        setPill("local-review-status", "unknown result", "warn");
        setCallout("local-review-summary", "Promotion result is unknown. Check status before retrying.", "warn");
        setButtonState("local-review-apply-button", true, "Check status first");
      }
    } else if (action === "discard-current-local-review") {
      resetLocalReviewPanel("Review discarded in the browser. Sandbox cleanup or rollback was not implied.");
      setLocalNextStep("Review discarded locally. Select another run or start a new task.", "warn");
    } else if (action === "promote-local-chat-run") {
      const runId = selectValue("local-run-id");
      const workspaceId = selectValue("local-workspace");
      const patchSha = selectValue("local-patch-sha");
      if (!runId) throw new Error("local run id is required");
      if (!workspaceId) throw new Error("workspace is required");
      if (!/^[0-9a-f]{64}$/.test(patchSha)) throw new Error("reviewed patch sha256 is required");
      if (!window.confirm(`Promote reviewed patch ${patchSha.slice(0, 12)} for ${runId}?`)) return;
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/promotion`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ workspace_id: workspaceId, patch_sha256: patchSha }),
      });
      setLocalReview(payload);
    } else if (action === "cancel-local-chat-run") {
      const runId = selectValue("local-run-id");
      const workspaceId = selectValue("local-workspace");
      if (!runId) throw new Error("local run id is required");
      if (!workspaceId) throw new Error("workspace is required");
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/lifecycle`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ action: "cancel", workspace_id: workspaceId }),
      });
      stopLocalChatPolling();
      setLocalRunFromPayload(payload);

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
    } else if (action === "delete-session") {
      const sessionId = byId("session-id").value.trim();
      if (!sessionId) throw new Error("session id is required");
      if (!window.confirm(`Delete harness session ${sessionId}? This removes only the repository-scoped session record.`)) return;
      const payload = await requestJson(`/v1/harness/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
      clearSession();
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
    } else if (action === "get-run-events") {
      await fetchSelectedRunEvents();
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
    const target = action.includes("local-chat")
      ? "local-chat-output"
      : action.includes("session")
        ? "sessions-output"
        : action.includes("run") || action === "copy-run-output"
          ? "runs-output"
          : action.includes("mcp")
            ? "mcp-output"
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
  const localPresetButton = event.target.closest("button[data-local-mode-preset]");
  if (localPresetButton) applyLocalModePreset(localPresetButton.dataset.localModePreset);
});

document.addEventListener("DOMContentLoaded", () => {
  updateTaskCounter();
  const taskBox = byId("run-task");
  if (taskBox) taskBox.addEventListener("input", updateTaskCounter);
  updateLocalTaskCounter();
  const localTaskBox = byId("local-run-task");
  if (localTaskBox) localTaskBox.addEventListener("input", updateLocalTaskCounter);
  const localModeSelect = byId("local-run-mode");
  if (localModeSelect) {
    localModeSelect.addEventListener("change", () => {
      if (!activeLocalRunTerminal) {
        localModeSelect.value = lastLocalMode;
        setLocalNextStep("A run is active. Cancel or wait before changing mode.", "warn");
        return;
      }
      clearLocalReviewState("Mode changed. Previous review/run selection was cleared.");
      const mode = selectValue("local-run-mode");
      lastLocalMode = mode;
      const phase = localModePhaseForMode(mode);
      const state = phase === "work" ? "running" : "ready";
      setText("local-mode-label", localModeLabel(mode));
      updateLocalModeFlow(phase, state);
      setLocalNextStep(
        phase === "work"
          ? "Work writes only inside the isolated sandbox. Review is required before promotion."
          : phase === "promote"
            ? "Apply starts with review. Promotion still requires the reviewed patch hash."
            : "Observe is read-only. Use it for diagnosis, planning, review, security, and release checks.",
        state,
      );
    });
    lastLocalMode = localModeSelect.value;
    setText("local-mode-label", localModeLabel(localModeSelect.value));
    updateLocalModeFlow(localModePhaseForMode(localModeSelect.value), "ready");
    updateLocalExecutionControls("idle");
  }
  const localWorkspaceSelect = byId("local-workspace");
  if (localWorkspaceSelect) {
    localWorkspaceSelect.addEventListener("change", () => {
      clearLocalReviewState("Workspace changed. Previous review/run selection was cleared.");
      const selectedOption = localWorkspaceSelect.options[localWorkspaceSelect.selectedIndex];
      setText("local-project-label", selectedOption ? selectedOption.textContent : "not loaded");
      runAction("load-local-chat-models");
    });
  }
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
    runAction("refresh-mcp-status");
    runAction("refresh-readiness");
    runAction("refresh-health-report");
    runAction("refresh-local-chat-contract");
    runAction("load-local-chat-workspaces");
  } else {
    setAuthBanner("Paste a fresh pair token to unlock private controls on this phone.", "warn");
    showPairRequiredOutputs();
  }
});
