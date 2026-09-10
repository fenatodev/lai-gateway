from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import __version__
from .access import collect_mobile_access
from .health import collect_health_report, render_health_report
from .ops import collect_ops_status
from .config import GatewayConfig, read_gateway_access_token, validate_gateway_bind
from .tokens import read_valid_gateway_pairing_token
from .errors import ConfigError, GatewayError, HarnessHTTPError
from .harness_client import (
    LOCAL_CHAT_RUN_MODES,
    READ_ONLY_RUN_MODES,
    HarnessClient,
    build_read_only_run_body,
    is_control_run_id,
    is_control_session_id,
)
from .model import collect_model_eval, collect_model_files, collect_model_plan, collect_model_runs, collect_model_status, collect_model_task
from .telegram import send_telegram_message

_REQUEST_BODY_MAX_BYTES = 64 * 1024
_AUTH_FAILURE_LIMIT = 5
_AUTH_FAILURE_WINDOW_SECONDS = 60.0
_MOBILE_SESSION_TTL_SECONDS = 8 * 60 * 60
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
        self.mobile_sessions: dict[str, float] = {}
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
        if parsed.path == "/v1/gateway/model-task":
            if not self._authorize_gateway_api(parsed.path):
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            task = values.get("task", ["code-mini"])[0] or "code-mini"
            timeout = self._positive_float_query(values.get("timeout_seconds", ["60"])[0], default=60.0, maximum=120.0)
            if timeout is None:
                return
            self._send_json(HTTPStatus.OK, collect_model_task(task=task, timeout_seconds=timeout))
            return
        if parsed.path == "/v1/gateway/model-eval":
            if not self._authorize_gateway_api(parsed.path):
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            timeout = self._positive_float_query(values.get("timeout_seconds", ["60"])[0], default=60.0, maximum=120.0)
            if timeout is None:
                return
            self._send_json(HTTPStatus.OK, collect_model_eval(timeout_seconds=timeout))
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
        if parsed.path == "/v1/gateway/model-runs":
            if not self._authorize_gateway_api(parsed.path):
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            limit = self._positive_int_query(values.get("limit", ["20"])[0], default=20, maximum=100)
            if limit is None:
                return
            self._send_json(HTTPStatus.OK, collect_model_runs(limit=limit))
            return
        if parsed.path == "/v1/gateway/health-report":
            if not self._authorize_gateway_api(parsed.path):
                return
            payload = collect_health_report(
                config=self.server.config,
                mobile_candidate_ip=_mobile_candidate_from_server_bind(self.server.server_address[0]),
                mobile_port=None if _is_loopback_bind(self.server.server_address[0]) else self.server.server_address[1],
            )
            self._send_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/v1/gateway/ops-status":
            if not self._authorize_gateway_api(parsed.path):
                return
            payload = collect_ops_status(
                config=self.server.config,
                mobile_candidate_ip=_mobile_candidate_from_server_bind(self.server.server_address[0]),
                mobile_port=None if _is_loopback_bind(self.server.server_address[0]) else self.server.server_address[1],
            )
            self._attach_mobile_session_status(payload)
            self._send_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/v1/local-chat/contract":
            if not self._authorize_local_chat_api():
                return
            self._proxy(lambda: self.server.client.local_chat_contract())
            return
        if parsed.path == "/v1/local-chat/workspaces":
            if not self._authorize_local_chat_api():
                return
            self._proxy(lambda: self.server.client.local_chat_workspaces())
            return
        if parsed.path == "/v1/local-chat/models":
            if not self._authorize_local_chat_api():
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            workspace_id = values.get("workspace_id", [""])[0]
            self._proxy(lambda: self.server.client.local_chat_models(workspace_id))
            return
        local_events_match = re.fullmatch(r"/v1/local-chat/runs/(cr-[0-9a-f]{16})/events", parsed.path)
        if local_events_match:
            if not self._authorize_local_chat_api():
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            cursor = self._nonnegative_int_query(values.get("cursor", ["0"])[0], default=0, maximum=1000000, error_name="cursor")
            if cursor is None:
                return
            self._proxy(lambda: self.server.client.get_local_chat_events(local_events_match.group(1), cursor=cursor))
            return
        local_review_match = re.fullmatch(r"/v1/local-chat/runs/(cr-[0-9a-f]{16})/review", parsed.path)
        if local_review_match:
            if not self._authorize_local_chat_api():
                return
            values = parse_qs(parsed.query, keep_blank_values=True)
            workspace_id = values.get("workspace_id", [""])[0]
            self._proxy(lambda: self.server.client.get_local_chat_review(local_review_match.group(1), workspace_id))
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
        if parsed.path == "/v1/harness/mcp/status":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.mcp_status())
            return
        if parsed.path == "/v1/harness/mcp/tools":
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.mcp_tools())
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
            if "/" in session_id or not is_control_session_id(session_id):
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
        run_events_match = re.fullmatch(r"/v1/harness/runs/(cr-[0-9a-f]{16})/events", parsed.path)
        if run_events_match:
            if not self._authorize_gateway_api(parsed.path):
                return
            self._proxy(lambda: self.server.client.get_run_events(run_events_match.group(1)))
            return
        if parsed.path.startswith("/v1/harness/runs/"):
            if not self._authorize_gateway_api(parsed.path):
                return
            run_id = parsed.path.removeprefix("/v1/harness/runs/")
            if "/" in run_id or not is_control_run_id(run_id):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._proxy(lambda: self.server.client.get_run(run_id))
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/v1/gateway/mobile-session":
            if not self._require_empty_body():
                return
            self._exchange_mobile_session()
            return
        if parsed.path == "/v1/gateway/health-report/telegram":
            if not self._authorize_gateway_api(parsed.path):
                return
            if not self._require_empty_body():
                return
            payload = collect_health_report(
                config=self.server.config,
                mobile_candidate_ip=_mobile_candidate_from_server_bind(self.server.server_address[0]),
                mobile_port=None if _is_loopback_bind(self.server.server_address[0]) else self.server.server_address[1],
            )
            try:
                notify_payload = send_telegram_message(text=render_health_report(payload))
            except ConfigError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {
                    "error": "telegram_notify_failed",
                    "message": str(exc),
                    "sent": False,
                    "token_printed": False,
                    "token_included": False,
                    "webhook_exposed": False,
                })
                return
            self._send_json(HTTPStatus.OK, {
                "product": "lai-gateway",
                "version": __version__,
                "operation": "health-report-telegram-notify",
                "overall": "ready",
                "health_report": payload,
                "telegram_notify": {
                    "sent": True,
                    "ok": bool(notify_payload.get("ok", False)),
                    "message_id": notify_payload.get("message_id"),
                    "token_printed": False,
                    "token_included": False,
                    "webhook_exposed": False,
                },
            })
            return
        if parsed.path == "/v1/local-chat/runs":
            if not self._authorize_local_chat_api():
                return
            body = self._read_local_chat_run_body()
            if body is None:
                return
            self._proxy(
                lambda: self.server.client.create_local_chat_run(
                    mode=body["mode"],
                    task=body["task"],
                    workspace_id=body["workspace_id"],
                    model_id=body["model_id"],
                    session_id=body.get("session_id"),
                ),
                success=HTTPStatus.ACCEPTED,
            )
            return
        local_promotion_match = re.fullmatch(r"/v1/local-chat/runs/(cr-[0-9a-f]{16})/promotion", parsed.path)
        if local_promotion_match:
            if not self._authorize_local_chat_api():
                return
            body = self._read_promotion_body()
            if body is None:
                return
            self._proxy(
                lambda: self.server.client.promote_local_chat_run(
                    local_promotion_match.group(1),
                    workspace_id=body["workspace_id"],
                    patch_sha256=body["patch_sha256"],
                )
            )
            return
        local_lifecycle_match = re.fullmatch(r"/v1/local-chat/runs/(cr-[0-9a-f]{16})/lifecycle", parsed.path)
        if local_lifecycle_match:
            if not self._authorize_local_chat_api():
                return
            body = self._read_lifecycle_body()
            if body is None:
                return
            self._proxy(
                lambda: self.server.client.local_chat_lifecycle(
                    local_lifecycle_match.group(1),
                    action=body["action"],
                    workspace_id=body["workspace_id"],
                )
            )
            return
        if parsed.path == "/v1/harness/sessions":
            if not self._authorize_gateway_api(parsed.path):
                return
            if not self._require_empty_body():
                return
            self._proxy(lambda: self.server.client.create_session(), success=HTTPStatus.CREATED)
            return
        if parsed.path == "/v1/harness/mcp/policy-check":
            if not self._authorize_gateway_api(parsed.path):
                return
            body = self._read_mcp_policy_body()
            if body is None:
                return
            self._proxy(lambda: self.server.client.mcp_policy_check(
                operation=body["operation"] or "",
                server=body["server"],
                tool=body["tool"],
            ))
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
        parsed = urlparse(self.path)
        if parsed.path == "/v1/gateway/mobile-session":
            self._revoke_mobile_session()
            return
        if parsed.path.startswith("/v1/harness/sessions/"):
            if not self._authorize_gateway_api(parsed.path):
                return
            session_id = parsed.path.removeprefix("/v1/harness/sessions/")
            if "/" in session_id or not is_control_session_id(session_id):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._proxy(lambda: self.server.client.delete_session(session_id))
            return
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


    def _authorize_local_chat_api(self) -> bool:
        if self.server.config.private_bind_enabled:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "local_chat_loopback_only"})
            return False
        client_host = self.client_address[0] if self.client_address else ""
        if client_host not in {"127.0.0.1", "::1"}:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "local_chat_client_loopback_only"})
            return False
        if not _is_loopback_http_host(self.headers.get("Host", "")):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "local_chat_host_loopback_only"})
            return False
        origin = self.headers.get("Origin")
        if origin and not _is_loopback_http_origin(origin):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "local_chat_origin_loopback_only"})
            return False
        return True

    def _authorize_gateway_api(self, path: str) -> bool:
        protected_gateway_paths = {
            "/v1/gateway/health-report",
            "/v1/gateway/health-report/telegram",
            "/v1/gateway/ops-status",
            "/v1/gateway/model-status",
            "/v1/gateway/model-plan",
            "/v1/gateway/model-files",
            "/v1/gateway/model-task",
            "/v1/gateway/model-runs",
            "/v1/gateway/model-eval",
        }
        if not (path.startswith("/v1/harness/") or path in protected_gateway_paths):
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
        if self._is_valid_mobile_session(supplied):
            self._clear_auth_failures(client_key)
            return True
        self._record_auth_failure(client_key)
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "gateway_auth_failed"})
        return False

    def _exchange_mobile_session(self) -> None:
        expected = self.server.access_token
        if expected is None:
            self._send_json(HTTPStatus.OK, {
                "product": "lai-gateway",
                "version": __version__,
                "overall": "ready",
                "session_required": False,
            })
            return
        client_key = self.client_address[0] if self.client_address else "unknown"
        if self._auth_rate_limited(client_key):
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "gateway_auth_rate_limited"})
            return
        raw = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not raw.startswith(prefix):
            self._record_auth_failure(client_key)
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "gateway_auth_required"})
            return
        supplied = raw[len(prefix):]
        pair_token = self._current_pairing_token()
        used_pair_token = pair_token is not None and hmac.compare_digest(supplied, pair_token)
        if not (hmac.compare_digest(supplied, expected) or used_pair_token):
            self._record_auth_failure(client_key)
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "gateway_auth_failed"})
            return
        if used_pair_token:
            self._consume_pairing_token()
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + _MOBILE_SESSION_TTL_SECONDS
        digest = self._mobile_session_hash(token)
        with self.server.auth_lock:
            self._prune_mobile_sessions_locked(time.time())
            self.server.mobile_sessions[digest] = expires_at
        self._clear_auth_failures(client_key)
        self._send_json(HTTPStatus.CREATED, {
            "product": "lai-gateway",
            "version": __version__,
            "overall": "ready",
            "session_token": token,
            "token_type": "mobile_session",
            "expires_at": self._utc_timestamp(expires_at),
            "seconds_remaining": _MOBILE_SESSION_TTL_SECONDS,
            "stored": "server_memory_hash_only",
            "client_storage": "page_memory_only",
            "pair_token_consumed": used_pair_token,
        })

    def _revoke_mobile_session(self) -> None:
        expected = self.server.access_token
        if expected is None:
            self._send_json(HTTPStatus.OK, {
                "product": "lai-gateway",
                "version": __version__,
                "overall": "ready",
                "session_required": False,
                "revoked": False,
            })
            return
        client_key = self.client_address[0] if self.client_address else "unknown"
        if self._auth_rate_limited(client_key):
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "gateway_auth_rate_limited"})
            return
        raw = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not raw.startswith(prefix):
            self._record_auth_failure(client_key)
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "gateway_auth_required"})
            return
        supplied = raw[len(prefix):]
        if hmac.compare_digest(supplied, expected):
            self._clear_auth_failures(client_key)
            self._send_json(HTTPStatus.OK, {
                "product": "lai-gateway",
                "version": __version__,
                "overall": "ready",
                "revoked": False,
                "reason": "gateway_access_token_is_not_a_mobile_session",
            })
            return
        revoked = self._pop_mobile_session(supplied)
        if revoked:
            self._clear_auth_failures(client_key)
            self._send_json(HTTPStatus.OK, {
                "product": "lai-gateway",
                "version": __version__,
                "overall": "ready",
                "revoked": True,
                "stored": "server_memory_hash_only",
            })
            return
        self._record_auth_failure(client_key)
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "gateway_auth_failed"})

    def _is_valid_mobile_session(self, token: str) -> bool:
        if not token:
            return False
        now = time.time()
        digest = self._mobile_session_hash(token)
        with self.server.auth_lock:
            self._prune_mobile_sessions_locked(now)
            expires_at = self.server.mobile_sessions.get(digest)
            return bool(expires_at and expires_at > now)

    def _pop_mobile_session(self, token: str) -> bool:
        if not token:
            return False
        now = time.time()
        digest = self._mobile_session_hash(token)
        with self.server.auth_lock:
            self._prune_mobile_sessions_locked(now)
            return self.server.mobile_sessions.pop(digest, None) is not None

    def _attach_mobile_session_status(self, payload: dict[str, Any]) -> None:
        now = time.time()
        with self.server.auth_lock:
            self._prune_mobile_sessions_locked(now)
            active_count = len(self.server.mobile_sessions)
        payload["mobile_session"] = {
            "overall": "ready" if active_count else "none",
            "active_count": active_count,
            "ttl_seconds": _MOBILE_SESSION_TTL_SECONDS,
            "stored": "server_memory_hash_only",
            "client_storage": "page_memory_only",
            "prints_tokens": False,
        }
        if active_count and isinstance(payload.get("mobile"), dict):
            payload["mobile"]["active_mobile_session"] = True

    def _prune_mobile_sessions_locked(self, now: float) -> None:
        expired = [digest for digest, expires_at in self.server.mobile_sessions.items() if expires_at <= now]
        for digest in expired:
            self.server.mobile_sessions.pop(digest, None)

    @staticmethod
    def _mobile_session_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _utc_timestamp(epoch_seconds: float) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))

    def _current_pairing_token(self) -> str | None:
        token_file = self.server.pair_token_file
        if token_file is None:
            return None
        try:
            return read_valid_gateway_pairing_token(token_file)
        except GatewayError:
            return None

    def _consume_pairing_token(self) -> None:
        token_file = self.server.pair_token_file
        if token_file is None:
            return
        try:
            token_file.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return

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

    def _positive_float_query(self, raw: str, *, default: float, maximum: float) -> float | None:
        if raw == "":
            return default
        try:
            value = float(raw)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_float"})
            return None
        if not 0 < value <= maximum:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_float"})
            return None
        return value

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

    def _nonnegative_int_query(self, raw: str, *, default: int, maximum: int, error_name: str = "value") -> int | None:
        try:
            value = int(raw or str(default))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid_{error_name}"})
            return None
        if not 0 <= value <= maximum:
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

    def _read_body(self) -> bytes | None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return None
        if length <= 0 or length > _REQUEST_BODY_MAX_BYTES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request_body_size"})
            return None
        return self.rfile.read(length)

    def _read_json_object(
        self,
        *,
        allowed_keys: set[str] | None = None,
        unsupported_error: str = "unsupported_json_fields",
    ) -> dict[str, Any] | None:
        raw = self._read_body()
        if raw is None:
            return None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return None
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json_object"})
            return None
        if allowed_keys is not None and set(payload) - allowed_keys:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": unsupported_error})
            return None
        return payload

    def _read_mcp_policy_body(self) -> dict[str, str | None] | None:
        payload = self._read_json_object(
            allowed_keys={"operation", "server", "tool"},
            unsupported_error="unsupported_mcp_policy_fields",
        )
        if payload is None:
            return None
        operation = payload.get("operation")
        server = payload.get("server")
        tool = payload.get("tool")
        if not isinstance(operation, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_mcp_policy_body"})
            return None
        if server is not None and not isinstance(server, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_mcp_policy_body"})
            return None
        if tool is not None and not isinstance(tool, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_mcp_policy_body"})
            return None
        return {"operation": operation, "server": server, "tool": tool}

    def _read_local_chat_run_body(self) -> dict[str, str] | None:
        payload = self._read_json_object(
            allowed_keys={"mode", "task", "workspace_id", "model_id", "session_id"},
            unsupported_error="unsupported_local_chat_run_fields",
        )
        if payload is None:
            return None
        mode = payload.get("mode")
        task = payload.get("task")
        workspace_id = payload.get("workspace_id")
        model_id = payload.get("model_id", "default")
        session_id = payload.get("session_id")
        if not all(isinstance(value, str) for value in [mode, task, workspace_id, model_id]):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_local_chat_run_body"})
            return None
        if session_id is not None and not isinstance(session_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_local_chat_run_body"})
            return None
        if mode not in LOCAL_CHAT_RUN_MODES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "unsupported_local_chat_mode"})
            return None
        return {
            "mode": mode,
            "task": task,
            "workspace_id": workspace_id,
            "model_id": model_id,
            **({"session_id": session_id} if session_id else {}),
        }

    def _read_promotion_body(self) -> dict[str, str] | None:
        payload = self._read_json_object(
            allowed_keys={"workspace_id", "patch_sha256"},
            unsupported_error="unsupported_promotion_fields",
        )
        if payload is None:
            return None
        workspace_id = payload.get("workspace_id")
        patch_sha256 = payload.get("patch_sha256")
        if not isinstance(workspace_id, str) or not isinstance(patch_sha256, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_promotion_body"})
            return None
        return {"workspace_id": workspace_id, "patch_sha256": patch_sha256}

    def _read_lifecycle_body(self) -> dict[str, str] | None:
        payload = self._read_json_object(
            allowed_keys={"action", "workspace_id"},
            unsupported_error="unsupported_lifecycle_fields",
        )
        if payload is None:
            return None
        action = payload.get("action")
        workspace_id = payload.get("workspace_id")
        if not isinstance(workspace_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_lifecycle_body"})
            return None
        if action != "cancel":
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "unsupported_lifecycle_action"})
            return None
        return {"action": action, "workspace_id": workspace_id}

    def _read_run_body(self) -> dict[str, str] | None:
        payload = self._read_json_object(
            allowed_keys={"mode", "task", "session_id"},
            unsupported_error="unsupported_run_fields",
        )
        if payload is None:
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


def _is_loopback_bind(bind: str) -> bool:
    return bind in {"127.0.0.1", "localhost", "::1"}


def _mobile_candidate_from_server_bind(bind: str) -> str | None:
    return None if _is_loopback_bind(bind) else bind

def _is_loopback_http_host(raw: str) -> bool:
    host = raw.rsplit("@", 1)[-1].split(":", 1)[0].strip("[]").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _is_loopback_http_origin(raw: str) -> bool:
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    return parsed.scheme == "http" and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}


def serve(config: GatewayConfig) -> None:
    with GatewayHTTPServer((config.bind, config.port), config) as httpd:
        print(f"lai-gateway listening on http://{config.bind}:{config.port}", flush=True)
        httpd.serve_forever()
