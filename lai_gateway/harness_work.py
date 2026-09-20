from __future__ import annotations

import math
import time
from typing import Any

from .errors import GatewayError
from .harness_client import (
    HarnessClient,
    WORK_RUN_MODES,
    build_local_chat_run_body,
    validate_control_run_id,
    validate_local_workspace_id,
)


class HarnessWorkError(GatewayError):
    """A bounded, secret-free Work coordination failure (never retry submission)."""


_TERMINAL = {"succeeded", "failed", "cancelled"}
_STATES = _TERMINAL | {"queued", "running"}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise HarnessWorkError(reason)


def _object(value: Any) -> dict[str, Any]:
    _require(isinstance(value, dict), "invalid Harness response object")
    return value


def run_work(
    client: HarnessClient,
    mode: str,
    task: str,
    workspace_id: str | None = None,
    model_id: str = "default",
    max_polls: int = 1000,
    timeout_seconds: float = 960.0,
    clock=time.monotonic,
    sleep=time.sleep,
) -> dict[str, Any]:
    """Submit once, poll and review. Never apply, cancel, execute or replay tools."""
    _require(isinstance(mode, str) and mode in WORK_RUN_MODES, "invalid work mode")
    _require(type(max_polls) is int and 1 <= max_polls <= 2000, "invalid polling budget")
    _require(type(timeout_seconds) in {int, float} and math.isfinite(timeout_seconds)
             and 0 < timeout_seconds <= 1800, "invalid work deadline")
    # Validate before any request, including when the workspace is selected later.
    try:
        build_local_chat_run_body(mode=mode, task=task,
                                  workspace_id="lw-0000000000000000" if workspace_id is None else workspace_id, model_id=model_id)
    except (GatewayError, TypeError, ValueError):
        raise HarnessWorkError("invalid work request") from None
    deadline = clock() + timeout_seconds

    def request(method, *args, **kwargs):
        _require(clock() < deadline, "work deadline exceeded; do not resubmit automatically")
        try:
            result = _object(method(*args, **kwargs))
        except HarnessWorkError:
            raise
        except (GatewayError, OSError, ValueError, TypeError):
            raise HarnessWorkError("Harness request failed; delivery may be uncertain; do not resubmit") from None
        _require(clock() < deadline, "work deadline exceeded; run may still be active")
        return result

    contract = request(client.local_chat_contract)
    capabilities = _object(contract.get("capabilities"))
    _require(contract.get("schema_version") == 1 and contract.get("negotiated") is True
             and capabilities.get("local_chat_work_runs") is True
             and capabilities.get("source_repository_write") is False,
             "Harness work contract is incompatible")
    workspace_payload = request(client.local_chat_workspaces)
    workspaces = workspace_payload.get("workspaces")
    _require(isinstance(workspaces, list) and 0 < len(workspaces) <= 100, "invalid workspace registry")
    registered = []
    for item in workspaces:
        item = _object(item)
        try:
            validate_local_workspace_id(item.get("workspace_id"))
        except (GatewayError, TypeError, ValueError):
            raise HarnessWorkError("invalid registered workspace") from None
        _require(item.get("source_checkout_write") is False, "unsafe workspace contract")
        registered.append(item["workspace_id"])
    _require(len(set(registered)) == len(registered), "duplicate workspace registration")
    if workspace_id is None:
        _require(len(registered) == 1, "workspace selection is ambiguous")
        workspace_id = registered[0]
    _require(workspace_id in registered, "workspace is not registered")
    models = request(client.local_chat_models, workspace_id)
    _require(models.get("workspace_id") == workspace_id, "model workspace mismatch")
    choices = models.get("models")
    _require(isinstance(choices, list), "invalid model registry")
    matches = [item for item in choices if isinstance(item, dict) and item.get("model_id") == model_id]
    _require(len(matches) == 1 and matches[0].get("available") is True, "model is not available")

    created = request(client.create_local_chat_run, mode=mode, task=task,
                      workspace_id=workspace_id, model_id=model_id)
    run = _object(created.get("run"))
    run_id = run.get("control_run_id")
    try:
        validate_control_run_id(run_id)
    except (GatewayError, TypeError, ValueError):
        raise HarnessWorkError("invalid created run identity; do not resubmit") from None
    _require(run.get("mode") == mode and isinstance(run.get("status"), str) and run.get("status") in _STATES, "created run mismatch")
    cursor = 0
    for _ in range(max_polls):
        events = request(client.get_local_chat_events, run_id, cursor=cursor)
        status = events.get("status")
        next_cursor = events.get("next_cursor")
        _require(events.get("control_run_id") == run_id and events.get("mode") == mode,
                 "event run identity mismatch")
        _require(type(events.get("cursor")) is int and events["cursor"] == cursor
                 and type(next_cursor) is int and cursor <= next_cursor <= 1000000,
                 "invalid event cursor")
        _require(isinstance(status, str) and status in _STATES
                 and type(events.get("terminal")) is bool
                 and events["terminal"] == (status in _TERMINAL), "inconsistent terminal state")
        cursor = next_cursor
        if events["terminal"]:
            break
        sleep(min(1.0, max(0.0, deadline - clock())))
    else:
        raise HarnessWorkError("poll limit exceeded; run may still be active; do not resubmit")

    payload = request(client.get_local_chat_review, run_id, workspace_id)
    review = _object(payload.get("review"))
    _require(payload.get("workspace_id") == workspace_id
             and review.get("control_run_id") == run_id and review.get("mode") == mode
             and review.get("status") == status and review.get("terminal") is True,
             "review does not match terminal run")
    workspace = _object(review.get("workspace"))
    _require(workspace.get("isolated") is True, "review workspace is not isolated")
    paths = workspace.get("changed_paths")
    _require(isinstance(paths, list) and len(paths) <= 100, "invalid review change list")
    validation = _object(review.get("validation"))
    last = validation.get("last_result")
    validated = isinstance(last, dict) and last.get("status") == "pass" and type(last.get("exit_code")) is int and last["exit_code"] == 0
    # Allowlist projection: no paths, model text, events, diff, commands or secrets.
    return {
        "status": "ready" if status == "succeeded" and validated and paths else "blocked",
        "tool": "harness_work",
        "run_id": run_id,
        "workspace_id": workspace_id,
        "mode": mode,
        "terminal_status": status,
        "review": {"terminal": True, "isolated": True, "changed_path_count": len(paths),
                   "validation_passed": validated},
        "content_grants_authority": False,
        "security": {"source_checkout_write": False, "promotion_performed": False,
                     "apply_performed": False, "gateway_subprocess": False, "git_mutation": False},
    }
