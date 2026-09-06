from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.config import GatewayConfig
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


def read_url(url: str) -> tuple[int, dict[str, str], str]:
    with urlopen(Request(url, headers={"Accept": "*/*"}), timeout=5) as response:
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
                self.assertIn('id="gateway-token"', html)
                self.assertIn('id="gateway-token-kind"', html)
                self.assertIn('id="pair-expires-at"', html)
                self.assertIn('id="pairing-state"', html)
                self.assertIn('temporary pair token', html)
                self.assertIn('lai-gateway pair create --ttl-seconds 600 --show', html)
                self.assertIn('data-action="use-gateway-token"', html)
                self.assertIn('data-action="forget-gateway-token"', html)
                self.assertIn('data-action="refresh-token-countdown"', html)
                self.assertIn('id="readiness-pill"', html)
                self.assertIn('id="active-session-pill"', html)
                self.assertIn('id="active-run-pill"', html)
                self.assertIn('data-action="poll-run"', html)
                self.assertIn('data-action="copy-run-output"', html)
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
        self.assertIn(".pill.running", css)
        self.assertIn(".history", css)
        self.assertIn(".warn-text", css)
        self.assertIn(".danger-text", css)
        self.assertEqual(js_status, 200)
        self.assertIn("application/javascript", js_headers["content-type"])
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
        self.assertIn("Authorization", js)
        for forbidden in (TOKEN, "localStorage", "sessionStorage", "innerHTML", "http://", "https://"):
            self.assertNotIn(forbidden, js)


if __name__ == "__main__":
    unittest.main()
