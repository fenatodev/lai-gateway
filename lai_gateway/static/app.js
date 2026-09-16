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
let lastGovernancePayload = null;
const localChatRenderedRuns = new Set();
const localChatRenderedEvents = new Set();
const TASK_PRESETS = {
  plan: "Planeje o próximo passo seguro e de maior impacto a partir do estado atual do projeto.",
  review: "Revise o estado atual e identifique problemas, riscos e melhorias rápidas.",
  diagnose: "Diagnostique o problema atual e sugira verificações read-only.",
  security: "Faça uma revisão focada em segurança do estado atual e dos limites.",
  release: "Cheque prontidão de release e identifique bloqueios antes da publicação.",
};
const LOCAL_MODE_PRESETS = {
  observe: {
    mode: "diagnose",
    task: "Diagnostique o estado atual do repositório com evidências read-only. Identifique bloqueios, setup faltante e próximo passo seguro.",
  },
  work: {
    mode: "implement",
    task: "Implemente uma alteração delimitada no workspace isolado do sandbox. Mantenha o checkout fonte intacto, valide e deixe a promoção para revisão.",
  },
  promote: {
    mode: "review",
    task: "Revise o diff do run isolado selecionado. Verifique o hash do patch e liste riscos antes de promover.",
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
  setButtonState("local-send-button", running, running ? "Run ativo" : "Enviar ao LAI");
  setButtonState("local-cancel-button", !running, running ? "Cancelar run ativo" : "Sem run ativo");
}

function clearLocalReviewState(reason = "") {
  byId("local-run-id").value = "";
  byId("local-patch-sha").value = "";
  activeLocalRunId = "";
  activeLocalRunTerminal = true;
  lastLocalChatCursor = 0;
  resetLocalReviewPanel(reason || "Nenhuma revisão carregada.");
  updateLocalExecutionControls("idle");
  if (reason) setLocalNextStep(reason, "warn");
}


function appendLocalChatTurn(kind, title, text) {
  const thread = byId("local-chat-thread");
  if (!thread) return;
  const anchor = byId("local-chat-live-anchor");
  const row = document.createElement("div");
  row.className = kind === "user" ? "message-row user-row" : kind === "status" ? "message-row status-row" : "message-row assistant-row";
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = kind === "user" ? "V" : kind === "status" ? "•" : "L";
  const bubble = document.createElement("article");
  bubble.className = kind === "user" ? "message-bubble user-bubble" : kind === "status" ? "message-bubble assistant-bubble status-bubble" : "message-bubble assistant-bubble";
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
  setText("local-conversation-mode", byId("local-mode-label")?.textContent || "Observar");
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
  const message = "Pareie este celular primeiro e atualize este painel.";
  for (const id of ["health-output", "ops-output", "status-output", "model-output", "mcp-output", "sessions-output", "runs-output", "run-events-output", "governance-output", "decision-output", "policy-output", "authorization-output", "proposal-output", "audit-events-output", "dry-run-output", "capture-output", "validation-output", "effective-output", "dispatcher-output", "memory-output", "document-output", "alpha-output"]) {
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
  byId("mobile-access-url").textContent = lastMobileUrl || "Nenhuma URL mobile detectada.";
  const label = browserUrl ? "URL mobile do navegador atual" : (payload.recommended_kind ? `mobile ${payload.recommended_kind}` : "URL mobile indisponível");
  setPill("mobile-access-kind", label, lastMobileUrl ? "ready" : "danger");
  setMobileQr(payload.qr_svg || "");
  show("mobile-access-output", browserUrl ? { ...payload, active_phone_url: browserUrl } : payload);
}


function setAlphaReadiness(payload) {
  const overall = payload.overall || "desconhecido";
  const decision = payload.decision || "sem decisão";
  const state = overall === "ready" ? "ready" : "danger";
  setPill("readiness-pill", `alpha ${decision}`, state);
  clearPairRequiredOutput("alpha-output");
  show("alpha-output", payload);
}

function setModelStatus(payload) {
  const overall = payload.overall || "desconhecido";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  const fallback = payload.fallback?.used ? " · fallback local explícito" : "";
  show("model-output", payload);
  setCheck("check-model", `Modelo ${overall}${fallback}.`, state);
}

function modelChatBody() {
  const message = byId("model-chat-message")?.value.trim() || "";
  if (!message) throw new Error("mensagem obrigatória para conversa local");
  return { message, timeout_seconds: 60, max_tokens: 768 };
}

function memoryContextBody(memoryAction = "show") {
  const contextKind = byId("memory-context-kind")?.value || "project";
  const projectId = byId("memory-project-id")?.value.trim() || "default";
  const note = byId("memory-note")?.value.trim() || "";
  const body = { memory_action: memoryAction, context_kind: contextKind, project_id: projectId, limit: 20 };
  if (memoryAction === "remember") body.note = note;
  return body;
}

function documentTextBody() {
  const workspaceRoot = byId("document-workspace-root")?.value.trim() || ".";
  const relativePath = byId("document-relative-path")?.value.trim() || "";
  if (!relativePath) throw new Error("caminho relativo do documento obrigatório");
  return { workspace_root: workspaceRoot, relative_path: relativePath, max_chars: 6000 };
}

function documentWorkbenchParams({ includeSelection = false } = {}) {
  const body = documentTextBody();
  const params = new URLSearchParams({
    workspace_root: body.workspace_root,
    max_results: "25",
    max_chars: "3000",
  });
  if (includeSelection && body.relative_path) params.set("selected_relative_path", body.relative_path);
  return params;
}

function setDocumentWorkbench(payload) {
  const select = byId("document-relative-select");
  if (select) {
    const selected = byId("document-relative-path")?.value.trim() || "";
    select.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = payload.documents?.length ? "selecione documento permitido" : "nenhum documento permitido listado";
    select.appendChild(empty);
    for (const item of payload.documents || []) {
      const option = document.createElement("option");
      option.value = item.relative_path;
      option.textContent = `${item.relative_path} · ${item.extension} · ${item.size_bytes} bytes`;
      select.appendChild(option);
    }
    if (selected && Array.from(select.options).some((option) => option.value === selected)) select.value = selected;
  }
  const count = payload.workbench?.candidate_count ?? 0;
  const status = payload.overall || "desconhecido";
  setPill("model-pill", `documentos ${status} · ${count}`, status === "blocked" ? "danger" : "ready");
  show("document-output", payload);
}

function setMcpStatus(payload) {
  const overall = payload.overall || payload.mcp_overall || "desconhecido";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  const serverCount = Number.isInteger(payload.server_count) ? payload.server_count : 0;
  const executionEnabled = Boolean(
    payload.execution_enabled || (payload.security && payload.security.executes_tools)
  );
  setPill("mcp-pill", `mcp ${overall}${serverCount ? ` · ${serverCount}` : ""}`, executionEnabled ? "danger" : state);
  setCheck(
    "check-mcp",
    executionEnabled ? "Execução de tools MCP habilitada." : `MCP ${overall}; execução de tools negada.`,
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
    `lai-gateway health-report: ${payload.overall || "desconhecido"}`,
    `version: ${payload.version || "desconhecido"}`,
    "scope: read-only daily operations snapshot",
    `doctor: ${checks.doctor || "desconhecido"}`,
    `harness_model: ${checks.harness_model || "desconhecido"}`,
    `mobile: ${checks.mobile || "desconhecido"} listener_active=${Boolean(mobile.listener_active)}`,
    `telegram: ${checks.telegram || "desconhecido"} send_enabled=${Boolean(telegram.send_enabled)}`,
    `model: ${checks.gateway_model_probe || "desconhecido"} runs=${checks.model_runs || 0}`,
    `mcp_broker: ${checks.mcp_broker || "desconhecido"} servers=${mcp.server_count || 0} execution_enabled=${Boolean(mcp.execution_enabled)}`,
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
  const overall = payload.overall || "desconhecido";
  const checks = payload.checks || {};
  const nextSteps = Array.isArray(payload.next_steps) ? payload.next_steps.length : 0;
  const mobile = checks.mobile || "desconhecido";
  const telegram = checks.telegram || "desconhecido";
  const model = checks.gateway_model_probe || "desconhecido";
  const mcp = checks.mcp_broker || "desconhecido";
  if (overall === "ready" && nextSteps === 0) {
    return "Todos os sistemas estão prontos. Mobile, Telegram, modelo e MCP verificados.";
  }
  if (overall === "blocked") {
    return `Saúde bloqueada. Revise ${nextSteps || "o"} próximo passo${nextSteps === 1 ? "" : "s"} antes de usar controles remotos.`;
  }
  return `Saúde ${overall}; ${nextSteps} próximo passo${nextSteps === 1 ? "" : "s"}. Mobile ${mobile}, Telegram ${telegram}, modelo ${model}, MCP ${mcp}.`;
}

function setHealthReport(payload) {
  const overall = payload.overall || "desconhecido";
  const nextSteps = Array.isArray(payload.next_steps) ? payload.next_steps.length : 0;
  const state = overall === "ready" && nextSteps === 0 ? "ready" : overall === "blocked" ? "danger" : "warn";
  setPill("ops-pill", `health ${overall}`, state);
  const checks = payload.checks || {};
  const mobile = checks.mobile || "desconhecido";
  const telegram = checks.telegram || "desconhecido";
  const mcp = checks.mcp_broker || "desconhecido";
  setCallout("health-summary", healthSummaryText(payload), state);
  setCheck("check-access", `Health: mobile ${mobile}, telegram ${telegram}, MCP ${mcp}.`, state);
  clearPairRequiredOutput("health-output");
  show("health-output", compactHealthText(payload));
}

function setOpsStatus(payload) {
  const overall = payload.overall || "desconhecido";
  const state = overall === "ready" ? "ready" : overall === "blocked" ? "danger" : "running";
  const doctor = payload.doctor && payload.doctor.overall ? payload.doctor.overall : "desconhecido";
  const mobileSession = payload.mobile_session && payload.mobile_session.overall === "ready" ? "session ready" : "";
  const mobile = mobileSession || (payload.mobile && payload.mobile.overall ? payload.mobile.overall : "desconhecido");
  const telegram = payload.telegram && payload.telegram.overall ? payload.telegram.overall : "desconhecido";
  setCheck("check-access", `Ops: doctor ${doctor}, mobile ${mobile}, telegram ${telegram}.`, state);
  clearPairRequiredOutput("ops-output");
  show("ops-output", payload);
}


function governanceQuery(options = {}) {
  const params = new URLSearchParams();
  params.set("adapter_id", selectValue("governance-adapter") || "local_status");
  params.set("capability", selectValue("governance-capability") || "local_status.status");
  params.set("actor", "user");
  params.set("channel", "workbench");
  params.set("domain", "governance");
  params.set("action", selectValue("governance-action") || "consultar status local seguro");
  const param = selectValue("governance-param");
  if (param) params.append("param", param);
  if (options.approve) params.set("approve", "true");
  if (options.approvedBy) params.set("approved_by", options.approvedBy);
  if (options.operationScope) params.set("operation_scope", options.operationScope);
  if (options.dispatch) params.set("dispatch", "true");
  return params.toString();
}

function governanceApprovedQuery() {
  return governanceQuery({ approve: true, approvedBy: "workbench", operationScope: "adapter-dry-run" });
}

function isSafeLocalStatusSelection() {
  const adapter = selectValue("governance-adapter") || "local_status";
  const capability = selectValue("governance-capability") || "local_status.status";
  return adapter === "local_status" && capability === "local_status.status";
}

function governanceState(payload) {
  const proposal = payload.proposal || {};
  const dryRun = payload.dry_run || {};
  const decision = payload.decision || proposal || (payload.record || {});
  const events = Array.isArray(payload.events) ? payload.events : [];
  const outcome = dryRun.status || decision.outcome || proposal.decision_outcome || proposal.status || payload.overall || "desconhecido";
  const requiresApproval = Boolean(
    decision.requires_human_approval
      || proposal.requires_human_approval
      || events.some((event) => event.requires_human_approval)
  );
  if (payload.operation === "adapter-dispatcher" && payload.result === "local_status" && payload.handler_result?.local_only && payload.dispatcher?.authorization_consumed && !payload.handler_result?.external_side_effects && !payload.handler_result?.shell_execution && !payload.handler_result?.filesystem_write) {
    return ["ready", "local_status executado após autorização persistida de uso único; handler sem rede, shell ou efeito externo."];
  }
  if (payload.operation === "adapter-dispatcher" && payload.dispatch_permitted === false) {
    return ["warn", "Dispatcher carregado sem execução. Só local_status pode ser despachado pela UI."];
  }
  if (payload.dispatch_enabled || proposal.dispatch_enabled || dryRun.dispatch_enabled || dryRun.adapter_dispatched || payload.effective_authorization || proposal.effective_authorization || dryRun.effective_authorization) {
    return ["danger", "Governança reportou autorização efetiva, dispatch ou execução fora do caminho seguro. Verifique antes de prosseguir."];
  }
  if (payload.operation === "adapter-dry-run" && outcome === "simulated") {
    return ["ready", "Dry-run simulado e não efetivo. Adapter não foi despachado nem executado."];
  }
  if (requiresApproval || outcome === "requires_approval" || outcome === "requires_authorization") {
    return ["warn", "Ação declarada exige aprovação humana. A UI apenas mostra a cadeia; não executa adapter."];
  }
  if (outcome === "deny" || outcome === "blocked") {
    return ["danger", "Ação bloqueada pela política ou pelo contrato do adapter."];
  }
  return ["ready", "Cadeia de governança carregada em modo read-only, sem dispatch."];
}

function setGovernanceOutput(targetId, payload) {
  lastGovernancePayload = payload;
  clearPairRequiredOutput(targetId);
  clearPairRequiredOutput("governance-output");
  show(targetId, payload);
  const [state, summary] = governanceState(payload);
  setCallout("governance-summary", summary, state);
  const operation = payload.operation || "governance";
  const count = Array.isArray(payload.events) ? ` · events=${payload.events.length}` : "";
  setPill("governance-pill", `${operation}${count}`, state);
  show("governance-output", {
    operation,
    overall: payload.overall || "unknown",
    dispatch_enabled: Boolean(payload.dispatch_enabled || payload.proposal?.dispatch_enabled || payload.dry_run?.dispatch_enabled),
    dispatch_permitted: Boolean(payload.dispatch_permitted || payload.dispatcher?.dispatch_permitted),
    handler_registered: Boolean(payload.dispatcher?.handler_registered),
    dry_run_executed: Boolean(payload.dry_run?.dry_run_executed),
    adapter_dispatched: Boolean(payload.adapter_dispatched || payload.dispatcher?.adapter_dispatched || payload.dry_run?.adapter_dispatched),
    adapter_executed: Boolean(payload.adapter_executed || payload.dispatcher?.adapter_executed || payload.dry_run?.adapter_executed),
    result: payload.result || "none",
    effective_authorization: Boolean(payload.effective_authorization || payload.proposal?.effective_authorization || payload.dry_run?.effective_authorization),
    executes_tools: Boolean(payload.executes_tools || payload.proposal?.executes_tools || payload.dry_run?.executes_tools),
    external_side_effects: Boolean(payload.external_side_effects || payload.handler_result?.external_side_effects),
    grants_permissions: Boolean(payload.security?.grants_permissions || payload.proposal?.grants_permission || payload.dry_run?.grants_permission),
  });
}

async function refreshGovernanceChain() {
  const query = governanceQuery();
  const decision = await requestJson(`/v1/gateway/permission-decision?${query}`);
  setGovernanceOutput("decision-output", decision);
  const policy = await requestJson(`/v1/gateway/policy-eval?${query}`);
  setGovernanceOutput("policy-output", policy);
  const authorization = await requestJson(`/v1/gateway/authorization-record?${query}`);
  setGovernanceOutput("authorization-output", authorization);
  const proposal = await requestJson(`/v1/gateway/adapter-invocation-proposal?${query}`);
  setGovernanceOutput("proposal-output", proposal);
  const events = await requestJson(`/v1/gateway/audit-events?${query}`);
  setGovernanceOutput("audit-events-output", events);
  const dryRun = await requestJson(`/v1/gateway/adapter-dry-run?${query}`);
  setGovernanceOutput("dry-run-output", dryRun);
  const dispatcher = await requestJson(`/v1/gateway/adapter-dispatcher?${query}`);
  setGovernanceOutput("dispatcher-output", dispatcher);
  return dispatcher;
}

async function copyMobileUrl() {
  const text = lastMobileUrl || byId("mobile-access-url").textContent;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text || "");
    setPill("mobile-access-kind", "URL mobile copiada", "ready");
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
  if (LOCAL_CHAT_WORK_MODES.has(mode)) return "Trabalhar";
  if (mode === "review") return "Aplicar";
  return "Observar";
}

function applyLocalModePreset(presetName) {
  const preset = LOCAL_MODE_PRESETS[presetName];
  if (!preset) return;
  if (!activeLocalRunTerminal) {
    setLocalNextStep("Há um run ativo. Cancele ou aguarde antes de mudar o modo.", "warn");
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
    observe: "Observar é read-only. Use para diagnóstico, planejamento, revisão, segurança e checagem de release.",
    work: "Trabalhar escreve apenas dentro do sandbox isolado. Revisão é obrigatória antes da promoção.",
    promote: "Aplicar começa pela revisão. A promoção ainda exige o hash do patch revisado.",
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
  if (!workspace) return "não carregado";
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
    `run: ${run.control_run_id || run.run_id || "desconhecido"}`,
    `mode: ${run.mode || "desconhecido"}`,
    `status: ${run.status || "desconhecido"}${run.timed_out ? " · timed out" : ""}`,
  ];
  if (child.tool_call_count !== undefined || child.write_call_count !== undefined || child.validation_call_count !== undefined) {
    lines.push(`telemetry: tools=${child.tool_call_count || 0} writes=${child.write_call_count || 0} validations=${child.validation_call_count || 0}`);
    lines.push(`paths: modified=${child.modified_path_count || 0} recent=${child.recent_path_count || 0}`);
  }
  if (child.last_phase || child.last_tool) {
    lines.push(`last: ${child.last_phase || "desconhecido"} via ${child.last_tool || "desconhecido"}`);
  }
  if (validation.status || child.last_validation_status) {
    lines.push(`validation: ${validation.status || child.last_validation_status} exit=${validation.exit_code ?? child.last_validation_exit_code ?? "desconhecido"}`);
  }
  return lines.join("\n");
}

function localNextStepForRun(run) {
  const status = run.status || "desconhecido";
  if (LOCAL_CHAT_WORK_MODES.has(run.mode || "") && status === "succeeded") {
    return ["Run de trabalho concluído. Revise o diff, confira o hash e aplique apenas se o resultado estiver correto.", "ready", "promote"];
  }
  if (status === "failed" || status === "timed_out") {
    return ["Run falhou. Inspecione telemetria e eventos antes de tentar novamente ou alterar a tarefa.", "danger", localModePhaseForMode(run.mode || "")];
  }
  if (status === "cancelled" || status === "canceled") {
    return ["Run cancelado. Inicie uma nova tarefa delimitada quando estiver pronto.", "warn", localModePhaseForMode(run.mode || "")];
  }
  if (!TERMINAL_STATUSES.has(status)) {
    return ["Run ativo. Aguarde status terminal antes de revisar ou promover.", "running", localModePhaseForMode(run.mode || "")];
  }
  return ["Run read-only finalizado. Use Trabalhar para alterações isoladas ou Aplicar após revisão.", "ready", localModePhaseForMode(run.mode || "")];
}

function selectValue(id) {
  const item = byId(id);
  return item ? item.value.trim() : "";
}

function shortSha(value) {
  return value ? value.slice(0, 12) : "indisponível";
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
  return review.validation_status || payload.validation_status || validation.status || validation.overall || "Ausente";
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
    state: text ? (truncated ? "Truncado" : "Disponível") : "Ausente",
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
  return lines.length ? lines.join("\n") : "Nenhuma telemetria disponível.";
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
  if (!evidence.runId) blockers.push("identidade do run ausente");
  if (!evidence.workspaceId) blockers.push("identidade do workspace ausente");
  if (!/^[0-9a-f]{64}$/.test(evidence.patchSha)) blockers.push("hash do patch ausente");
  if (!evidence.changedPaths.length) blockers.push("arquivos alterados ausentes");
  if (!validationPassed(evidence.validationStatus)) blockers.push(`validation ${evidence.validationStatus || "missing"}`);
  if (evidence.diffInfo.state !== "Disponível") blockers.push(`diff ${evidence.diffInfo.state.toLowerCase()}`);
  if (evidence.diffInfo.truncated) blockers.push("diff truncado");
  if (evidence.stale) blockers.push("revisão obsoleta");
  return blockers;
}

function resetLocalReviewPanel(reason = "Nenhuma revisão carregada.") {
  currentLocalReview = null;
  const panel = byId("local-review-panel");
  if (panel) panel.hidden = true;
  setText("local-review-title", "Nenhuma revisão carregada");
  setPill("local-review-status", "revisão indisponível", "muted");
  setCallout("local-review-summary", reason, "warn");
  setText("local-review-validation", "Ausente");
  setText("local-review-files-count", "0");
  setText("local-review-patch", "indisponível");
  setText("local-review-diff-state", "Ausente");
  setListItems("local-review-files", [], "Nenhum arquivo alterado.");
  show("local-review-telemetry", "Nenhuma telemetria disponível.");
  show("local-review-diff", "Nenhum diff carregado.");
  setButtonState("local-review-apply-button", true, "Aplicar alteração revisada");
  setText("local-review-result", "Nenhuma decisão de revisão ainda.");
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
  setText("local-review-title", evidence.changedPaths.length ? "Proposta de alteração revisada" : "Revisão carregada sem arquivos alterados");
  setPill("local-review-status", applyReady ? "pronto para aplicar" : "aplicação bloqueada", applyReady ? "ready" : "warn");
  setCallout(
    "local-review-summary",
    applyReady
      ? "Revisão completa. Aplicar usará workspace, run id e hash de patch desta revisão."
      : `Aplicação desabilitada: ${blockers.join(", ") || "revisão incompleta"}.`,
    applyReady ? "ready" : "warn",
  );
  setText("local-review-validation", evidence.validationStatus || "Ausente");
  setText("local-review-files-count", String(evidence.changedPaths.length));
  setText("local-review-patch", shortSha(evidence.patchSha));
  setText("local-review-diff-state", evidence.diffInfo.state);
  setListItems("local-review-files", evidence.changedPaths, "Nenhum arquivo alterado.");
  show("local-review-telemetry", telemetryTextFromReview(payload));
  show("local-review-diff", evidence.diffInfo.text || "Nenhum diff exibível no payload de revisão. Abra Debug avançado para metadados brutos.");
  setButtonState("local-review-apply-button", !applyReady, applyReady ? "Aplicar alteração revisada" : "Aplicação bloqueada");
  setText("local-review-result", applyReady ? "Aguardando confirmação explícita." : "Corrija o bloqueio da revisão ou carregue uma revisão nova antes de aplicar.");
  return currentLocalReview;
}

async function loadLocalReviewForCurrentRun() {
  const runId = selectValue("local-run-id");
  const workspaceId = selectValue("local-workspace");
  if (!runId) throw new Error("run id local obrigatório");
  if (!workspaceId) throw new Error("workspace obrigatório");
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
    setLocalNextStep("Run de trabalho finalizou, mas a revisão não pôde ser carregada. Abra o Debug avançado para eventos brutos.", "warn");
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
  setLocalChatSummary(`workbench ${payload.negotiated ? "negociado" : "não negociado"}; work_runs=${work}`, state);
  updateLocalRunCard("Contrato", `local-chat negociado=${Boolean(payload.negotiated)}; work_runs=${work}`, payload.negotiated ? "ready" : "warn", state);
  show("local-chat-output", payload);
}

function setLocalWorkspaces(payload) {
  const workspaces = Array.isArray(payload.workspaces) ? payload.workspaces : [];
  const selected = setOptions("local-workspace", workspaces, "workspace_id", localWorkspaceLabel);
  const selectedWorkspace = workspaces.find((workspace) => workspace.workspace_id === selected);
  setText("local-project-label", localWorkspaceLabel(selectedWorkspace));
  setLocalChatSummary(workspaces.length ? `Projeto selecionado · ${localWorkspaceLabel(selectedWorkspace)}` : "nenhum workspace local-chat", workspaces.length ? "ready" : "danger");
  updateLocalRunCard("Projeto", workspaces.length ? `Selecionado ${localWorkspaceLabel(selectedWorkspace)}` : "Nenhum workspace local-chat encontrado", workspaces.length ? "ready" : "missing", workspaces.length ? "ready" : "danger");
  show("local-chat-output", payload);
}

function setLocalModels(payload) {
  const models = Array.isArray(payload.models) ? payload.models : [];
  const selected = setOptions("local-model", models, "model_id", (model) => {
    const label = model.label || model.model_id;
    const available = model.available === false ? " · unavailable" : " · available";
    return `${label}${available}`;
  });
  setLocalChatSummary(models.length ? `modelo selecionado ${selected}` : "nenhum modelo local-chat", models.length ? "ready" : "danger");
  show("local-chat-output", payload);
}

function setLocalRunFromPayload(payload) {
  const run = payload.run || payload;
  const runId = run.control_run_id || run.run_id || payload.control_run_id;
  if (runId) byId("local-run-id").value = runId;
  const status = run.status || payload.status || "desconhecido";
  const mode = run.mode || payload.mode || selectValue("local-run-mode") || "desconhecido";
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
    appendLocalToolMessage("Run finalizado", `${localModeLabel(mode)} finalizou com ${status}. A revisão aparece quando houver patch elegível.`, state);
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
  setText("local-mode-label", "Aplicar");
  setText("local-status-label", status);
  updateLocalModeFlow("promote", state);
  setLocalNextStep(
    state === "ready"
      ? "Revisão carregada. Aplicar está preso a workspace, run e hash do patch."
      : "Revisão carregada, mas Aplicar está bloqueado até validação, diff, workspace, run e evidência de patch ficarem completos.",
    state,
  );
  updateLocalRunCard("Revisão", state === "ready" ? "Revisão elegível para aplicação explícita." : "Revisão carregada com bloqueios.", status, state);
  appendLocalToolMessage("Revisão carregada", state === "ready" ? "Aplicar está disponível na barra lateral direita." : "Aplicar fica bloqueado até a revisão ficar completa.", state);
  setLocalChatSummary(`revisão ${status}`, state);
  show("local-review-output", payload);
}

async function loadLocalChatModelsForSelectedWorkspace() {
  const workspaceId = selectValue("local-workspace");
  if (!workspaceId) throw new Error("workspace obrigatório");
  return requestJson(`/v1/local-chat/models?workspace_id=${encodeURIComponent(workspaceId)}`);
}

function localEventDisplayText(event) {
  const name = event.event || event.type || event.phase || "evento";
  const status = event.status || event.state || "em andamento";
  const tool = event.tool || event.tool_name || event.last_tool || "";
  const phase = event.phase && event.phase !== name ? ` · fase ${event.phase}` : "";
  const via = tool ? ` · via ${tool}` : "";
  return `${name} · ${status}${phase}${via}`;
}

function renderLocalChatEvents(events, runId) {
  for (const event of events) {
    if (!event || typeof event !== "object") continue;
    const name = event.event || event.type || event.phase || "evento";
    const status = event.status || event.state || "em andamento";
    const cursor = event.cursor ?? event.sequence ?? event.index ?? "";
    const key = `${runId || "run"}:${cursor}:${name}:${status}`;
    if (localChatRenderedEvents.has(key)) continue;
    localChatRenderedEvents.add(key);
    appendLocalChatTurn("status", "LAI trabalhando", localEventDisplayText(event));
  }
}

async function fetchLocalChatEvents() {
  const runId = selectValue("local-run-id");
  if (!runId) throw new Error("run id local obrigatório");
  const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/events?cursor=${lastLocalChatCursor}`);
  const events = Array.isArray(payload.events) ? payload.events : [];
  renderLocalChatEvents(events, runId);
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
  setLocalChatSummary("acompanhando run local", "running");
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

function openVSCodeFolderHandoff() {
  const uri = "vscode://fenatodev.lai-chat/open-folder";
  appendLocalToolMessage(
    "Abrindo VS Code",
    "Autorize o navegador a abrir o VS Code. No painel LAI, use Abrir pasta/repositório para escolher ou focar o projeto.",
    "running",
  );
  window.location.href = uri;
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
    byId("gateway-access-state").textContent = "Nenhum token do Gateway carregado na memória da página.";
    setCheck("check-access", "Token de pareamento ainda não carregado.", "muted");
    return;
  }
  if (ok) {
    const label = `${tokenKindLabel()} authenticated.`;
    byId("gateway-access-state").textContent = `${label} Token remains only in page memory.`;
    setCheck("check-access", `${tokenKindLabel()} authenticated in memory.`, "ready");
    return;
  }
  if (status === 401) {
    byId("gateway-access-state").textContent = "Token carregado ausente, inválido ou expirado.";
    setCallout("gateway-auth-result", "Token não aceito ou sessão mobile expirada. Gere um novo token de pareamento e tente novamente.", "danger");
    setAuthBanner("Pareamento falhou ou sessão mobile expirou. Gere um novo token de pareamento e tente novamente.", "danger");
    setCheck("check-access", "Token de pareamento ausente, inválido ou expirado.", "danger");
  } else if (status === 403) {
    byId("gateway-access-state").textContent = "Token carregado rejeitado pelo Gateway.";
    setCallout("gateway-auth-result", "Token rejeitado pelo Gateway.", "danger");
    setAuthBanner("Token rejeitado pelo Gateway.", "danger");
    setCheck("check-access", "Token carregado rejeitado.", "danger");
  } else if (status === 429) {
    byId("gateway-access-state").textContent = "Muitas tentativas inválidas de token. Aguarde antes de tentar novamente.";
    setCallout("gateway-auth-result", "Muitas tentativas inválidas de token. Aguarde antes de tentar novamente.", "danger");
    setAuthBanner("Muitas tentativas inválidas de token. Aguarde antes de tentar novamente.", "danger");
    setCheck("check-access", "Tentativas de token limitadas.", "danger");
  }
}

function parseSessionExpiresAt(raw) {
  const value = (raw || "").trim();
  if (!value) return null;
  const instant = Date.parse(value);
  if (Number.isNaN(instant)) throw new Error("expiração de sessão precisa ser um timestamp ISO");
  return instant;
}

function tokenKindLabel() {
  if (gatewayTokenKind === "session") return "Sessão mobile";
  if (gatewayTokenKind === "pair") return "Token de pareamento";
  if (gatewayTokenKind === "permanent") return "Token do Gateway";
  return "Sem token";
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
  throw new Error("Gateway não retornou token de sessão mobile");
}

function renderSessionCountdown() {
  const target = byId("pairing-state");
  if (gatewayTokenKind !== "session" || sessionExpiresAt === null) {
    target.textContent = "Nenhum temporizador de sessão mobile carregado.";
    target.className = "muted";
    return;
  }
  const remainingSeconds = Math.max(0, Math.floor((sessionExpiresAt - Date.now()) / 1000));
  if (remainingSeconds <= 0) {
    target.textContent = "Sessão mobile expirada. Esqueça o token e pareie novamente.";
    target.className = "danger-text";
    return;
  }
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  target.textContent = `Sessão mobile: ${minutes}m ${String(seconds).padStart(2, "0")}s restantes.`;
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
    setCheck("check-session", `Sessão selecionada: ${session.session_id}`, "ready");
  }
}

function summarizeRun(run) {
  const id = run.control_run_id || run.run_id || "desconhecido";
  const status = run.status || "desconhecido";
  const mode = run.mode || "desconhecido";
  return `${id} · ${mode} · ${status}`;
}

function recordRun(run) {
  const runId = run && (run.control_run_id || run.run_id);
  if (!runId) return;
  const existing = runHistory.findIndex((item) => item.control_run_id === runId);
  if (existing >= 0) runHistory.splice(existing, 1);
  runHistory.unshift({
    control_run_id: runId,
    mode: run.mode || "desconhecido",
    status: run.status || "desconhecido",
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
  const status = payload.status || "desconhecido";
  const lines = [`${runId} · ${status}${payload.terminal ? " · terminal" : ""}`];
  if (!events.length) {
    lines.push("Nenhum evento de linha do tempo reportado ainda.");
    return lines.join("\n");
  }
  for (const event of events) {
    const label = event.event || event.name || "evento";
    const eventStatus = event.status ? ` · ${event.status}` : "";
    const at = event.at || "hora desconhecida";
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
  const status = payload.status || "desconhecido";
  const state = payload.terminal ? (status === "succeeded" ? "ready" : "danger") : "running";
  show("run-events-output", renderRunEvents(payload));
  setPill("active-run-pill", `run events ${events.length} · ${status}`, state);
}

async function fetchSelectedRunEvents() {
  const runId = byId("run-id").value.trim();
  if (!runId) throw new Error("run id obrigatório");
  const payload = await requestJson(`/v1/harness/runs/${encodeURIComponent(runId)}/events`);
  setRunEventsFromPayload(payload);
  return payload;
}

async function pollSelectedRun() {
  const runId = byId("run-id").value.trim();
  if (!runId) throw new Error("run id obrigatório");
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
  setPill("active-run-pill", "acompanhando run selecionado", "running");
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
  setPill("active-session-pill", "sem sessão ativa", "muted");
  setCheck("check-session", "Nenhuma sessão ativa selecionada.", "muted");
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
    setPill("active-run-pill", "saída copiada", "ready");
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
        byId("gateway-access-state").textContent = "Nenhum token do Gateway carregado na memória da página.";
        setCallout("gateway-auth-result", "Cole um token de pareamento antes de parear este celular.", "danger");
        setAuthBanner("Cole um token de pareamento antes de usar controles privados.", "warn");
        setCheck("check-access", "Token de pareamento ainda não carregado.", "muted");
        return;
      }
      byId("gateway-access-state").textContent = `${selectedTokenKind === "pair" ? "Pair" : "Gateway"} token loaded in page memory. Validating now...`;
      setCallout("gateway-auth-result", "Validando token com o Gateway...", "warn");
      setAuthBanner("Validando pareamento do celular...", "warn");
      setCheck("check-access", `${selectedTokenKind === "pair" ? "Pair" : "Gateway"} token validating.`, "running");
      let sessionPayload = null;
      if (selectedTokenKind === "pair") {
        sessionPayload = await exchangeMobileSession(gatewayAccessToken);
        setCallout("gateway-auth-result", "Pareado com sucesso. Sessão mobile liberada nesta página.", "ready");
        setAuthBanner("Celular pareado. Sessão mobile temporária ativa só nesta página.", "ready");
      } else {
        startSessionCountdown();
        setCallout("gateway-auth-result", "Token do Gateway aceito. Controles privados liberados nesta página.", "ready");
        setAuthBanner("Token do Gateway aceito. Controles privados liberados só nesta página.", "ready");
      }
      const payload = await requestJson("/v1/gateway/health-report");
      setHealthReport(payload);
      if (sessionPayload && sessionPayload.expires_at) {
        setCallout("gateway-auth-result", `Pareado com sucesso. Sessão mobile expira em ${sessionPayload.expires_at}.`, "ready");
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
      byId("gateway-access-state").textContent = "Nenhum token do Gateway carregado na memória da página.";
      setCallout("gateway-auth-result", "Token esquecido. Cole um novo token de pareamento para liberar este celular.", "warn");
      setAuthBanner("Celular não pareado. Controles privados bloqueados.", "warn");
      setCheck("check-access", "Token de pareamento ainda não carregado.", "muted");
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
      setCallout("health-telegram-result", "Enviando relatório de saúde ao Telegram...", "warn");
      const payload = await requestJson("/v1/gateway/health-report/telegram", { method: "POST" });
      setHealthReport(payload.health_report || payload);
      const notify = payload.telegram_notify || {};
      setCallout("health-telegram-result", notify.sent ? `Relatório de saúde enviado ao Telegram. message_id=${notify.message_id || "desconhecido"}` : "Entrega no Telegram não reportou sucesso.", notify.sent ? "ready" : "danger");
    } else if (action === "refresh-ops-status") {
      clearPairRequiredOutput("ops-output");
      setOpsStatus(await requestJson("/v1/gateway/ops-status"));
    } else if (action === "refresh-governance-chain") {
      await refreshGovernanceChain();
    } else if (action === "refresh-governance-decision") {
      const payload = await requestJson(`/v1/gateway/permission-decision?${governanceQuery()}`);
      setGovernanceOutput("decision-output", payload);
    } else if (action === "refresh-governance-policy") {
      const payload = await requestJson(`/v1/gateway/policy-eval?${governanceQuery()}`);
      setGovernanceOutput("policy-output", payload);
    } else if (action === "refresh-governance-authorization") {
      const payload = await requestJson(`/v1/gateway/authorization-record?${governanceQuery()}`);
      setGovernanceOutput("authorization-output", payload);
    } else if (action === "refresh-governance-proposal") {
      const payload = await requestJson(`/v1/gateway/adapter-invocation-proposal?${governanceQuery()}`);
      setGovernanceOutput("proposal-output", payload);
    } else if (action === "refresh-governance-audit") {
      const payload = await requestJson(`/v1/gateway/audit-events?${governanceQuery()}`);
      setGovernanceOutput("audit-events-output", payload);
    } else if (action === "refresh-governance-dry-run") {
      const payload = await requestJson(`/v1/gateway/adapter-dry-run?${governanceQuery()}`);
      setGovernanceOutput("dry-run-output", payload);
    } else if (action === "refresh-governance-capture") {
      const payload = await requestJson(`/v1/gateway/authorization-capture-stub?${governanceApprovedQuery()}`);
      setGovernanceOutput("capture-output", payload);
    } else if (action === "refresh-governance-validation") {
      const payload = await requestJson(`/v1/gateway/authorization-validation-gate?${governanceApprovedQuery()}`);
      setGovernanceOutput("validation-output", payload);
    } else if (action === "refresh-governance-effective") {
      const payload = await requestJson(`/v1/gateway/effective-authorization?${governanceApprovedQuery()}`);
      setGovernanceOutput("effective-output", payload);
    } else if (action === "refresh-governance-dispatcher") {
      const payload = await requestJson(`/v1/gateway/adapter-dispatcher?${governanceApprovedQuery()}`);
      setGovernanceOutput("dispatcher-output", payload);
    } else if (action === "dispatch-local-status") {
      if (!isSafeLocalStatusSelection()) throw new Error("dispatch seguro permitido somente para local_status.status");
      const confirmation = [
        "Executar adapter local_status agora?",
        "Escopo: local-status-read com autorização persistida de uso único.",
        "A autorização será gravada/consumida localmente; o handler não usa rede, shell, credenciais ou arquivo.",
      ].join("\n");
      if (!window.confirm(confirmation)) return;
      const baseQuery = governanceQuery({ approve: true, approvedBy: "workbench", operationScope: "local-status-read" });
      const issued = await requestJson(`/v1/gateway/authorization-recovery?${baseQuery}&recovery_action=issue`);
      if (!issued.authorization_grant_id) throw new Error("falha ao emitir autorização local de uso único");
      const query = governanceQuery({ approve: true, approvedBy: "workbench", operationScope: "local-status-read", dispatch: true });
      const dispatchQuery = `${query}&authorization_grant_id=${encodeURIComponent(issued.authorization_grant_id)}`;
      const payload = await requestJson(`/v1/gateway/adapter-dispatcher?${dispatchQuery}`);
      setGovernanceOutput("dispatcher-output", payload);
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
    } else if (action === "send-model-chat") {
      const payload = await requestJson("/v1/gateway/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(modelChatBody()),
      });
      setModelStatus(payload);
    } else if (action === "refresh-alpha-readiness") {
      setAlphaReadiness(await requestJson("/v1/gateway/alpha-readiness"));
    } else if (action === "refresh-model-status") {
      setModelStatus(await requestJson("/v1/gateway/model-status"));
    } else if (action === "refresh-model-plan") {
      const payload = await requestJson("/v1/gateway/model-plan");
      setPill("model-pill", `model plan ${payload.overall || "desconhecido"}`, payload.overall === "ready_to_prepare" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-model-files") {
      const payload = await requestJson("/v1/gateway/model-files?max_results=10");
      setPill("model-pill", `arquivos de modelo ${payload.models_found || 0}`, payload.recommended ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "run-model-task") {
      const payload = await requestJson("/v1/gateway/model-task?task=code-mini&timeout_seconds=60");
      setPill("model-pill", `model task ${payload.overall || "desconhecido"}`, payload.overall === "ready" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "run-model-eval") {
      const payload = await requestJson("/v1/gateway/model-eval?timeout_seconds=60");
      setPill("model-pill", `model eval ${payload.overall || "desconhecido"}`, payload.overall === "ready" ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-model-runs") {
      const payload = await requestJson("/v1/gateway/model-runs?limit=20");
      setPill("model-pill", `runs do modelo ${payload.count || 0}`, payload.count ? "ready" : "warn");
      show("model-output", payload);
    } else if (action === "refresh-memory-context") {
      const body = memoryContextBody("show");
      const params = new URLSearchParams({
        context_kind: body.context_kind,
        project_id: body.project_id,
        limit: String(body.limit),
      });
      const payload = await requestJson(`/v1/gateway/memory-context?${params}`);
      setPill("model-pill", `memória ${payload.overall || "desconhecido"}`, payload.overall === "blocked" ? "danger" : "ready");
      show("memory-output", payload);
    } else if (action === "remember-memory-context") {
      const payload = await requestJson("/v1/gateway/memory-context", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(memoryContextBody("remember")),
      });
      setPill("model-pill", `memória ${payload.overall || "desconhecido"}`, payload.overall === "blocked" ? "danger" : "ready");
      show("memory-output", payload);
    } else if (action === "refresh-document-workbench") {
      const payload = await requestJson(`/v1/gateway/document-workbench?${documentWorkbenchParams()}`);
      setDocumentWorkbench(payload);
    } else if (action === "inspect-document-workbench") {
      const payload = await requestJson(`/v1/gateway/document-workbench?${documentWorkbenchParams({ includeSelection: true })}`);
      setDocumentWorkbench(payload);
    } else if (action === "read-document-text-local") {
      const payload = await requestJson("/v1/gateway/document-text-local", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(documentTextBody()),
      });
      setPill("model-pill", `documento ${payload.overall || "desconhecido"}`, payload.overall === "blocked" ? "danger" : "ready");
      show("document-output", payload);
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
      if (!LOCAL_CHAT_MODES.has(mode)) throw new Error("modo local-chat não suportado");
      if (!task) throw new Error("tarefa obrigatória");
      if (!workspaceId) throw new Error("workspace obrigatório");
      if (!activeLocalRunTerminal && activeLocalRunId) throw new Error("já existe um run local ativo");
      resetLocalReviewPanel("Novo run iniciado. Revisão anterior limpa.");
      activeLocalRunTerminal = false;
      updateLocalExecutionControls("running");
      const body = { mode, task, workspace_id: workspaceId, model_id: modelId };
      if (sessionId) body.session_id = sessionId;
      lastLocalChatCursor = 0;
      localChatRenderedEvents.clear();
      appendLocalChatTurn("user", "Você", task);
      appendLocalToolMessage("Iniciando run do LAI", `${localModeLabel(mode)} enfileirado pelo Gateway.`, "running");
      const payload = await requestJson("/v1/local-chat/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify(body),
      });
      setLocalRunFromPayload(payload);
      if (LOCAL_CHAT_WORK_MODES.has(mode)) setLocalChatSummary(`local ${mode} enfileirado; revise antes de promover`, "running");
      startLocalChatPolling();
    } else if (action === "get-local-chat-events") {
      await fetchLocalChatEvents();
    } else if (action === "poll-local-chat-run") {
      await fetchLocalChatEvents();
      startLocalChatPolling();
    } else if (action === "stop-local-chat-polling") {
      stopLocalChatPolling();
      setLocalChatSummary("polling local parado", "warn");
    } else if (action === "get-local-chat-review") {
      await loadLocalReviewForCurrentRun();
    } else if (action === "apply-current-local-review") {
      if (!currentLocalReview) throw new Error("nenhuma revisão atual carregada");
      if (currentLocalReview.blockers.length) throw new Error(`aplicação bloqueada: ${currentLocalReview.blockers.join(", ")}`);
      const projectLabel = byId("local-project-label").textContent || currentLocalReview.workspaceId;
      const confirmation = [
        "Aplicar esta alteração revisada?",
        `Projeto: ${projectLabel}`,
        `Arquivos alterados: ${currentLocalReview.changedCount}`,
        `Validação: ${currentLocalReview.validationStatus}`,
        `Patch: ${shortSha(currentLocalReview.patchSha)}`,
        "",
        "Isto aplica o patch revisado pelos gates de promoção do Harness.",
      ].join("\n");
      if (!window.confirm(confirmation)) return;
      setButtonState("local-review-apply-button", true, "Aplicando...");
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(currentLocalReview.runId)}/promotion`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ workspace_id: currentLocalReview.workspaceId, patch_sha256: currentLocalReview.patchSha }),
      });
      const promotion = payload.promotion || payload;
      const result = promotion.status || payload.status || "desconhecido";
      show("local-review-output", payload);
      if (["aplicado", "promoted", "succeeded", "success"].includes(String(result).toLowerCase())) {
        currentLocalReview = null;
        setPill("local-review-status", "aplicado", "ready");
        setCallout("local-review-summary", "Backend confirmou que a alteração revisada passou pelos gates de promoção.", "ready");
        setButtonState("local-review-apply-button", true, "Aplicado");
        setText("local-review-result", "Aplicado. Active review cleared; source checkout state remains governed by Harness promotion output.");
        setLocalNextStep("Promoção aplicada. Confira o destino relatado antes de qualquer push ou PR.", "ready");
      } else if (["drift", "stale"].includes(String(result).toLowerCase())) {
        setPill("local-review-status", "drift", "danger");
        setCallout("local-review-summary", "Promoção indicou drift. Carregue uma revisão nova antes de tentar novamente.", "danger");
        setButtonState("local-review-apply-button", true, "Revisão nova obrigatória");
      } else if (["rejected", "denied", "blocked", "failed"].includes(String(result).toLowerCase())) {
        setPill("local-review-status", "rejected", "danger");
        setCallout("local-review-summary", "Promoção não aplicada. A revisão permanece visível para inspeção.", "danger");
        setButtonState("local-review-apply-button", false, "Aplicar alteração revisada");
      } else {
        setPill("local-review-status", "resultado desconhecido", "warn");
        setCallout("local-review-summary", "Resultado da promoção desconhecido. Cheque o status antes de tentar novamente.", "warn");
        setButtonState("local-review-apply-button", true, "Checar status primeiro");
      }
    } else if (action === "discard-current-local-review") {
      resetLocalReviewPanel("Revisão descartada no navegador. Isso não limpa sandbox nem faz rollback.");
      setLocalNextStep("Revisão descartada localmente. Selecione outro run ou inicie nova tarefa.", "warn");
    } else if (action === "promote-local-chat-run") {
      const runId = selectValue("local-run-id");
      const workspaceId = selectValue("local-workspace");
      const patchSha = selectValue("local-patch-sha");
      if (!runId) throw new Error("run id local obrigatório");
      if (!workspaceId) throw new Error("workspace obrigatório");
      if (!/^[0-9a-f]{64}$/.test(patchSha)) throw new Error("sha256 do patch revisado obrigatório");
      if (!window.confirm(`Promover patch revisado ${patchSha.slice(0, 12)} para ${runId}?`)) return;
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/promotion`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ workspace_id: workspaceId, patch_sha256: patchSha }),
      });
      setLocalReview(payload);
    } else if (action === "cancel-local-chat-run") {
      const runId = selectValue("local-run-id");
      const workspaceId = selectValue("local-workspace");
      if (!runId) throw new Error("run id local obrigatório");
      if (!workspaceId) throw new Error("workspace obrigatório");
      const payload = await requestJson(`/v1/local-chat/runs/${encodeURIComponent(runId)}/lifecycle`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ action: "cancel", workspace_id: workspaceId }),
      });
      stopLocalChatPolling();
      setLocalRunFromPayload(payload);

    } else if (action === "open-vscode-folder") {
      openVSCodeFolderHandoff();

    } else if (action === "refresh-status") {
      clearPairRequiredOutput("status-output");
      show("status-output", await requestJson("/v1/harness/status"));
    } else if (action === "refresh-readiness") {
      clearPairRequiredOutput("status-output");
      const payload = await requestJson("/v1/harness/readiness");
      const overall = payload.overall || "desconhecido";
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
      if (!window.confirm(`Excluir sessão do Harness ${sessionId}? Isso remove apenas o registro de sessão escopado ao repositório.`)) return;
      const payload = await requestJson(`/v1/harness/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
      clearSession();
      show("sessions-output", payload);
    } else if (action === "clear-session") {
      clearSession();
      show("sessions-output", "Seleção de sessão limpa. As sessões existentes do Harness não foram alteradas.");
    } else if (action === "list-runs") {
      const payload = await requestJson("/v1/harness/runs?limit=10");
      setRunFromPayload(payload);
      show("runs-output", payload);
    } else if (action === "create-run") {
      const mode = byId("run-mode").value;
      const task = byId("run-task").value.trim();
      const sessionId = byId("session-id").value.trim();
      if (!READ_ONLY_MODES.has(mode)) throw new Error("modo precisa ser read-only");
      if (!task) throw new Error("tarefa obrigatória");
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
      setPill("active-run-pill", "acompanhamento parado", "muted");
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
      : action.includes("governance")
        ? "governance-output"
        : action.includes("session")
          ? "sessions-output"
        : action.includes("run") || action === "copy-run-output"
          ? "runs-output"
          : action.includes("mcp")
            ? "mcp-output"
          : action.includes("alpha")
            ? "alpha-output"
          : action.includes("ops")
            ? "ops-output"
          : action.includes("memory")
            ? "memory-output"
            : action.includes("document")
              ? "document-output"
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
  if (localTaskBox) {
    localTaskBox.addEventListener("input", updateLocalTaskCounter);
    localTaskBox.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        runAction("create-local-chat-run");
      }
    });
  }
  const localModeSelect = byId("local-run-mode");
  if (localModeSelect) {
    localModeSelect.addEventListener("change", () => {
      if (!activeLocalRunTerminal) {
        localModeSelect.value = lastLocalMode;
        setLocalNextStep("Há um run ativo. Cancele ou aguarde antes de mudar o modo.", "warn");
        return;
      }
      clearLocalReviewState("Modo alterado. Seleção anterior de revisão/run limpa.");
      const mode = selectValue("local-run-mode");
      lastLocalMode = mode;
      const phase = localModePhaseForMode(mode);
      const state = phase === "work" ? "running" : "ready";
      setText("local-mode-label", localModeLabel(mode));
      updateLocalModeFlow(phase, state);
      setLocalNextStep(
        phase === "work"
          ? "Trabalhar escreve apenas dentro do sandbox isolado. Revisão é obrigatória antes da promoção."
          : phase === "promote"
            ? "Aplicar começa pela revisão. A promoção ainda exige o hash do patch revisado."
            : "Observar é read-only. Use para diagnóstico, planejamento, revisão, segurança e checagem de release.",
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
      clearLocalReviewState("Workspace alterado. Seleção anterior de revisão/run limpa.");
      const selectedOption = localWorkspaceSelect.options[localWorkspaceSelect.selectedIndex];
      setText("local-project-label", selectedOption ? selectedOption.textContent : "não carregado");
      runAction("load-local-chat-models");
    });
  }
  const documentSelect = byId("document-relative-select");
  if (documentSelect) {
    documentSelect.addEventListener("change", () => {
      const selected = documentSelect.value || "";
      if (selected) byId("document-relative-path").value = selected;
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
    setAuthBanner("Acesso local por loopback não precisa de pareamento do celular.", "ready");
    runAction("refresh-model-status");
    runAction("refresh-memory-context");
    runAction("refresh-document-workbench");
    runAction("refresh-mcp-status");
    runAction("refresh-readiness");
    runAction("refresh-alpha-readiness");
    runAction("refresh-health-report");
    runAction("refresh-local-chat-contract");
    runAction("load-local-chat-workspaces");
  } else {
    setAuthBanner("Cole um token de pareamento novo para liberar controles privados neste celular.", "warn");
    showPairRequiredOutputs();
  }
});
