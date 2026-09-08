from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
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
                self.assertIn('temporary pair token', html)
                self.assertIn('Mobile checklist', html)
                self.assertIn('id="check-access"', html)
                self.assertIn('id="check-session"', html)
                self.assertIn('id="check-run"', html)
                self.assertIn('id="check-model"', html)
                self.assertIn('lai-gateway-daily --show-pair', html)
                self.assertIn('data-action="use-gateway-token"', html)
                self.assertIn('data-action="forget-gateway-token"', html)
                self.assertIn('id="readiness-pill"', html)
                self.assertIn('id="ops-pill"', html)
                self.assertIn('id="health-output"', html)
                self.assertIn('id="health-telegram-result"', html)
                self.assertIn('data-action="refresh-health-report"', html)
                self.assertIn('data-action="send-health-report-telegram"', html)
                self.assertIn('Health Report', html)
                self.assertIn('id="ops-output"', html)
                self.assertIn('data-action="refresh-ops-status"', html)
                self.assertIn('id="active-session-pill"', html)
                self.assertIn('id="active-run-pill"', html)
                self.assertIn('id="model-pill"', html)
                self.assertIn('id="mcp-pill"', html)
                self.assertIn('id="mcp-output"', html)
                self.assertIn('id="check-mcp"', html)
                self.assertIn('id="mcp-server"', html)
                self.assertIn('id="mcp-tool"', html)
                self.assertIn('data-action="refresh-mcp-status"', html)
                self.assertIn('data-action="refresh-mcp-tools"', html)
                self.assertIn('data-action="check-mcp-call-tool"', html)
                self.assertIn('MCP Broker', html)
                self.assertIn('id="auth-banner"', html)
                self.assertIn('id="gateway-auth-result"', html)
                self.assertIn('Pair this phone', html)
                self.assertIn('data-action="get-run-events"', html)
                self.assertIn('data-action="poll-run"', html)
                self.assertIn('data-action="stop-polling"', html)
                self.assertIn('data-action="copy-run-output"', html)
                self.assertIn('data-action="clear-session"', html)
                self.assertIn('data-action="delete-session"', html)
                self.assertIn("Delete selected session", html)
                self.assertIn('id="task-counter"', html)
                self.assertIn('data-preset="plan"', html)
                self.assertIn('data-preset="security"', html)
                self.assertIn('autocapitalize="none"', html)
                self.assertIn('id="run-events-output"', html)
                self.assertIn('Run timeline', html)
                self.assertIn('id="run-history"', html)
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
        self.assertIn("touch-action", css)
        self.assertIn("max-width: 480px", css)
        self.assertIn(".warn-text", css)
        self.assertIn(".danger-text", css)
        self.assertIn("button.danger", css)
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("white-space: pre-wrap", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn(".callout.ready", css)
        self.assertIn(".primary-actions", css)
        self.assertEqual(js_status, 200)
        self.assertIn("application/javascript", js_headers["content-type"])
        self.assertIn("/v1/gateway/mobile-access", js)
        self.assertIn("/v1/gateway/health-report", js)
        self.assertIn("/v1/gateway/health-report/telegram", js)
        self.assertIn("send-health-report-telegram", js)
        self.assertIn("/v1/gateway/ops-status", js)
        self.assertIn("/v1/gateway/model-status", js)
        self.assertIn("/v1/gateway/model-plan", js)
        self.assertIn("/v1/gateway/model-files", js)
        self.assertIn("/v1/gateway/model-task", js)
        self.assertIn("/v1/gateway/model-eval", js)
        self.assertIn("/v1/gateway/model-runs", js)
        self.assertIn("/v1/harness/mcp/status", js)
        self.assertIn("/v1/harness/mcp/tools", js)
        self.assertIn("/v1/harness/mcp/policy-check", js)
        self.assertIn("setHealthReport", js)
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
        self.assertIn("mobile current browser URL", js)
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
        self.assertIn("Pair this phone first", js)
        self.assertIn("Mobile session", js)
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

    def test_gateway_mobile_access_endpoint_returns_local_qr_without_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/mobile-access")
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
