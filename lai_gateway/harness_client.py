from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import GatewayConfig, read_control_token
from .contract import assert_no_secret_values, validate_gateway_contract
from .errors import ConfigError, HarnessHTTPError

MAX_RESPONSE_BYTES = 1024 * 1024
READ_ONLY_RUN_MODES = frozenset({"diagnose", "plan", "release", "review", "security"})
WORK_RUN_MODES = frozenset({"ci-fix", "fix", "implement", "refactor"})
LOCAL_CHAT_RUN_MODES = READ_ONLY_RUN_MODES | WORK_RUN_MODES
MAX_TASK_CHARS = 12000
MAX_LOCAL_CHAT_TASK_CHARS = 12000
LOCAL_WORKSPACE_ID_RE = re.compile(r"^lw-[0-9a-f]{16}$")
CONTROL_RUN_ID_RE = re.compile(r"^cr-[0-9a-f]{16}$")
CONTROL_SESSION_ID_RE = re.compile(r"^cs-[0-9a-f]{16}$")
MCP_REDACTED_VALUE = "[redacted-mcp-secret]"
LOCAL_PATH_REDACTED_VALUE = "[redacted-local-path]"
LOCAL_PATH_PATTERNS = (
    re.compile(r"/home/[^\s\"']+"),
    re.compile(r"/mnt/[a-zA-Z]/Users/[^\s\"']+"),
    re.compile(r"[A-Za-z]:\\Users\\[^\s\"']+"),
)
MCP_SECRET_KEY_TERMS = (
    "access_token",
    "api_key",
    "api-key",
    "authorization",
    "bearer",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token_value",
)
MCP_SAFE_SECURITY_KEYS = frozenset({
    "auth_required",
    "credential_values_require_env_interpolation",
    "executes_tools",
    "prints_credentials",
    "reads_env_values",
    "token_handling",
})


class HarnessClient:
    def __init__(self, config: GatewayConfig):
        self.config = config

    def gateway_contract(self) -> dict[str, Any]:
        payload = self._request_json("GET", "/v1/gateway-contract")
        validate_gateway_contract(payload)
        assert_no_secret_values(payload)
        return payload

    def status(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/status")

    def readiness(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/readiness")

    def mcp_status(self) -> dict[str, Any]:
        return sanitize_mcp_payload(self._request_json("GET", "/v1/mcp/status"))

    def mcp_tools(self) -> dict[str, Any]:
        return sanitize_mcp_payload(self._request_json("GET", "/v1/mcp/tools"))

    def mcp_policy_check(self, *, operation: str, server: str | None = None, tool: str | None = None) -> dict[str, Any]:
        if operation not in {"status", "list-tools", "call-tool"}:
            raise ConfigError("operation must be status, list-tools, or call-tool")
        body: dict[str, Any] = {"operation": operation}
        if server is not None:
            _validate_id(server, "server")
            body["server"] = server
        if tool is not None:
            _validate_id(tool, "tool")
            body["tool"] = tool
        return sanitize_mcp_payload(self._request_json("POST", "/v1/mcp/policy-check", body))

    def list_sessions(self, limit: int = 20) -> dict[str, Any]:
        _validate_limit(limit)
        return sanitize_mobile_harness_payload(
            self._request_json("GET", f"/v1/sessions?{urlencode({'limit': limit})}")
        )

    def create_session(self) -> dict[str, Any]:
        return sanitize_mobile_harness_payload(self._request_json("POST", "/v1/sessions", {}))

    def get_session(self, session_id: str) -> dict[str, Any]:
        validate_control_session_id(session_id)
        return sanitize_mobile_harness_payload(self._request_json("GET", f"/v1/sessions/{session_id}"))

    def delete_session(self, session_id: str) -> dict[str, Any]:
        validate_control_session_id(session_id)
        return sanitize_mobile_harness_payload(self._request_json("DELETE", f"/v1/sessions/{session_id}"))

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        _validate_limit(limit)
        return sanitize_mobile_harness_payload(normalize_run_list_payload(
            self._request_json("GET", f"/v1/runs?{urlencode({'limit': limit})}")
        ))

    def get_run(self, run_id: str) -> dict[str, Any]:
        validate_control_run_id(run_id)
        return sanitize_mobile_harness_payload(self._request_json("GET", f"/v1/runs/{run_id}"))

    def get_run_events(self, run_id: str) -> dict[str, Any]:
        validate_control_run_id(run_id)
        return sanitize_mobile_harness_payload(sanitize_run_events_payload(
            self._request_json("GET", f"/v1/runs/{run_id}/events")
        ))

    def create_read_only_run(
        self,
        *,
        mode: str,
        task: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        body = build_read_only_run_body(mode=mode, task=task, session_id=session_id)
        return sanitize_mobile_harness_payload(self._request_json("POST", "/v1/runs", body))

    def local_chat_contract(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/local-chat/contract?client_version=1")

    def local_chat_workspaces(self) -> dict[str, Any]:
        return self._request_json("GET", "/v1/local-chat/workspaces?client_version=1")

    def local_chat_models(self, workspace_id: str) -> dict[str, Any]:
        validate_local_workspace_id(workspace_id)
        return self._request_json("GET", f"/v1/local-chat/models?{urlencode({'client_version': 1, 'workspace_id': workspace_id})}")

    def create_local_chat_run(
        self,
        *,
        mode: str,
        task: str,
        workspace_id: str,
        model_id: str = "default",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        body = build_local_chat_run_body(
            mode=mode,
            task=task,
            workspace_id=workspace_id,
            model_id=model_id,
            session_id=session_id,
        )
        return self._request_json("POST", "/v1/local-chat/runs", body, extra_headers=self._local_chat_csrf_headers())

    def get_local_chat_events(self, run_id: str, cursor: int = 0) -> dict[str, Any]:
        validate_control_run_id(run_id)
        if cursor < 0 or cursor > 1000000:
            raise ConfigError("cursor must be between 0 and 1000000")
        query = urlencode({"client_version": 1, "cursor": cursor})
        return self._request_json("GET", f"/v1/local-chat/runs/{run_id}/events?{query}")

    def get_local_chat_review(self, run_id: str, workspace_id: str) -> dict[str, Any]:
        validate_control_run_id(run_id)
        validate_local_workspace_id(workspace_id)
        query = urlencode({"client_version": 1, "workspace_id": workspace_id})
        return self._request_json("GET", f"/v1/local-chat/runs/{run_id}/review?{query}")

    def promote_local_chat_run(self, run_id: str, *, workspace_id: str, patch_sha256: str) -> dict[str, Any]:
        validate_control_run_id(run_id)
        validate_local_workspace_id(workspace_id)
        if not re.fullmatch(r"[0-9a-f]{64}", patch_sha256):
            raise ConfigError("patch_sha256 must be 64 lowercase hex characters")
        body = {"client_version": 1, "workspace_id": workspace_id, "patch_sha256": patch_sha256}
        return self._request_json("POST", f"/v1/local-chat/runs/{run_id}/promotion", body, extra_headers=self._local_chat_csrf_headers())

    def local_chat_lifecycle(self, run_id: str, *, action: str, workspace_id: str) -> dict[str, Any]:
        validate_control_run_id(run_id)
        validate_local_workspace_id(workspace_id)
        if action != "cancel":
            raise ConfigError("only cancel lifecycle action is exposed by the Gateway")
        body = {"client_version": 1, "workspace_id": workspace_id, "action": action}
        return self._request_json("POST", f"/v1/local-chat/runs/{run_id}/lifecycle", body, extra_headers=self._local_chat_csrf_headers())

    def _local_chat_csrf_headers(self) -> dict[str, str]:
        contract = self.local_chat_contract()
        security = contract.get("security") if isinstance(contract.get("security"), dict) else {}
        header = security.get("csrf_header")
        token = security.get("csrf_token")
        if not isinstance(header, str) or not header:
            raise ConfigError("local-chat contract did not provide a CSRF header")
        if not isinstance(token, str) or not token:
            raise ConfigError("local-chat contract did not provide a CSRF token")
        return {header: token}

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        token = read_control_token(self.config.token_file)
        data = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Cache-Control": "no-store",
        }
        if extra_headers:
            headers.update(extra_headers)
        if body is not None:
            data = json.dumps(body, sort_keys=True).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = Request(
            f"{self.config.harness_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            message = exc.read(4096).decode("utf-8", errors="replace")
            raise HarnessHTTPError(exc.code, message) from exc
        except URLError as exc:
            raise ConfigError(f"could not reach lai harness control plane: {exc}") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ConfigError("harness response exceeded gateway response limit")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError("harness response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ConfigError("harness response must be a JSON object")
        return payload


def sanitize_mcp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return MCP metadata with secret-shaped fields defensively redacted."""
    clean = _sanitize_mcp_value(payload)
    if not isinstance(clean, dict):
        raise ConfigError("MCP payload must be a JSON object")
    return clean


RUN_EVENT_FORBIDDEN_KEYS = frozenset({
    "stdout",
    "stderr",
    "task",
    "task_text",
    "transcript",
    "transcripts",
    "turn",
    "turns",
})


def sanitize_run_events_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return run-event metadata without output, task text, or transcript fields."""
    clean = _strip_run_event_forbidden_fields(payload)
    if not isinstance(clean, dict):
        raise ConfigError("run events payload must be a JSON object")
    return clean


def _strip_run_event_forbidden_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_run_event_forbidden_fields(nested)
            for key, nested in value.items()
            if str(key).lower() not in RUN_EVENT_FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_strip_run_event_forbidden_fields(item) for item in value]
    return value


MOBILE_HARNESS_FORBIDDEN_KEYS = RUN_EVENT_FORBIDDEN_KEYS | frozenset({
    "audit_file",
    "cwd",
    "metrics_file",
    "repository",
    "root_path",
    "workspace",
    "workspace_path",
})


def sanitize_mobile_harness_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return phone/CLI session-run payloads without local paths or raw run text."""
    clean = _strip_mobile_harness_private_fields(payload)
    if not isinstance(clean, dict):
        raise ConfigError("mobile harness payload must be a JSON object")
    return clean


def _strip_mobile_harness_private_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_mobile_harness_private_fields(nested)
            for key, nested in value.items()
            if str(key).lower() not in MOBILE_HARNESS_FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_strip_mobile_harness_private_fields(item) for item in value]
    if isinstance(value, str):
        return _redact_local_path_strings(value)
    return value


def _redact_local_path_strings(value: str) -> str:
    redacted = value
    for pattern in LOCAL_PATH_PATTERNS:
        redacted = pattern.sub(LOCAL_PATH_REDACTED_VALUE, redacted)
    return redacted


def _sanitize_mcp_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _is_mcp_secret_key(key):
        return None if value is None else MCP_REDACTED_VALUE
    if isinstance(value, dict):
        return {str(nested_key): _sanitize_mcp_value(nested, key=str(nested_key)) for nested_key, nested in value.items()}
    if isinstance(value, list):
        return [_sanitize_mcp_value(item) for item in value]
    if isinstance(value, str):
        return _redact_mcp_secret_strings(value)
    return value


def _is_mcp_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if lowered in MCP_SAFE_SECURITY_KEYS:
        return False
    return any(term in lowered for term in MCP_SECRET_KEY_TERMS)


def _redact_mcp_secret_strings(value: str) -> str:
    if "Bearer " in value:
        return value.split("Bearer ", 1)[0] + "Bearer " + MCP_REDACTED_VALUE
    if "sk-" in value and len(value) >= 20:
        return MCP_REDACTED_VALUE
    return value


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 100:
        raise ConfigError("limit must be between 1 and 100")


def _validate_id(value: str, label: str) -> None:
    if not value or any(ch in value for ch in "/?#\\") or len(value) > 128:
        raise ConfigError(f"invalid {label}")


def is_control_run_id(value: str) -> bool:
    return isinstance(value, str) and CONTROL_RUN_ID_RE.fullmatch(value) is not None


def is_control_session_id(value: str) -> bool:
    return isinstance(value, str) and CONTROL_SESSION_ID_RE.fullmatch(value) is not None


def is_local_workspace_id(value: str) -> bool:
    return isinstance(value, str) and LOCAL_WORKSPACE_ID_RE.fullmatch(value) is not None


def validate_control_run_id(value: str) -> None:
    if not is_control_run_id(value):
        raise ConfigError("invalid run_id")


def validate_control_session_id(value: str) -> None:
    if not is_control_session_id(value):
        raise ConfigError("invalid session_id")


def validate_local_workspace_id(value: str) -> None:
    if not is_local_workspace_id(value):
        raise ConfigError("invalid workspace_id")


def normalize_run_list_payload(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return payload
    normalized_runs = []
    changed = False
    for item in runs:
        if isinstance(item, dict) and "control_run_id" not in item and is_control_run_id(item.get("run_id", "")):
            updated = dict(item)
            updated["control_run_id"] = item["run_id"]
            normalized_runs.append(updated)
            changed = True
        else:
            normalized_runs.append(item)
    if not changed:
        return payload
    normalized = dict(payload)
    normalized["runs"] = normalized_runs
    return normalized


def build_read_only_run_body(*, mode: str, task: str, session_id: str | None = None) -> dict[str, str]:
    if mode not in READ_ONLY_RUN_MODES:
        allowed = ", ".join(sorted(READ_ONLY_RUN_MODES))
        raise ConfigError(f"mode must be read-only; allowed: {allowed}")
    if not isinstance(task, str) or not task.strip():
        raise ConfigError("task must be a non-empty string")
    if len(task) > MAX_TASK_CHARS:
        raise ConfigError(f"task must be at most {MAX_TASK_CHARS} characters")
    body = {"mode": mode, "task": task}
    if session_id is not None:
        validate_control_session_id(session_id)
        body["session_id"] = session_id
    return body


def build_local_chat_run_body(
    *,
    mode: str,
    task: str,
    workspace_id: str,
    model_id: str = "default",
    session_id: str | None = None,
) -> dict[str, str | int]:
    if mode not in LOCAL_CHAT_RUN_MODES:
        allowed = ", ".join(sorted(LOCAL_CHAT_RUN_MODES))
        raise ConfigError(f"mode must be allowed by local-chat; allowed: {allowed}")
    if not isinstance(task, str) or not task.strip():
        raise ConfigError("task must be a non-empty string")
    if len(task) > MAX_LOCAL_CHAT_TASK_CHARS:
        raise ConfigError(f"task must be at most {MAX_LOCAL_CHAT_TASK_CHARS} characters")
    validate_local_workspace_id(workspace_id)
    _validate_id(model_id, "model_id")
    body: dict[str, str | int] = {
        "client_version": 1,
        "workspace_id": workspace_id,
        "model_id": model_id,
        "mode": mode,
        "task": task,
    }
    if session_id is not None:
        validate_control_session_id(session_id)
        body["session_id"] = session_id
    return body
