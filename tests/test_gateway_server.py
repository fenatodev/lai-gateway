from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lai_gateway.config import GatewayConfig
from lai_gateway.server import GatewayHTTPServer

from .fake_harness import TOKEN, fake_harness, get_json


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


class GatewayServerTest(unittest.TestCase):
    def test_gateway_exposes_read_only_harness_contract_status_and_readiness(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                self.assertEqual(get_json(f"{gateway.url}/healthz")["product"], "lai-gateway")
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/gateway-contract")["version"],
                    "0.4.2",
                )
                self.assertEqual(get_json(f"{gateway.url}/v1/harness/status")["ok"], True)
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/readiness")["overall"],
                    "ready",
                )
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/sessions?limit=5")["sessions"][0]["session_id"],
                    "s_test",
                )
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/sessions/s_test")["session"]["session_id"],
                    "s_test",
                )

    def test_gateway_creates_sessions_without_exposing_runs(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                request = Request(f"{gateway.url}/v1/harness/sessions", data=None, method="POST")
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, HTTPStatus.CREATED)
                self.assertEqual(payload["session"]["session_id"], "s_test")

                bad_request = Request(f"{gateway.url}/v1/harness/sessions", data=b"{}", method="POST")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(bad_request, timeout=5)
                self.assertEqual(caught.exception.code, HTTPStatus.BAD_REQUEST)

                with self.assertRaises(HTTPError) as caught:
                    urlopen(f"{gateway.url}/v1/harness/sessions?limit=0", timeout=5)
                self.assertEqual(caught.exception.code, HTTPStatus.BAD_REQUEST)

    def test_gateway_mvp_does_not_expose_run_creation(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                request = Request(f"{gateway.url}/v1/runs", data=b"{}", method="POST")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, HTTPStatus.METHOD_NOT_ALLOWED)


if __name__ == "__main__":
    unittest.main()
