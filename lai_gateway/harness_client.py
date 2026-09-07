from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import GatewayConfig, read_control_token
from .contract import assert_no_secret_values, validate_gateway_contract
from .errors import ConfigError, HarnessHTTPError

MAX_RESPONSE_BYTES = 1024 * 1024
READ_ONLY_RUN_MODES = frozenset({"diagnose", "plan", "release", "review", "security"})
MAX_TASK_CHARS = 12000



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

    def list_sessions(self, limit: int = 20) -> dict[str, Any]:
        _validate_limit(limit)
        return self._request_json("GET", f"/v1/sessions?{urlencode({'limit': limit})}")

    def create_session(self) -> dict[str, Any]:
        return self._request_json("POST", "/v1/sessions", {})

    def get_session(self, session_id: str) -> dict[str, Any]:
        _validate_id(session_id, "session_id")
        return self._request_json("GET", f"/v1/sessions/{session_id}")

    def delete_session(self, session_id: str) -> dict[str, Any]:
        _validate_id(session_id, "session_id")
        return self._request_json("DELETE", f"/v1/sessions/{session_id}")

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        _validate_limit(limit)
        return self._request_json("GET", f"/v1/runs?{urlencode({'limit': limit})}")

    def get_run(self, run_id: str) -> dict[str, Any]:
        _validate_id(run_id, "run_id")
        return self._request_json("GET", f"/v1/runs/{run_id}")

    def create_read_only_run(
        self,
        *,
        mode: str,
        task: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        body = build_read_only_run_body(mode=mode, task=task, session_id=session_id)
        return self._request_json("POST", "/v1/runs", body)

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = read_control_token(self.config.token_file)
        data = None
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Cache-Control": "no-store",
        }
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


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 100:
        raise ConfigError("limit must be between 1 and 100")


def _validate_id(value: str, label: str) -> None:
    if not value or any(ch in value for ch in "/?#\\") or len(value) > 128:
        raise ConfigError(f"invalid {label}")


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
        _validate_id(session_id, "session_id")
        body["session_id"] = session_id
    return body
