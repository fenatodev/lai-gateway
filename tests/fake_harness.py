from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.request import Request, urlopen

from .fixtures import CONTRACT

TOKEN = "test-token"


class FakeHarnessHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "auth_required"})
            return
        if self.path == "/v1/gateway-contract":
            self._send(HTTPStatus.OK, CONTRACT)
            return
        if self.path == "/v1/status":
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.2", "ok": True})
            return
        if self.path == "/v1/readiness":
            self._send(HTTPStatus.OK, {"overall": "ready", "version": "0.4.2"})
            return
        if self.path.startswith("/v1/sessions?"):
            self._send(HTTPStatus.OK, {"sessions": []})
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "auth_required"})
            return
        if self.path == "/v1/sessions":
            self._send(HTTPStatus.CREATED, {"session_id": "s_test", "turns": []})
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def _send(self, status: int | HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class RunningServer:
    def __init__(self, server: ThreadingHTTPServer):
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "RunningServer":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def fake_harness() -> RunningServer:
    return RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), FakeHarnessHandler))


def get_json(url: str) -> dict[str, Any]:
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
