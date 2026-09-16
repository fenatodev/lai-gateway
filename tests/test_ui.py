from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from unittest.mock import patch

from lai_gateway.config import GatewayConfig
from lai_gateway.tokens import create_gateway_access_token, create_gateway_pairing_token
from lai_gateway.server import GatewayHTTPServer

from .fake_harness import TOKEN, fake_harness


class RunningGateway:
    def __init__(self, config: GatewayConfig):
        self.server = GatewayHTTPServer(("127.0.0.1", 0), config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "RunningGateway":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def read_url(url: str, headers: dict[str, str] | None = None, data: bytes | None = None, method: str | None = None) -> tuple[int, dict[str, str], str]:
    request_headers = {"Accept": "*/*", **(headers or {})}
    request = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(request, timeout=5) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.status, headers, response.read().decode("utf-8")


class GatewayUITest(unittest.TestCase):
    def test_gateway_serves_local_ui_with_security_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, html = read_url(f"{gateway.url}/")
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["content-type"])
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertIn("default-src 'self'", headers["content-security-policy"])
                self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertIn('<script src="/assets/app.js" defer></script>', html)
                self.assertIn('<link rel="stylesheet" href="/assets/app.css">', html)
                self.assertIn('id="mobile-access-qr"', html)
                self.assertIn('id="mobile-access-url"', html)
                self.assertIn('data-action="refresh-mobile-access"', html)
                self.assertIn('data-action="copy-mobile-url"', html)
                self.assertIn('id="gateway-token"', html)
                self.assertIn('id="gateway-token-kind"', html)
                self.assertIn('id="pair-expires-at"', html)
                self.assertIn('id="pairing-state"', html)
                self.assertIn('token temporário de pareamento', html)
                self.assertIn('Checklist mobile', html)
                self.assertIn('id="check-access"', html)
                self.assertIn('id="check-session"', html)
                self.assertIn('id="check-run"', html)
                self.assertIn('id="check-model"', html)
                self.assertIn('lai-gateway-daily --show-pair', html)
                self.assertIn('data-action="use-gateway-token"', html)
                self.assertIn('data-action="forget-gateway-token"', html)
                self.assertIn('id="readiness-pill"', html)
                self.assertIn('id="alpha-output"', html)
                self.assertIn('data-action="refresh-alpha-readiness"', html)
                self.assertIn("Alpha técnico", html)
                self.assertIn('id="external-expansion-output"', html)
                self.assertIn('data-action="refresh-external-expansion-gate"', html)
                self.assertIn("Expansão externa", html)
                self.assertIn('id="objective-output"', html)
                self.assertIn('data-action="refresh-objective-state"', html)
                self.assertIn("Objetivo local", html)
                self.assertIn('id="action-proposal-output"', html)
                self.assertIn('data-action="refresh-action-proposal"', html)
                self.assertIn("Proposta de ação", html)
                self.assertIn('id="approval-inbox-output"', html)
                self.assertIn('data-action="refresh-approval-inbox"', html)
                self.assertIn('data-action="enqueue-approval-inbox"', html)
                self.assertIn("Caixa de aprovação", html)
                self.assertIn('id="memory-output"', html)
                self.assertIn('data-action="refresh-memory-context"', html)
                self.assertIn('data-action="remember-memory-context"', html)
                self.assertIn("Memória local", html)
                self.assertIn('id="ops-pill"', html)
                self.assertIn('id="onboarding-pill"', html)
                self.assertIn('id="onboarding-output"', html)
                self.assertIn('data-action="refresh-onboarding"', html)
                self.assertIn("Primeiros passos", html)
                self.assertIn('id="health-summary"', html)
                self.assertIn('Saúde ainda não carregada.', html)
                self.assertIn('id="health-output"', html)
                self.assertIn('id="health-telegram-result"', html)
                self.assertIn('data-action="refresh-health-report"', html)
                self.assertIn('data-action="send-health-report-telegram"', html)
                self.assertIn('Saúde', html)
                self.assertIn('id="ops-output"', html)
                self.assertIn('data-action="refresh-ops-status"', html)
                self.assertIn('id="active-session-pill"', html)
                self.assertIn('id="active-run-pill"', html)
                self.assertIn('id="model-pill"', html)
                self.assertIn('id="model-runtime-output"', html)
                self.assertIn('data-action="refresh-model-runtime"', html)
                self.assertIn('data-action="configure-model-runtime"', html)
                self.assertIn('id="mcp-pill"', html)
                self.assertIn('id="workbench-pill"', html)
                self.assertIn('LAI Workbench', html)
                self.assertIn('id="workbench-shell"', html)
                self.assertIn('clean-workbench-app', html)
                self.assertIn('clean-left-rail', html)
                self.assertIn('clean-chat-main', html)
                self.assertIn('data-action="open-vscode-folder"', html)
                self.assertIn('workbench-shell-layout', html)
                self.assertIn('workbench-sidebar', html)
                self.assertIn('workbench-chat-center', html)
                self.assertIn('workbench-review-column', html)
                self.assertIn('id="local-chat-thread"', html)
                self.assertIn('ops-drawer', html)
                self.assertIn('chat-shell-layout', html)
                self.assertIn('reference-chat-shell', html)
                self.assertIn('top-workbench-tabs', html)
                self.assertIn('data-ui-surface="chat"', html)
                self.assertIn('data-ui-surface="shell"', html)
                self.assertIn('data-ui-surface="files"', html)
                self.assertIn('session-list', html)
                self.assertIn('chat-input-dock', html)
                self.assertIn('id="local-run-card"', html)
                self.assertIn('Operações e diagnósticos', html)
                self.assertIn('id="local-workspace"', html)
                self.assertIn('id="local-model"', html)
                self.assertIn('id="local-run-mode"', html)
                self.assertIn('id="local-run-task"', html)
                self.assertIn('id="local-run-id"', html)
                self.assertIn('id="local-patch-sha"', html)
                self.assertIn('Três modos de operação do workbench local', html)
                self.assertIn('id="local-mode-flow"', html)
                self.assertIn('id="local-flow-observe"', html)
                self.assertIn('id="local-flow-work"', html)
                self.assertIn('id="local-flow-promote"', html)
                self.assertIn('id="local-next-step"', html)
                self.assertIn('id="local-run-summary"', html)
                self.assertIn('id="local-review-panel"', html)
                self.assertIn('id="local-review-apply-button"', html)
                self.assertIn('data-action="apply-current-local-review"', html)
                self.assertIn('data-action="discard-current-local-review"', html)
                self.assertIn('id="local-review-validation"', html)
                self.assertIn('id="local-review-diff"', html)
                self.assertIn('id="local-project-label"', html)
                self.assertIn('id="local-mode-label"', html)
                self.assertIn('id="local-status-label"', html)
                self.assertIn('Debug avançado', html)
                self.assertIn('debug-panel', html)
                self.assertIn('Enviar ao LAI', html)
                self.assertIn('id="local-send-button"', html)
                self.assertIn("Pressione Enter para enviar", html)
                self.assertIn("Shift+Enter para nova linha", html)
                self.assertIn('id="local-cancel-button"', html)
                self.assertIn('Sem run ativo', html)
                self.assertIn('Usar Observar', html)
                self.assertIn('Usar Trabalhar', html)
                self.assertIn('Usar Aplicar', html)
                self.assertIn('data-local-mode-preset="observe"', html)
                self.assertIn('data-local-mode-preset="work"', html)
                self.assertIn('data-local-mode-preset="promote"', html)
                self.assertIn('data-action="refresh-local-chat-contract"', html)
                self.assertIn('data-action="create-local-chat-run"', html)
                self.assertIn('data-action="get-local-chat-review"', html)
                self.assertIn('data-action="promote-local-chat-run"', html)
                self.assertIn('data-action="cancel-local-chat-run"', html)
                self.assertIn('value="implement"', html)
                self.assertIn('value="ci-fix"', html)
                self.assertIn('id="mcp-output"', html)
                self.assertIn('id="check-mcp"', html)
                self.assertIn('id="mcp-server"', html)
                self.assertIn('id="mcp-tool"', html)
                self.assertIn('data-action="refresh-mcp-status"', html)
                self.assertIn('data-action="refresh-mcp-tools"', html)
                self.assertIn('data-action="check-mcp-call-tool"', html)
                self.assertIn('data-action="issue-mcp-local-tool"', html)
                self.assertIn('data-action="run-mcp-local-tool"', html)
                self.assertIn('id="n8n-output"', html)
                self.assertIn('data-action="plan-n8n-local"', html)
                self.assertIn('data-action="issue-n8n-local-plan"', html)
                self.assertIn('data-action="inspect-n8n-local-plan"', html)
                self.assertIn('Broker MCP', html)
                self.assertIn('n8n local', html)
                self.assertIn('id="auth-banner"', html)
                self.assertIn('id="gateway-auth-result"', html)
                self.assertIn('Parear este celular', html)
                self.assertIn('data-action="get-run-events"', html)
                self.assertIn('data-action="poll-run"', html)
                self.assertIn('data-action="stop-polling"', html)
                self.assertIn('data-action="copy-run-output"', html)
                self.assertIn('data-action="clear-session"', html)
                self.assertIn('data-action="delete-session"', html)
                self.assertIn("Excluir sessão selecionada", html)
                self.assertIn('id="task-counter"', html)
                self.assertIn('data-preset="plan"', html)
                self.assertIn('data-preset="security"', html)
                self.assertIn('autocapitalize="none"', html)
                self.assertIn('id="run-events-output"', html)
                self.assertIn('Linha do tempo do run', html)
                self.assertIn('id="run-history"', html)
                self.assertIn('Governança', html)
                self.assertIn('id="governance-adapter"', html)
                self.assertIn('id="governance-capability"', html)
                self.assertIn('id="governance-action"', html)
                self.assertIn('id="governance-param"', html)
                self.assertIn('id="governance-summary"', html)
                self.assertIn('id="governance-pill"', html)
                self.assertIn('id="governance-output"', html)
                self.assertIn('id="permission-ux-summary"', html)
                self.assertIn('id="permission-ux-output"', html)
                self.assertIn('id="decision-output"', html)
                self.assertIn('id="policy-output"', html)
                self.assertIn('id="authorization-output"', html)
                self.assertIn('id="proposal-output"', html)
                self.assertIn('id="audit-events-output"', html)
                self.assertIn('id="dry-run-output"', html)
                self.assertIn('data-action="refresh-governance-chain"', html)
                self.assertIn('data-action="refresh-permission-ux"', html)
                self.assertIn('data-action="refresh-governance-decision"', html)
                self.assertIn('data-action="refresh-governance-policy"', html)
                self.assertIn('data-action="refresh-governance-authorization"', html)
                self.assertIn('data-action="refresh-governance-proposal"', html)
                self.assertIn('data-action="refresh-governance-audit"', html)
                self.assertIn('data-action="refresh-governance-dry-run"', html)
                self.assertIn('data-action="refresh-governance-capture"', html)
                self.assertIn('data-action="refresh-governance-validation"', html)
                self.assertIn('data-action="refresh-governance-effective"', html)
                self.assertIn('data-action="refresh-governance-dispatcher"', html)
                self.assertIn('data-action="dispatch-local-status"', html)
                self.assertIn('id="capture-output"', html)
                self.assertIn('id="validation-output"', html)
                self.assertIn('id="effective-output"', html)
                self.assertIn('id="dispatcher-output"', html)
                self.assertIn('Dry-run', html)
                self.assertIn('local_status', html)
                self.assertIn('Executar local_status seguro', html)
                self.assertNotIn(TOKEN, html)

    def test_gateway_serves_assets_without_external_dependencies_or_token_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                css_status, css_headers, css = read_url(f"{gateway.url}/assets/app.css")
                js_status, js_headers, js = read_url(f"{gateway.url}/assets/app.js")

        self.assertEqual(css_status, 200)
        self.assertIn("text/css", css_headers["content-type"])
        self.assertIn(".shell", css)
        self.assertIn(".mobile-access-card", css)
        self.assertIn(".qr", css)
        self.assertIn(".pill.running", css)
        self.assertIn(".history", css)
        self.assertIn("#run-events-output", css)
        self.assertIn(".mobile-guide", css)
        self.assertIn(".quick-grid", css)
        self.assertIn(".task-meta", css)
        self.assertIn(".check.ready", css)
        self.assertIn(".pill.warn", css)
        self.assertIn("touch-action", css)
        self.assertIn("max-width: 480px", css)
        self.assertIn(".warn-text", css)
        self.assertIn(".danger-text", css)
        self.assertIn("button.danger", css)
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("white-space: pre-wrap", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn(".callout.ready", css)
        self.assertIn(".health-summary", css)
        self.assertIn(".primary-actions", css)
        self.assertIn(".mode-flow", css)
        self.assertIn(".flow-step.ready", css)
        self.assertIn(".compact-output", css)
        self.assertIn(".workbench-topline", css)
        self.assertIn(".clean-shell-layout", css)
        self.assertIn(".clean-chat-header", css)
        self.assertIn(".clean-ops-drawer", css)
        self.assertIn(".compact-tools-grid", css)
        self.assertIn(".debug-panel", css)
        self.assertIn(".chat-composer", css)
        self.assertIn(".reference-chat-shell", css)
        self.assertIn(".chat-shell-layout", css)
        self.assertIn(".chat-left-rail", css)
        self.assertIn(".chat-main-pane", css)
        self.assertIn(".top-workbench-tabs", css)
        self.assertIn(".message-row", css)
        self.assertIn(".chat-input-dock", css)
        self.assertEqual(js_status, 200)
        self.assertIn("application/javascript", js_headers["content-type"])
        self.assertIn("/v1/gateway/mobile-access", js)
        self.assertIn("/v1/gateway/health-report", js)
        self.assertIn("/v1/gateway/health-report/telegram", js)
        self.assertIn("send-health-report-telegram", js)
        self.assertIn("/v1/gateway/ops-status", js)
        self.assertIn("/v1/gateway/model-status", js)
        self.assertIn("/v1/gateway/alpha-readiness", js)
        self.assertIn("refresh-alpha-readiness", js)
        self.assertIn("setAlphaReadiness", js)
        self.assertIn("/v1/gateway/external-expansion-gate", js)
        self.assertIn("refresh-external-expansion-gate", js)
        self.assertIn("setExternalExpansionGate", js)
        self.assertIn("external-expansion-output", js)
        self.assertIn("/v1/gateway/chat", js)
        self.assertIn("send-model-chat", js)
        self.assertIn("modelChatBody", js)
        self.assertIn("fallback local explícito", js)
        self.assertIn("/v1/gateway/model-plan", js)
        self.assertIn("/v1/gateway/model-files", js)
        self.assertIn("/v1/gateway/model-task", js)
        self.assertIn("/v1/gateway/model-eval", js)
        self.assertIn("/v1/gateway/model-runs", js)
        self.assertIn("/v1/gateway/memory-context", js)
        self.assertIn("memoryContextBody", js)
        self.assertIn("documentTextBody", js)
        self.assertIn("documentWorkbenchParams", js)
        self.assertIn("setDocumentWorkbench", js)
        self.assertIn("/v1/gateway/document-text-local", js)
        self.assertIn("/v1/gateway/document-workbench", js)
        self.assertIn("read-document-text-local", js)
        self.assertIn("refresh-document-workbench", js)
        self.assertIn("inspect-document-workbench", js)
        self.assertIn("remember-memory-context", js)
        self.assertIn("/v1/local-chat/contract", js)
        self.assertIn("/v1/local-chat/workspaces", js)
        self.assertIn("/v1/local-chat/models", js)
        self.assertIn("/v1/local-chat/runs", js)
        self.assertIn("promote-local-chat-run", js)
        self.assertIn("cancel-local-chat-run", js)
        self.assertIn("workspace_id: workspaceId", js)
        self.assertIn("LOCAL_MODE_PRESETS", js)
        self.assertIn("applyLocalModePreset", js)
        self.assertIn("data-local-mode-preset", js)
        self.assertIn("updateLocalModeFlow", js)
        self.assertIn("summarizeLocalChildTelemetry", js)
        self.assertIn("renderReviewPanel", js)
        self.assertIn("applyBlockersForReview", js)
        self.assertIn("apply-current-local-review", js)
        self.assertIn("open-vscode-folder", js)
        self.assertIn("vscode://fenatodev.lai-chat/open-folder", js)
        self.assertIn('event.key === "Enter"', js)
        self.assertIn("!event.shiftKey", js)
        self.assertIn("renderLocalChatEvents", js)
        self.assertIn("LAI trabalhando", js)
        self.assertIn("appendLocalChatTurn", js)
        self.assertIn("updateLocalRunCard", js)
        self.assertIn("discard-current-local-review", js)
        self.assertIn("Aplicar esta alteração revisada?", js)
        self.assertIn("localNextStepForRun", js)
        self.assertIn("workspace_child_summary", js)
        self.assertIn("local-run-summary", js)
        self.assertIn("localModeLabel", js)
        self.assertIn("localWorkspaceLabel", js)
        self.assertIn('setText("local-project-label"', js)
        self.assertIn('setText("local-status-label"', js)
        self.assertIn("updateLocalExecutionControls", js)
        self.assertIn("já existe um run local ativo", js)
        self.assertIn("Há um run ativo. Cancele ou aguarde antes de mudar o modo.", js)
        self.assertIn("clearLocalReviewState", js)
        self.assertIn("local-next-step", js)
        self.assertIn("/v1/harness/mcp/status", js)
        self.assertIn("/v1/harness/mcp/tools", js)
        self.assertIn("/v1/harness/mcp/policy-check", js)
        self.assertIn("/v1/gateway/mcp-local-tool", js)
        self.assertIn("/v1/gateway/n8n-local-plan", js)
        self.assertIn("issue-n8n-local-plan", js)
        self.assertIn("inspect-n8n-local-plan", js)
        self.assertIn("/v1/gateway/permission-decision", js)
        self.assertIn("/v1/gateway/permission-ux", js)
        self.assertIn("/v1/gateway/policy-eval", js)
        self.assertIn("/v1/gateway/authorization-record", js)
        self.assertIn("/v1/gateway/adapter-invocation-proposal", js)
        self.assertIn("/v1/gateway/audit-events", js)
        self.assertIn("/v1/gateway/adapter-dry-run", js)
        self.assertIn("/v1/gateway/authorization-capture-stub", js)
        self.assertIn("/v1/gateway/authorization-validation-gate", js)
        self.assertIn("/v1/gateway/effective-authorization", js)
        self.assertIn("/v1/gateway/adapter-dispatcher", js)
        self.assertIn("governanceQuery", js)
        self.assertIn("refreshGovernanceChain", js)
        self.assertIn("setGovernanceOutput", js)
        self.assertIn("setPermissionUx", js)
        self.assertIn("compactPermissionUxText", js)
        self.assertIn("refresh-governance-chain", js)
        self.assertIn("refresh-governance-dry-run", js)
        self.assertIn("refresh-governance-capture", js)
        self.assertIn("refresh-governance-validation", js)
        self.assertIn("refresh-governance-effective", js)
        self.assertIn("refresh-governance-dispatcher", js)
        self.assertIn("dispatch-local-status", js)
        self.assertIn("isSafeLocalStatusSelection", js)
        self.assertIn("governanceApprovedQuery", js)
        self.assertIn("local_status.status", js)
        self.assertIn("adapter-dry-run", js)
        self.assertIn("dry_run_executed", js)
        self.assertIn("adapter_dispatched", js)
        self.assertIn("dispatch_enabled", js)
        self.assertIn("effective_authorization", js)
        self.assertIn("setHealthReport", js)
        self.assertIn("healthSummaryText", js)
        self.assertIn("Todos os sistemas estão prontos", js)
        self.assertIn('setCallout("health-summary", healthSummaryText(payload), state)', js)
        self.assertIn('overall === "ready" && nextSteps === 0 ? "ready"', js)
        self.assertIn("setOpsStatus", js)
        self.assertIn("setMcpStatus", js)
        self.assertIn("mcpPolicyBody", js)
        self.assertIn("check-mcp-call-tool", js)
        self.assertIn("setModelStatus", js)
        self.assertIn("data:image/svg+xml", js)
        self.assertIn("setMobileQr", js)
        self.assertIn("copyMobileUrl", js)
        self.assertIn("currentBrowserUrl", js)
        self.assertIn("active_phone_url", js)
        self.assertIn("URL mobile do navegador atual", js)
        self.assertIn("/v1/harness/status", js)
        self.assertIn("/v1/harness/sessions", js)
        self.assertIn('method: "DELETE"', js)
        self.assertIn("/v1/harness/runs", js)
        self.assertIn("/events", js)
        self.assertIn("renderRunEvents", js)
        self.assertIn("fetchSelectedRunEvents", js)
        self.assertIn("get-run-events", js)
        self.assertIn("lastRunEventsPayload", js)
        self.assertIn("run.control_run_id || run.run_id", js)
        self.assertIn("window.setInterval", js)
        self.assertIn("window.clearInterval", js)
        self.assertIn("navigator.clipboard.writeText", js)
        self.assertIn("replaceChildren", js)
        self.assertIn("textContent", js)
        self.assertIn("READ_ONLY_MODES", js)
        self.assertIn("gatewayAccessToken", js)
        self.assertIn("gatewayTokenKind", js)
        self.assertIn("sessionExpiresAt", js)
        self.assertIn("renderSessionCountdown", js)
        self.assertIn("updateGatewayAuthState", js)
        self.assertIn("parseSessionExpiresAt", js)
        self.assertIn("Pareie este celular primeiro", js)
        self.assertIn("Sessão mobile", js)
        self.assertIn("isLoopbackHost", js)
        self.assertIn("showPairRequiredOutputs", js)
        self.assertIn("setAuthBanner", js)
        self.assertIn("TASK_PRESETS", js)
        self.assertIn("applyPreset", js)
        self.assertIn("updateTaskCounter", js)
        self.assertIn("setCheck", js)
        self.assertIn("clearSession", js)
        self.assertIn("stop-polling", js)
        self.assertIn("button[data-preset]", js)
        self.assertIn("Authorization", js)
        self.assertIn("/v1/gateway/mobile-session", js)
        self.assertIn("revokeMobileSessionIfLoaded", js)
        for forbidden in (TOKEN, "localStorage", "sessionStorage", "innerHTML", "http://", "https://"):
            self.assertNotIn(forbidden, js)



    def test_gateway_mcp_ui_routes_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/harness/mcp/status")
                tools_status, _tool_headers, tools_body = read_url(f"{gateway.url}/v1/harness/mcp/tools")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        tools = json.loads(tools_body)
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertEqual(tools_status, 200)
        self.assertEqual(tools["execution_enabled"], False)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)
        self.assertNotIn(TOKEN, tools_body)
        self.assertNotIn("Bearer", tools_body)


    def test_gateway_mcp_local_tool_endpoint_is_governed_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/mcp-local-tool?mcp_action=plan")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "mcp-local-tool")
        self.assertEqual(payload["schema_version"], "mcp-local-tool/v1")
        self.assertEqual(payload["requested_capability"], "mcp.local_echo_digest")
        self.assertFalse(payload["local_tool_executed"])
        self.assertFalse(payload["security"]["calls_upstream_mcp"])
        self.assertFalse(payload["security"]["broad_mcp_tool_execution"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_n8n_local_plan_endpoint_is_governed_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/n8n-local-plan?n8n_action=plan")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "n8n-local-plan")
        self.assertEqual(payload["schema_version"], "n8n-local-plan/v1")
        self.assertEqual(payload["requested_capability"], "n8n.local_plan_digest")
        self.assertFalse(payload["local_plan_inspected"])
        self.assertFalse(payload["workflow_executed"])
        self.assertFalse(payload["workflow_activated"])
        self.assertFalse(payload["webhook_called"])
        self.assertFalse(payload["calls_n8n_instance"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_n8n_local_plan_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/n8n-local-plan?n8n_action=plan")
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/n8n-local-plan?n8n_action=plan",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "n8n-local-plan")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_gateway_permission_ux_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            query = "adapter_id=local_status&capability=local_status.status&approve=true&approved_by=workbench&operation_scope=local-status-read"
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/permission-ux?{query}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "permission-ux")
        self.assertEqual(payload["schema_version"], "permission-ux/v1")
        self.assertEqual(payload["stage_count"], 8)
        self.assertTrue(payload["effective"]["effective_authorization"])
        self.assertFalse(payload["grant"]["issued"])
        self.assertFalse(payload["grant"]["consumed"])
        self.assertFalse(payload["execution"]["adapter_executed"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


    def test_gateway_objective_state_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            (workspace / ".lai").mkdir(parents=True)
            (workspace / ".lai" / "objective-state.json").write_text(json.dumps({
                "schema_version": "objective-state/v1",
                "project_id": "lai-gateway",
                "objective": "Alpha operacional local",
                "tasks": [{"id": "t1", "title": "Ler estado", "status": "todo"}],
            }), encoding="utf-8")
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/objective-state?workspace_root={quote(str(workspace))}"
                )
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "objective-state")
        self.assertEqual(payload["schema_version"], "objective-state/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["implicit_ingestion"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)



    def test_gateway_approval_inbox_endpoint_is_sanitized_and_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            query = (
                f"workspace_root={quote(str(workspace))}&inbox_action=enqueue"
                "&domain=project&channel=workbench&autonomy=high"
                "&capability=approval-inbox&target=.lai/approval-inbox.jsonl"
                "&action=record%20pending%20approval&data=proposal%20fields&effect=record%20only&risk=low"
            )
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/approval-inbox?{query}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "approval-inbox")
        self.assertEqual(payload["schema_version"], "approval-inbox/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["data_touched"]["filesystem_write"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["uses_credentials"])
        self.assertFalse(payload["security"]["sends_messages"])
        self.assertFalse(payload["security"]["publishes"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_approval_inbox_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/approval-inbox?workspace_root={quote(str(workspace))}"
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(url)
                status, _headers, body = read_url(
                    url,
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "approval-inbox")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)


    def test_gateway_action_proposal_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            query = (
                f"workspace_root={quote(str(workspace))}"
                "&domain=project&channel=workbench&autonomy=high"
                "&capability=action-proposal&target=docs/product/action_proposal.md"
                "&action=prepare%20proposal&data=explicit%20fields&effect=render%20only&risk=low"
            )
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/action-proposal?{query}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "action-proposal")
        self.assertEqual(payload["schema_version"], "action-proposal/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["effective_authorization"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["implicit_ingestion"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_external_expansion_gate_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/external-expansion-gate")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "external-expansion-gate")
        self.assertEqual(payload["schema_version"], "external-expansion-gate/v1")
        self.assertFalse(payload["external_expansion_allowed"])
        self.assertFalse(payload["external_capabilities_enabled"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


    def test_private_objective_state_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/objective-state?workspace_root={quote(str(workspace))}"
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(url)
                status, _headers, body = read_url(
                    url,
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "objective-state")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)


    def test_private_action_proposal_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/action-proposal?workspace_root={quote(str(workspace))}&domain=project&channel=workbench&autonomy=none&capability=action-proposal&target=x&action=x&data=x&effect=x&risk=low"
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(url)
                status, _headers, body = read_url(
                    url,
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "action-proposal")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_private_external_expansion_gate_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/external-expansion-gate")
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/external-expansion-gate",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "external-expansion-gate")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_private_permission_ux_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            query = "adapter_id=local_status&capability=local_status.status"
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/permission-ux?{query}")
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/permission-ux?{query}",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "permission-ux")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_private_mcp_local_tool_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/mcp-local-tool?mcp_action=plan")
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/mcp-local-tool?mcp_action=plan",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "mcp-local-tool")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_gateway_mobile_access_endpoint_returns_local_qr_without_tokens(self) -> None:
        fake_access = {
            "operation": "mobile-access",
            "qr_svg": "<svg></svg>",
            "security": {"qr_contains_token": False},
        }
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch("lai_gateway.server.collect_mobile_access", return_value=fake_access) as mocked_collect:
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/mobile-access")
        mocked_collect.assert_called_once()
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = __import__("json").loads(body)
        self.assertEqual(payload["operation"], "mobile-access")
        self.assertIn("qr_svg", payload)
        self.assertIn("<svg", payload["qr_svg"])
        self.assertFalse(payload["security"]["qr_contains_token"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


    def test_gateway_ops_status_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/ops-status")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "ops-status")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_health_and_ops_endpoints_do_not_force_loopback_mobile_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            health_payload = {
                "operation": "health-report",
                "overall": "warn",
                "starts_server": False,
                "modifies_files": False,
                "checks": {"mcp_broker": "ready"},
                "security": {
                    "prints_tokens": False,
                    "prints_pairing_secret": False,
                    "prints_chat_reference": False,
                },
            }
            ops_payload = {
                "operation": "ops-status",
                "overall": "warn",
                "starts_server": False,
                "modifies_files": False,
                "security": {"prints_tokens": False},
            }
            with patch("lai_gateway.server.collect_health_report", return_value=health_payload) as health, patch(
                "lai_gateway.server.collect_ops_status", return_value=ops_payload
            ) as ops:
                with RunningGateway(config) as gateway:
                    read_url(f"{gateway.url}/v1/gateway/health-report")
                    read_url(f"{gateway.url}/v1/gateway/ops-status")

        self.assertIsNone(health.call_args.kwargs["mobile_candidate_ip"])
        self.assertIsNone(health.call_args.kwargs["mobile_port"])
        self.assertIsNone(ops.call_args.kwargs["mobile_candidate_ip"])
        self.assertIsNone(ops.call_args.kwargs["mobile_port"])

    def test_gateway_onboarding_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/onboarding")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "onboarding")
        self.assertEqual(payload["schema_version"], "onboarding-next-steps/v1")
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertFalse(payload["security"]["prints_paths"])
        self.assertFalse(payload["security"]["starts_server"])
        self.assertFalse(payload["security"]["modifies_files"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertIn("next_steps", payload)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn(str(token_file), body)
        self.assertNotIn("Bearer", body)

    def test_gateway_health_report_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/health-report")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "health-report")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertFalse(payload["security"]["prints_pairing_secret"])
        self.assertFalse(payload["security"]["prints_chat_reference"])
        self.assertIn("mcp_broker", payload["checks"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)
        self.assertNotIn("chat_id", body)

    def test_gateway_health_report_telegram_endpoint_is_explicit_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch("lai_gateway.server.send_telegram_message", return_value={"ok": True, "message_id": 88}) as send:
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(
                        f"{gateway.url}/v1/gateway/health-report/telegram",
                        method="POST",
                    )
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "health-report-telegram-notify")
        self.assertEqual(payload["telegram_notify"]["message_id"], 88)
        self.assertEqual(payload["health_report"]["operation"], "health-report")
        send.assert_called_once()
        self.assertIn("lai-gateway health-report:", send.call_args.kwargs["text"])
        self.assertNotIn(TOKEN, body + send.call_args.kwargs["text"])
        self.assertNotIn("Bearer", body + send.call_args.kwargs["text"])
        self.assertNotIn("chat_id", body + send.call_args.kwargs["text"])

    def test_gateway_health_report_telegram_requires_empty_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch("lai_gateway.server.send_telegram_message") as send:
                with RunningGateway(config) as gateway:
                    try:
                        read_url(
                            f"{gateway.url}/v1/gateway/health-report/telegram",
                            data=b"{}",
                            method="POST",
                        )
                    except Exception as exc:
                        self.assertIn("HTTP Error 400", str(exc))
        send.assert_not_called()

    def test_private_health_report_telegram_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            access = create_gateway_access_token(access_file, include_token=True)["token"]
            create_gateway_pairing_token(pair_file, ttl_seconds=600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with patch("lai_gateway.server.send_telegram_message", return_value={"ok": True, "message_id": 89}):
                with RunningGateway(config) as gateway:
                    try:
                        read_url(f"{gateway.url}/v1/gateway/health-report/telegram", method="POST")
                    except Exception as exc:
                        self.assertIn("HTTP Error 401", str(exc))
                    status, _headers, body = read_url(
                        f"{gateway.url}/v1/gateway/health-report/telegram",
                        headers={"Authorization": f"Bearer {access}"},
                        method="POST",
                    )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "health-report-telegram-notify")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("chat_id", body)

    def test_private_ops_status_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            access = create_gateway_access_token(access_file, include_token=True)["token"]
            create_gateway_pairing_token(pair_file, ttl_seconds=600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                try:
                    read_url(f"{gateway.url}/v1/gateway/ops-status")
                except Exception as exc:
                    self.assertIn("HTTP Error 401", str(exc))
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/ops-status",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "ops-status")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_private_health_report_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            access = create_gateway_access_token(access_file, include_token=True)["token"]
            create_gateway_pairing_token(pair_file, ttl_seconds=600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                try:
                    read_url(f"{gateway.url}/v1/gateway/health-report")
                except Exception as exc:
                    self.assertIn("HTTP Error 401", str(exc))
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/health-report",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "health-report")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("chat_id", body)

    def test_gateway_model_status_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-status")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = __import__("json").loads(body)
        self.assertEqual(payload["operation"], "model-status")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertFalse(payload["network_calls"]["local_openai_probe"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_chat_endpoint_is_direct_secret_free_and_does_not_touch_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch("lai_gateway.server.collect_model_chat") as collect:
                collect.return_value = {
                    "operation": "model-chat",
                    "overall": "ready",
                    "message": "resposta direta",
                    "starts_server": False,
                    "modifies_files": False,
                    "downloads_models": False,
                    "security": {
                        "prints_tokens": False,
                        "executes_tools": False,
                        "creates_harness_run": False,
                        "echoes_user_prompt": False,
                    },
                }
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(
                        f"{gateway.url}/v1/gateway/chat",
                        data=json.dumps({
                            "message": "mensagem comum",
                            "timeout_seconds": 5,
                            "max_tokens": 128,
                        }).encode("utf-8"),
                        method="POST",
                    )
        collect.assert_called_once_with(prompt="mensagem comum", timeout_seconds=5.0, max_tokens=128)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "model-chat")
        self.assertFalse(payload["security"]["creates_harness_run"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertNotIn("mensagem comum", body)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


    def test_gateway_model_task_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch("lai_gateway.server.collect_model_task") as collect:
                collect.return_value = {
                    "operation": "model-task",
                    "overall": "ready",
                    "task": "code-mini",
                    "starts_server": False,
                    "modifies_files": False,
                    "downloads_models": False,
                }
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-task?task=code-mini&timeout_seconds=5")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "model-task")
        self.assertEqual(payload["overall"], "ready")
        collect.assert_called_once_with(task="code-mini", timeout_seconds=5.0)
        self.assertNotIn("Bearer", body)
        self.assertNotIn(TOKEN, body)

    def test_gateway_model_eval_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                with patch("lai_gateway.server.collect_model_eval") as collect:
                    collect.return_value = {
                        "operation": "model-eval",
                        "overall": "ready",
                        "starts_server": False,
                        "modifies_files": False,
                        "downloads_models": False,
                        "security": {"prints_tokens": False, "stores_prompts": False},
                    }
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-eval?timeout_seconds=5")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "model-eval")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        collect.assert_called_once_with(timeout_seconds=5.0)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_model_eval_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/model-eval")
                with patch("lai_gateway.server.collect_model_eval") as collect:
                    collect.return_value = {"operation": "model-eval", "overall": "ready"}
                    status, _headers, body = read_url(
                        f"{gateway.url}/v1/gateway/model-eval",
                        headers={"Authorization": f"Bearer {access}"},
                    )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "model-eval")
        self.assertNotIn(access, body)

    def test_gateway_model_runs_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            runs_file = Path(tmp) / "model-runs.jsonl"
            runs_file.write_text(
                '{"operation":"model-task","overall":"ready","task":"code-mini","elapsed_ms":12.5,"response_preview":"ok"}\n',
                encoding="utf-8",
            )
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch.dict(os.environ, {"LAI_GATEWAY_MODEL_RUNS_FILE": str(runs_file)}, clear=False):
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-runs?limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "model-runs")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertEqual(payload["count"], 1)
        self.assertFalse(payload["security"]["stores_prompts"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_memory_context_endpoint_is_scoped_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/memory-context?context_kind=project&project_id=lai-gateway&limit=5"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "memory-context")
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["security"]["memory_grants_authority"])
        self.assertFalse(payload["security"]["grants_permission"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_document_text_local_endpoint_is_restricted_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            base = Path(tmp)
            token_file = base / "token"
            workspace = base / "workspace"
            workspace.mkdir()
            (workspace / "doc.md").write_text("# Doc\ntexto local", encoding="utf-8")
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            body = json.dumps({
                "workspace_root": str(workspace),
                "relative_path": "doc.md",
                "max_chars": 100,
            }).encode("utf-8")
            with RunningGateway(config) as gateway:
                status, headers, body_text = read_url(
                    f"{gateway.url}/v1/gateway/document-text-local",
                    data=body,
                    method="POST",
                )
        payload = json.loads(body_text)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "document-text-local")
        self.assertEqual(payload["overall"], "ready")
        self.assertIn("texto local", payload["document"]["text_preview"])
        self.assertTrue(payload["security"]["untrusted_content"])
        self.assertFalse(payload["security"]["grants_permission"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["supports_pdf"])
        self.assertNotIn(TOKEN, body_text)
        self.assertNotIn("Bearer", body_text)


    def test_gateway_alpha_readiness_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/alpha-readiness")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "alpha-readiness")
        self.assertEqual(payload["schema_version"], "alpha-readiness/v1")
        self.assertFalse(payload["publication_allowed"])
        self.assertTrue(payload["human_publication_approval_required"])
        self.assertFalse(payload["tag_or_release_created"])
        self.assertFalse(payload["security"]["publishes_release"])
        self.assertFalse(payload["security"]["creates_tag"])
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_gateway_document_workbench_endpoint_lists_metadata_only_and_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "readme.md").write_text("visible but not listed as content", encoding="utf-8")
            (workspace / "blocked.pdf").write_bytes(b"%PDF")
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/document-workbench?workspace_root={workspace}&max_results=10"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "document-workbench")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["limits"]["metadata_only_selection"])
        self.assertFalse(payload["limits"]["recursive_listing"])
        self.assertFalse(payload["security"]["external_upload"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertEqual([item["relative_path"] for item in payload["documents"]], ["readme.md"])
        self.assertIsNone(payload["inspection"])
        self.assertNotIn("visible but not listed as content", body)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_model_runs_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/model-runs")
                status, _headers, body = read_url(
                    f"{gateway.url}/v1/gateway/model-runs",
                    headers={"Authorization": f"Bearer {access}"},
                )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "model-runs")
        self.assertNotIn(access, body)

    def test_gateway_model_files_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            model_dir = Path(tmp) / "models"
            model_dir.mkdir()
            (model_dir / "local-code-q4_k_m.gguf").write_bytes(b"model")
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch.dict(os.environ, {"LAI_GATEWAY_MODEL_PATHS": str(model_dir)}, clear=False):
                with RunningGateway(config) as gateway:
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-files?max_results=5")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "model-files")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertEqual(payload["recommended"]["name"], "local-code-q4_k_m")
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)
    def test_private_gateway_chat_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            pair_file = Path(tmp) / "pair-token.json"
            access = create_gateway_access_token(access_file, include_token=True)["token"]
            create_gateway_pairing_token(pair_file, ttl_seconds=600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            body = json.dumps({"message": "mensagem privada"}).encode("utf-8")
            with RunningGateway(config) as gateway:
                try:
                    read_url(f"{gateway.url}/v1/gateway/chat", data=body, method="POST")
                except Exception as exc:
                    self.assertIn("HTTP Error 401", str(exc))
                with patch("lai_gateway.server.collect_model_chat") as collect:
                    collect.return_value = {"operation": "model-chat", "overall": "ready", "message": "ok"}
                    status, _headers, response_body = read_url(
                        f"{gateway.url}/v1/gateway/chat",
                        headers={"Authorization": f"Bearer {access}"},
                        data=body,
                        method="POST",
                    )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(response_body)["operation"], "model-chat")
        self.assertNotIn(access, response_body)
        self.assertNotIn(TOKEN, response_body)
        self.assertNotIn("mensagem privada", response_body)


    def test_private_onboarding_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/onboarding")
                with patch("lai_gateway.server.collect_onboarding_status") as collect:
                    collect.return_value = {"operation": "onboarding", "overall": "ready", "security": {"prints_tokens": False}}
                    status, _headers, body = read_url(
                        f"{gateway.url}/v1/gateway/onboarding",
                        headers={"Authorization": f"Bearer {access}"},
                    )
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["operation"], "onboarding")
        self.assertNotIn(access, body)
        self.assertNotIn(TOKEN, body)

    def test_private_model_task_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as unauth:
                    read_url(f"{gateway.url}/v1/gateway/model-task?task=code-mini")
                with patch("lai_gateway.server.collect_model_task") as collect:
                    collect.return_value = {"operation": "model-task", "overall": "ready"}
                    status, _headers, body = read_url(
                        f"{gateway.url}/v1/gateway/model-task?task=code-mini",
                        headers={"Authorization": f"Bearer {access}"},
                    )
        payload = json.loads(body)
        self.assertEqual(unauth.exception.code, 401)
        self.assertEqual(status, 200)
        self.assertEqual(payload["operation"], "model-task")
        collect.assert_called_once()
        self.assertNotIn(access, body)

    def test_private_model_files_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access_file.write_text("gateway-access-secret-value-1234567890", encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as ctx:
                    read_url(f"{gateway.url}/v1/gateway/model-files")
        self.assertEqual(ctx.exception.code, 401)


    def test_gateway_public_browser_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                with patch("lai_gateway.server.collect_public_browser") as collect:
                    collect.return_value = {
                        "operation": "public-browser",
                        "schema_version": "public-browser-read/v1",
                        "overall": "ready_to_fetch",
                        "fetch_attempted": False,
                        "network_calls": False,
                        "security": {"uses_cookies": False, "executes_javascript": False, "downloads_files": False},
                    }
                    url = quote("https://example.com/docs", safe="")
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/public-browser?url={url}&browser_action=plan")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "public-browser")
        collect.assert_called_once()
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_public_browser_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as ctx:
                    read_url(f"{gateway.url}/v1/gateway/public-browser?url=https%3A%2F%2Fexample.com%2F")
        self.assertEqual(ctx.exception.code, 401)

    def test_gateway_model_runtime_endpoint_is_configurable_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                with patch("lai_gateway.server.collect_model_runtime") as collect:
                    collect.return_value = {
                        "operation": "model-runtime",
                        "schema_version": "model-runtime/v1",
                        "overall": "warn",
                        "security": {"prints_tokens": False},
                    }
                    status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-runtime?runtime_action=diagnose&probe_openai=1")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "model-runtime")
        collect.assert_called_once()
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_model_runtime_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access = "gateway-access-secret-value-1234567890"
            access_file.write_text(access, encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as ctx:
                    read_url(f"{gateway.url}/v1/gateway/model-runtime")
        self.assertEqual(ctx.exception.code, 401)

    def test_gateway_model_plan_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/model-plan")
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = __import__("json").loads(body)
        self.assertEqual(payload["operation"], "model-plan")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertIn("commands", payload)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_private_model_status_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access_file.write_text("gateway-access-secret-value-1234567890", encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as ctx:
                    read_url(f"{gateway.url}/v1/gateway/model-status")
        self.assertEqual(ctx.exception.code, 401)

    def test_private_model_plan_requires_gateway_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            access_file = Path(tmp) / "access-token"
            access_file.write_text("gateway-access-secret-value-1234567890", encoding="utf-8")
            access_file.chmod(0o600)
            pair_file = Path(tmp) / "pair-token.json"
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                bind="127.0.0.1",
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                with self.assertRaises(__import__("urllib.error").error.HTTPError) as ctx:
                    read_url(f"{gateway.url}/v1/gateway/model-plan")
        self.assertEqual(ctx.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
