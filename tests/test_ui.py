from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

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


def read_url(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
    request_headers = {"Accept": "*/*", **(headers or {})}
    with urlopen(Request(url, headers=request_headers), timeout=5) as response:
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
                self.assertIn('lai-gateway mobile-serve --show-pair', html)
                self.assertIn('lai-gateway pair create --ttl-seconds 600 --show', html)
                self.assertIn('data-action="use-gateway-token"', html)
                self.assertIn('data-action="forget-gateway-token"', html)
                self.assertIn('data-action="refresh-token-countdown"', html)
                self.assertIn('id="readiness-pill"', html)
                self.assertIn('id="ops-pill"', html)
                self.assertIn('id="ops-output"', html)
                self.assertIn('data-action="refresh-ops-status"', html)
                self.assertIn('id="active-session-pill"', html)
                self.assertIn('id="active-run-pill"', html)
                self.assertIn('data-action="poll-run"', html)
                self.assertIn('data-action="stop-polling"', html)
                self.assertIn('data-action="copy-run-output"', html)
                self.assertIn('data-action="clear-session"', html)
                self.assertIn('id="task-counter"', html)
                self.assertIn('data-preset="plan"', html)
                self.assertIn('data-preset="security"', html)
                self.assertIn('autocapitalize="none"', html)
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
        self.assertIn(".mobile-guide", css)
        self.assertIn(".quick-grid", css)
        self.assertIn(".task-meta", css)
        self.assertIn(".check.ready", css)
        self.assertIn("touch-action", css)
        self.assertIn("max-width: 480px", css)
        self.assertIn(".warn-text", css)
        self.assertIn(".danger-text", css)
        self.assertEqual(js_status, 200)
        self.assertIn("application/javascript", js_headers["content-type"])
        self.assertIn("/v1/gateway/mobile-access", js)
        self.assertIn("/v1/gateway/ops-status", js)
        self.assertIn("/v1/gateway/model-status", js)
        self.assertIn("/v1/gateway/model-plan", js)
        self.assertIn("setOpsStatus", js)
        self.assertIn("setModelStatus", js)
        self.assertIn("data:image/svg+xml", js)
        self.assertIn("setMobileQr", js)
        self.assertIn("copyMobileUrl", js)
        self.assertIn("/v1/harness/status", js)
        self.assertIn("/v1/harness/sessions", js)
        self.assertIn("/v1/harness/runs", js)
        self.assertIn("window.setInterval", js)
        self.assertIn("window.clearInterval", js)
        self.assertIn("navigator.clipboard.writeText", js)
        self.assertIn("replaceChildren", js)
        self.assertIn("textContent", js)
        self.assertIn("READ_ONLY_MODES", js)
        self.assertIn("gatewayAccessToken", js)
        self.assertIn("gatewayTokenKind", js)
        self.assertIn("pairExpiresAt", js)
        self.assertIn("renderPairCountdown", js)
        self.assertIn("updateGatewayAuthState", js)
        self.assertIn("parsePairExpiresAt", js)
        self.assertIn("TASK_PRESETS", js)
        self.assertIn("applyPreset", js)
        self.assertIn("updateTaskCounter", js)
        self.assertIn("setCheck", js)
        self.assertIn("clearSession", js)
        self.assertIn("stop-polling", js)
        self.assertIn("button[data-preset]", js)
        self.assertIn("Authorization", js)
        for forbidden in (TOKEN, "localStorage", "sessionStorage", "innerHTML", "http://", "https://"):
            self.assertNotIn(forbidden, js)


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
