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


def post_json(url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def post_json_error(url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body
    raise AssertionError("expected HTTPError")


class GatewayServerTest(unittest.TestCase):
    def _config(self, tmp: str, harness_url: str) -> GatewayConfig:
        token_file = Path(tmp) / "token"
        token_file.write_text(TOKEN, encoding="utf-8")
        return GatewayConfig(harness_url=harness_url, token_file=token_file)

    def test_gateway_exposes_read_only_harness_contract_status_and_readiness(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                self.assertEqual(get_json(f"{gateway.url}/healthz")["product"], "lai-gateway")
                contract = get_json(f"{gateway.url}/v1/harness/gateway-contract")
                self.assertEqual(contract["version"], "0.4.2")
                self.assertEqual(get_json(f"{gateway.url}/v1/harness/status")["ok"], True)
                readiness = get_json(f"{gateway.url}/v1/harness/readiness")
                self.assertEqual(readiness["overall"], "ready")

    def test_gateway_creates_sessions_without_exposing_runs(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                listed = get_json(f"{gateway.url}/v1/harness/sessions?limit=5")
                self.assertEqual(listed["sessions"][0]["session_id"], "s_test")

                request = Request(f"{gateway.url}/v1/harness/sessions", data=None, method="POST")
                with urlopen(request, timeout=5) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, HTTPStatus.CREATED)
                self.assertEqual(body["session"]["session_id"], "s_test")
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/sessions/s_test")["session"]["session_id"],
                    "s_test",
                )

    def test_gateway_creates_only_read_only_runs(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                listed = get_json(f"{gateway.url}/v1/harness/runs?limit=5")
                self.assertEqual(listed["runs"][0]["control_run_id"], "cr_test")

                status, created = post_json(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "plan", "task": "Summarize.", "session_id": "s_test"},
                )
                self.assertEqual(status, HTTPStatus.ACCEPTED)
                self.assertEqual(created["run"]["control_run_id"], "cr_test")
                fetched = get_json(f"{gateway.url}/v1/harness/runs/cr_test")
                self.assertEqual(fetched["run"]["status"], "succeeded")

    def test_gateway_blocks_write_modes_and_malformed_run_bodies(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                status, body = post_json_error(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "implement", "task": "change files"},
                )
                self.assertEqual(status, HTTPStatus.BAD_REQUEST)
                self.assertEqual(body["error"], "invalid_run_request")

                status, body = post_json_error(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "plan", "task": "x", "surprise": True},
                )
                self.assertEqual(status, HTTPStatus.BAD_REQUEST)
                self.assertEqual(body["error"], "unknown_run_fields")

    def test_gateway_mvp_does_not_expose_raw_run_creation(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                request = Request(f"{gateway.url}/v1/runs", data=b"{}", method="POST")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, HTTPStatus.METHOD_NOT_ALLOWED)


if __name__ == "__main__":
    unittest.main()
