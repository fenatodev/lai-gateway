from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import __version__
from .config import GatewayConfig, validate_loopback_bind
from .errors import GatewayError, HarnessHTTPError
from .harness_client import HarnessClient


class GatewayHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], config: GatewayConfig):
        validate_loopback_bind(server_address[0])
        super().__init__(server_address, GatewayHandler)
        self.config = config
        self.client = HarnessClient(config)


class GatewayHandler(BaseHTTPRequestHandler):
    server: GatewayHTTPServer

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send_json(HTTPStatus.OK, {"ok": True, "product": "lai-gateway", "version": __version__})
            return
        if self.path == "/v1/harness/status":
            self._proxy(lambda: self.server.client.status())
            return
        if self.path == "/v1/harness/readiness":
            self._proxy(lambda: self.server.client.readiness())
            return
        if self.path == "/v1/harness/gateway-contract":
            self._proxy(lambda: self.server.client.gateway_contract())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"error": "run_creation_not_exposed_in_gateway_mvp"},
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "delete_not_supported"})

    def _proxy(self, call: Any) -> None:
        try:
            payload = call()
        except HarnessHTTPError as exc:
            self._send_json(exc.status, {"error": "harness_http_error", "status": exc.status})
        except GatewayError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": "gateway_error", "message": str(exc)})
        else:
            self._send_json(HTTPStatus.OK, payload)

    def _send_json(self, status: int | HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(config: GatewayConfig) -> None:
    with GatewayHTTPServer((config.bind, config.port), config) as httpd:
        print(f"lai-gateway listening on http://{config.bind}:{config.port}", flush=True)
        httpd.serve_forever()
