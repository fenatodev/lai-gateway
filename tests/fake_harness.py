from __future__ import annotations

import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.request import Request, urlopen

from .fixtures import CONTRACT

TOKEN = "test-token"
LAST_RUN_BODY: dict[str, Any] | None = None
LOCAL_CHAT_LAST_BODY: dict[str, Any] | None = None
LOCAL_CHAT_CSRF = "csrf-test-token"
MCP_SECRET_LEAK = False



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
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.7", "ok": True})
            return
        if self.path == "/v1/readiness":
            self._send(HTTPStatus.OK, {"overall": "ready", "version": "0.4.7"})
            return
        if self.path == "/v1/mcp/status":
            payload: dict[str, Any] = {
                "product": "lai harness",
                "version": "0.4.7",
                "overall": "ready",
                "server_count": 1,
                "servers": [{"name": "desktop-commander", "status": "configured"}],
                "security": {"executes_tools": False},
                "issues": [],
            }
            if MCP_SECRET_LEAK or os.environ.get("LAI_FAKE_HARNESS_LEAK_MCP_SECRET") == "1":
                payload["authorization"] = "Bearer leaked-harness-token"
                payload["servers"][0]["env"] = {
                    "LAI_GATEWAY_MODEL_API_KEY": "leaked-model-secret",
                    "NORMAL_SETTING": "safe",
                }
            self._send(HTTPStatus.OK, payload)
            return
        if self.path == "/v1/mcp/tools":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.4.7",
                "overall": "ready",
                "server_count": 1,
                "execution_enabled": False,
                "servers": [{
                    "name": "desktop-commander",
                    "status": "configured",
                    "tool_count": 2,
                    "tools": ["read_file", "start_process"],
                }],
                "security": {"executes_tools": False},
            })
            return
        if self.path == "/v1/local-chat/contract?client_version=1":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "schema_version": 1,
                "client_version": 1,
                "negotiated": True,
                "security": {"csrf_header": "X-LAI-CSRF", "csrf_token": LOCAL_CHAT_CSRF},
                "capabilities": {
                    "local_chat": True,
                    "local_chat_read_only_runs": True,
                    "local_chat_work_runs": True,
                    "source_repository_write": False,
                    "mcp_tool_execution": False,
                },
                "workspace_selection": {"current_workspace_id": "lw-1234567890abcdef"},
            })
            return
        if self.path == "/v1/local-chat/workspaces?client_version=1":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "schema_version": 1,
                "workspaces": [{
                    "workspace_id": "lw-1234567890abcdef",
                    "display_name": "fake-harness",
                    "branch": "main",
                    "git_clean": True,
                    "source_checkout_write": False,
                }],
            })
            return
        if self.path == "/v1/local-chat/models?client_version=1&workspace_id=lw-1234567890abcdef":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "schema_version": 1,
                "workspace_id": "lw-1234567890abcdef",
                "models": [{"model_id": "default", "available": True, "api_key_exposed": False}],
            })
            return
        if self.path == "/v1/local-chat/runs/cr-1234567890abcdef/events?client_version=1&cursor=0":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "control_run_id": "cr-1234567890abcdef",
                "status": "succeeded",
                "terminal": True,
                "cursor": 2,
                "events": [{"event": "queued", "status": "queued"}, {"event": "finished", "status": "succeeded"}],
            })
            return
        if self.path == "/v1/local-chat/runs/cr-1234567890abcdef/review?client_version=1&workspace_id=lw-1234567890abcdef":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "control_run_id": "cr-1234567890abcdef",
                "workspace_id": "lw-1234567890abcdef",
                "review": {
                    "status": "ready",
                    "changed_paths": ["src/app.py"],
                    "patch_sha256": "a" * 64,
                    "promotion_available": True,
                    "source_checkout_write": False,
                },
            })
            return
        if self.path.startswith("/v1/sessions?"):
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "sessions": [{"session_id": "cs-1234567890abcdef", "turn_count": 0, "workspace_path": "/home/example/private/repo/.lai", "note": "safe relative src/app.py"}]})
            return
        if self.path.startswith("/v1/runs?"):
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "runs": [{"run_id": "cr-1234567890abcdef", "status": "queued", "mode": "plan", "metrics_file": "/home/example/private/.local/metrics.jsonl"}]})
            return
        if self.path == "/v1/runs/cr-1234567890abcdef":
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "run": {"control_run_id": "cr-1234567890abcdef", "status": "succeeded", "mode": "plan", "audit_file": "/home/example/private/.local/audit.jsonl"}})
            return
        if self.path == "/v1/runs/cr-1234567890abcdef/events":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.4.7",
                "control_run_id": "cr-1234567890abcdef",
                "mode": "plan",
                "status": "succeeded",
                "terminal": True,
                "repository": "/home/example/private/repo",
                "stdout": "leaked fake response",
                "task": "leaked task text",
                "events": [
                    {"event": "queued", "status": "queued", "at": "2026-09-07T00:00:00Z"},
                    {"event": "started", "status": "running", "at": "2026-09-07T00:00:01Z", "details": {"stderr": "leaked stderr"}},
                    {"event": "finished", "status": "succeeded", "at": "2026-09-07T00:00:02Z", "details": {"output_truncated": False}},
                ],
            })
            return
        if self.path == "/v1/sessions/cs-1234567890abcdef":
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "session": {"session_id": "cs-1234567890abcdef", "turn_count": 0, "turns": [], "cwd": "/home/example/private/repo"}})
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_DELETE(self) -> None:  # noqa: N802
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "auth_required"})
            return
        if self.path == "/v1/sessions/cs-1234567890abcdef":
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.4.7",
                "session": {"session_id": "cs-1234567890abcdef", "deleted": True, "turn_count": 0},
            })
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        global LAST_RUN_BODY
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "auth_required"})
            return
        if self.path == "/v1/local-chat/runs":
            global LOCAL_CHAT_LAST_BODY
            if self.headers.get("X-LAI-CSRF") != LOCAL_CHAT_CSRF:
                self._send(HTTPStatus.FORBIDDEN, {"error": "csrf_required"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            LOCAL_CHAT_LAST_BODY = json.loads(self.rfile.read(length).decode("utf-8"))
            self._send(HTTPStatus.ACCEPTED, {
                "product": "lai harness",
                "version": "0.5.0",
                "run": {
                    "control_run_id": "cr-1234567890abcdef",
                    "status": "queued",
                    "mode": LOCAL_CHAT_LAST_BODY.get("mode"),
                    "workspace_id": LOCAL_CHAT_LAST_BODY.get("workspace_id"),
                    "model_id": LOCAL_CHAT_LAST_BODY.get("model_id"),
                },
            })
            return
        if self.path == "/v1/local-chat/runs/cr-1234567890abcdef/promotion":
            if self.headers.get("X-LAI-CSRF") != LOCAL_CHAT_CSRF:
                self._send(HTTPStatus.FORBIDDEN, {"error": "csrf_required"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            self._send(HTTPStatus.OK, {
                "product": "lai harness",
                "version": "0.5.0",
                "promotion": {
                    "status": "promoted",
                    "workspace_id": body.get("workspace_id"),
                    "patch_sha256": body.get("patch_sha256"),
                    "source_checkout_write": False,
                    "push_performed": False,
                },
            })
            return
        if self.path == "/v1/local-chat/runs/cr-1234567890abcdef/lifecycle":
            if self.headers.get("X-LAI-CSRF") != LOCAL_CHAT_CSRF:
                self._send(HTTPStatus.FORBIDDEN, {"error": "csrf_required"})
                return
            self._send(HTTPStatus.OK, {"product": "lai harness", "version": "0.5.0", "lifecycle": {"action": "cancel", "accepted": True}})
            return
        if self.path == "/v1/sessions":
            self._send(HTTPStatus.CREATED, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "session": {"session_id": "cs-1234567890abcdef", "turn_count": 0, "turns": [], "cwd": "/home/example/private/repo"}})
            return
        if self.path == "/v1/mcp/policy-check":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            operation = str(body.get("operation") or "").strip()
            server = str(body.get("server") or "").strip()
            tool = body.get("tool") if isinstance(body.get("tool"), str) else None
            if operation not in {"status", "list-tools", "call-tool"}:
                response = {"decision": "DENY", "reason": "unsupported MCP operation"}
            elif operation != "status" and not server:
                response = {"decision": "DENY", "reason": "MCP server is required"}
            elif operation == "call-tool":
                response = {
                    "decision": "DENY",
                    "reason": "MCP tool execution is not enabled in this foundation milestone",
                }
            else:
                response = {
                    "decision": "ALLOW",
                    "reason": f"MCP {operation} is read-only and does not execute external tools",
                }
            response.update({
                "product": "lai harness",
                "version": "0.4.7",
                "operation": operation,
                "executed": False,
                "server": server or None,
                "tool": tool,
            })
            self._send(HTTPStatus.OK, response)
            return
        if self.path == "/v1/runs":
            length = int(self.headers.get("Content-Length", "0"))
            LAST_RUN_BODY = json.loads(self.rfile.read(length).decode("utf-8"))
            self._send(HTTPStatus.ACCEPTED, {"product": "lai harness", "version": "0.4.7", "repository": "/home/example/private/repo", "run": {"control_run_id": "cr-1234567890abcdef", "status": "queued", "mode": LAST_RUN_BODY.get("mode"), "session_id": LAST_RUN_BODY.get("session_id"), "workspace_path": "/home/example/private/work"}})
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
