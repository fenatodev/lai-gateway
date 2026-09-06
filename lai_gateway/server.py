from __future__ import annotations

import hmac
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import __version__
from .access import collect_mobile_access
from .ops import collect_ops_status
from .config import GatewayConfig, read_gateway_access_token, validate_gateway_bind
from .tokens import read_valid_gateway_pairing_token
from .errors import ConfigError, GatewayError, HarnessHTTPError
from .harness_client import READ_ONLY_RUN_MODES, HarnessClient, build_read_only_run_body
from .model import collect_model_files, collect_model_plan, collect_model_status

_REQUEST_BODY_MAX_BYTES = 64 * 1024
_AUTH_FAILURE_LIMIT = 5
_AUTH_FAILURE_WINDOW_SECONDS = 60.0
_STATIC_DIR = Path(__file__).with_name("static")
_STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
    "/assets/app.js": ("app.js", "application/javascript; charset=utf-8"),
}
_CSP = (
    "default-src 'self'; "
    "connect-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'none'"
)


class GatewayHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], config: GatewayConfig):
        validate_gateway_bind(server_address[0], private_bind_enabled=config.private_bind_enabled)
        if config.private_bind_enabled:
            if config.access_token_file is None:
                raise ConfigError("private bind requires a gateway access token file")
            access_token = read_gateway_access_token(config.access_token_file)
        else:
            access_token = None
        super().__init__(server_address, GatewayHandler)
        self.config = config
        self.client = HarnessClient(config)
        self.access_token = access_token
        self.pair_token_file = config.pair_token_file if config.private_bind_enabled else None
        self.auth_failures: dict[str, list[float]] = {}
        self.auth_lock = threading.Lock()


class GatewayHandler(BaseHTTPRequestHandler):
    server: GatewayHTTPServer

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if self._serve_static(parsed.path):
            return
        if parsed.path == "/healthz":
            self._send_json(HTTPStatus.OK, {"ok": True, "product": "lai-gateway", "version": __version__})
            return
        if parsed.path == "/v1/gateway/mobile-access":
            self._send_json(HTTPStatus.OK, collect_mobile_access(port=self.server.server_address[1], bind=self.server.server_address[0]))
            return
        if parsed.path == "/v1/gateway/model-status":
            if not self._authorize_gateway_api(parsed.path):
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            probe = values.get("probe_openai", ["0"])[0] in {"1", "true", "yes", "on"}
            self._send_json(HTTPStatus.OK, collect_model_status(probe_openai=probe))
            return
        if parsed.path == "/v1/gateway/model-plan":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._send_json(HTTPStatus.OK, collect_model_plan())
            return
        if parsed.path == "/v1/gateway/model-files":
            if not self._authorize_gateway_api(parsed.path):
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            max_results = self._positive_int_query(values.get("max_results", ["10"])[0], default=10, maximum=50)
            if max_results is None:
                return
            self._send_json(HTTPStatus.OK, collect_model_files(max_results=max_results, max_seconds=12.0))
            return
        if parsed.path == "/v1/gateway/ops-status":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._send_json(
                HTTPStatus.OK,
                collect_ops_status(
                    config=self.server.config,
                    mobile_candidate_ip=self.server.server_address[0],
                    mobile_port=self.server.server_address[1],
                ),
            )
            return
        if parsed.path == "/v1/harness/status":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.status())
            return
        if parsed.path == "/v1/harness/readiness":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.readiness())
            return
        if parsed.path == "/v1/harness/gateway-contract":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.gateway_contract())
            return
        if parsed.path == "/v1/harness/sessions":
            if not self._authorize_gateway_api(parsed.path):
                return
            limit = self._limit_from_query(parsed.query)
            if limit is None:
                return
            self._proxy(lambda: self.server.client.list_sessions(limit))
            return
        if parsed.path.startswith("/v1/harness/sessions/"):
            if not self._authorize_gateway_api(parsed.path):
                return
            session_id = parsed.path.removeprefix("/v1/harness/sessions/")
            if "/" in session_id or not session_id:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._proxy(lambda: self.server.client.get_session(session_id))
            return
        if parsed.path == "/v1/harness/runs":
            if not self._authorize_gateway_api(parsed.path):
                return
            limit = self._limit_from_query(parsed.query)
            if limit is None:
                return
            self._proxy(lambda: self.server.client.list_runs(limit))
            return
        if parsed.path.startswith("/v1/harness/runs/"):
            if not self._authorize_gateway_api(parsed.path):
                return
            run_id = parsed.path.removeprefix("/v1/harness/runs/")
            if "/" in run_id or not run_id:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._proxy(lambda: self.server.client.get_run(run_id))
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/v1/harness/sessions":
            if not self._authorize_gateway_api(parsed.path):
                return
            if not self._require_empty_body():
                return
            self._proxy(lambda: self.server.client.create_session(), success=HTTPStatus.CREATED)
            return
        if parsed.path == "/v1/harness/runs":
            if not self._authorize_gateway_api(parsed.path):
                return
            body = self._read_run_body()
            if body is None:
                return
            self._proxy(
                lambda: self.server.client.create_read_only_run(
                    mode=body["mode"],
                    task=body["task"],
                    session_id=body.get("session_id"),
                ),
                success=HTTPStatus.ACCEPTED,
            )
            return
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"error": "run_creation_not_exposed_in_gateway_mvp"},
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "delete_not_supported"})

    def _serve_static(self, path: str) -> bool:
        route = _STATIC_ROUTES.get(path)
        if route is None:
            return False
        filename, content_type = route
        try:
            data = (_STATIC_DIR / filename).read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "static_asset_missing"})
            return True
        self._send_bytes(HTTPStatus.OK, data, content_type)
        return True


    def _authorize_gateway_api(self, path: str) -> bool:
        if not (path.startswith("/v1/harness/") or path in {"/v1/gateway/ops-status", "/v1/gateway/model-status", "/v1/gateway/model-plan", "/v1/gateway/model-files"}):
            return True
        expected = self.server.access_token
        if expected is None:
            return True
        client_key = self.client_address[0] if self.client_address else "unknown"
        if self._auth_rate_limited(client_key):
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "gateway_auth_rate_limited"})
            return False
        raw = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not raw.startswith(prefix):
            self._record_auth_failure(client_key)
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "gateway_auth_required"})
            return False
        supplied = raw[len(prefix) :]
        if hmac.compare_digest(supplied, expected):
            self._clear_auth_failures(client_key)
            return True
        pair_token = self._current_pairing_token()
        if pair_token is not None and hmac.compare_digest(supplied, pair_token):
            self._clear_auth_failures(client_key)
            return True
        self._record_auth_failure(client_key)
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "gateway_auth_failed"})
        return False

    def _current_pairing_token(self) -> str | None:
        token_file = self.server.pair_token_file
        if token_file is None:
            return None
        try:
            return read_valid_gateway_pairing_token(token_file)
        except GatewayError:
            return None

    def _auth_rate_limited(self, client_key: str) -> bool:
        now = time.monotonic()
        with self.server.auth_lock:
            recent = [
                stamp for stamp in self.server.auth_failures.get(client_key, [])
                if now - stamp < _AUTH_FAILURE_WINDOW_SECONDS
            ]
            self.server.auth_failures[client_key] = recent
            return len(recent) >= _AUTH_FAILURE_LIMIT

    def _record_auth_failure(self, client_key: str) -> None:
        now = time.monotonic()
        with self.server.auth_lock:
            recent = [
                stamp for stamp in self.server.auth_failures.get(client_key, [])
                if now - stamp < _AUTH_FAILURE_WINDOW_SECONDS
            ]
            recent.append(now)
            self.server.auth_failures[client_key] = recent

    def _clear_auth_failures(self, client_key: str) -> None:
        with self.server.auth_lock:
            self.server.auth_failures.pop(client_key, None)

    def _proxy(self, call: Any, success: int | HTTPStatus = HTTPStatus.OK) -> None:
        try:
            payload = call()
        except HarnessHTTPError as exc:
            self._send_json(exc.status, {"error": "harness_http_error", "status": exc.status})
        except GatewayError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": "gateway_error", "message": str(exc)})
        else:
            self._send_json(success, payload)

    def _limit_from_query(self, query: str) -> int | None:
        values = parse_qs(query, keep_blank_values=True)
        raw_values = values.get("limit", ["20"])
        if len(raw_values) != 1:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_limit"})
            return None
        try:
            limit = int(raw_values[0])
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_limit"})
            return None
        if not 1 <= limit <= 100:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_limit"})
            return None
        return limit

    def _positive_int_query(self, raw: str, *, default: int, maximum: int, error_name: str = "value") -> int | None:
        try:
            value = int(raw or str(default))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_{error_name}"})
            return None
        if not 1 <= value <= maximum:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_{error_name}"})
            return None
        return value

    def _require_empty_body(self) -> bool:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return False
        if length != 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "request_body_not_supported"})
            return False
        return True

    def _read_run_body(self) -> dict[str, str] | None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return None
        if length <= 0 or length > _REQUEST_BODY_MAX_BYTES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request_body_size"})
            return None
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return None
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json_object"})
            return None
        allowed_keys = {"mode", "task", "session_id"}
        if set(payload) - allowed_keys:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "unsupported_run_fields"})
            return None
        mode = payload.get("mode")
        task = payload.get("task")
        session_id = payload.get("session_id")
        if not isinstance(mode, str) or not isinstance(task, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_run_body"})
            return None
        if session_id is not None and not isinstance(session_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_run_body"})
            return None
        if mode not in READ_ONLY_RUN_MODES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "write_mode_not_allowed"})
            return None
        try:
            return build_read_only_run_body(mode=mode, task=task, session_id=session_id)
        except ConfigError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_run_body", "message": str(exc)})
            return None

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", _CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Vary", "Authorization")

    def _send_json(self, status: int | HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self._send_bytes(status, data, "application/json; charset=utf-8")

    def _send_bytes(self, status: int | HTTPStatus, data: bytes, content_type: str) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self._security_headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(config: GatewayConfig) -> None:
    with GatewayHTTPServer((config.bind, config.port), config) as httpd:
        print(f"lai-gateway listening on http://{config.bind}:{config.port}", flush=True)
        httpd.serve_forever()
