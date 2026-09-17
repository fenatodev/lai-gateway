from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import __version__
from .local_task_content_binding import (
    LocalTaskContentBindingError,
    compute_local_task_digest,
    parse_local_task_json,
)

_SCHEMA_VERSION = "local-task-review-gate/v1"
_TASK_SCHEMA_VERSION = "local-task/v1"
_OUTBOX_SCHEMA_VERSION = "local-task-outbox/v1"

_UNSAFE_TRUE_FIELDS = (
    "effective_authorization",
    "executes_commands",
    "would_execute_commands",
    "calls_harness",
    "would_call_harness",
    "executes_tools",
    "would_call_tools",
    "dispatches_adapter",
    "would_dispatch_adapter",
    "issues_grants",
    "would_issue_grants",
    "consumes_grants",
    "would_consume_grants",
    "uses_credentials",
    "would_use_credentials",
    "sends_messages",
    "would_send_messages",
    "publishes",
    "would_publish",
    "merges_main",
    "would_merge_main",
    "external_side_effects",
)


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def _safe_relative_path(value: str | None, label: str) -> tuple[Path | None, dict[str, str]]:
    raw = (value or "").strip()
    if not raw:
        return None, _check(f"path:{label}", "invalid", "path is required")

    path = Path(raw)
    if path.is_absolute():
        return None, _check(f"path:{label}", "invalid", "path must be repository-relative")
    if ".." in path.parts:
        return None, _check(f"path:{label}", "invalid", "path must not contain parent traversal")

    return path, _check(f"path:{label}", "ok", "path is repository-relative and bounded")


def _read_json(
    repo: Path,
    rel: Path | None,
    label: str,
    *,
    strict_local_task: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if rel is None:
        return None, [_check(f"json:{label}", "invalid", "path is invalid")]

    target = (repo / rel).resolve()
    try:
        target.relative_to(repo)
    except ValueError:
        return None, [_check(f"json:{label}", "invalid", "resolved path escapes repository root")]

    if not target.exists():
        return None, [_check(f"json:{label}", "invalid", "file does not exist")]

    try:
        text = target.read_text(encoding="utf-8")
        parsed = parse_local_task_json(text) if strict_local_task else json.loads(text)
    except LocalTaskContentBindingError as exc:
        return None, [_check(f"json:{label}", "invalid", str(exc))]
    except json.JSONDecodeError as exc:
        return None, [_check(f"json:{label}", "invalid", f"invalid JSON: {exc.msg}")]
    except OSError as exc:
        return None, [_check(f"json:{label}", "invalid", f"cannot read file: {exc}")]

    if not isinstance(parsed, dict):
        return None, [_check(f"json:{label}", "invalid", "JSON root must be an object")]

    return parsed, [_check(f"json:{label}", "ok", "valid JSON object")]


def _schema_check(payload: dict[str, Any] | None, label: str, expected: str) -> dict[str, str]:
    if payload is None:
        return _check(f"schema:{label}", "invalid", "payload is missing")
    actual = payload.get("schema_version")
    if actual != expected:
        return _check(f"schema:{label}", "invalid", f"expected {expected}, got {actual!r}")
    return _check(f"schema:{label}", "ok", f"{expected} present")


def _unsafe_claim_checks(payload: dict[str, Any] | None, label: str) -> list[dict[str, str]]:
    if payload is None:
        return [_check(f"unsafe:{label}", "invalid", "payload is missing")]

    checks: list[dict[str, str]] = []
    for field in _UNSAFE_TRUE_FIELDS:
        if bool(payload.get(field)):
            checks.append(_check(f"unsafe:{label}:{field}", "blocked", f"{field} claims operational authority"))

    if not checks:
        checks.append(_check(f"unsafe:{label}", "ok", "no unsafe true authority claims"))
    return checks


def collect_local_task_review_gate(
    *,
    repo: Path | None = None,
    task_file: str | None = None,
    outbox_file: str | None = None,
) -> dict[str, Any]:
    repo_root = (repo or Path.cwd()).resolve()

    task_rel, task_path_check = _safe_relative_path(task_file, "task_file")
    outbox_rel, outbox_path_check = _safe_relative_path(outbox_file, "outbox_file")

    task_record, task_json_checks = _read_json(repo_root, task_rel, "task_file", strict_local_task=True)
    outbox_record, outbox_json_checks = _read_json(repo_root, outbox_rel, "outbox_file")

    checks: list[dict[str, str]] = [
        task_path_check,
        outbox_path_check,
        *task_json_checks,
        *outbox_json_checks,
        _schema_check(task_record, "task", _TASK_SCHEMA_VERSION),
        _schema_check(outbox_record, "outbox", _OUTBOX_SCHEMA_VERSION),
    ]

    if task_record is not None and outbox_record is not None:
        task_id = task_record.get("task_id")
        outbox_task_id = outbox_record.get("task_id")
        checks.append(
            _check("identity:task_id", "ok", "task ids match")
            if task_id and task_id == outbox_task_id
            else _check("identity:task_id", "invalid", "task ids are missing or do not match")
        )

        checks.append(
            _check("autonomy:red_zone", "blocked", "red-zone task requires explicit approval at the moment of action")
            if task_record.get("autonomy_zone") == "red"
            else _check("autonomy:red_zone", "ok", "task is not red-zone")
        )

    checks.extend(_unsafe_claim_checks(task_record, "task"))
    checks.extend(_unsafe_claim_checks(outbox_record, "outbox"))

    task_digest: str | None = None
    if task_record is not None:
        try:
            task_digest = compute_local_task_digest(task_record)
            checks.append(_check("identity:task_digest", "ok", "task digest computed"))
        except LocalTaskContentBindingError as exc:
            checks.append(_check("identity:task_digest", "invalid", str(exc)))

    has_invalid = any(check["status"] == "invalid" for check in checks)
    has_blocked = any(check["status"] == "blocked" for check in checks)

    decision = "invalid" if has_invalid else ("blocked" if has_blocked else "ready")

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-task-review-gate",
        "schema_version": _SCHEMA_VERSION,
        "overall": decision,
        "decision": decision,
        "summary": "PR125 reviews local task/outbox JSON records without execution.",
        "repo_root": str(repo_root),
        "task_file": str(task_rel) if task_rel is not None else task_file,
        "outbox_file": str(outbox_rel) if outbox_rel is not None else outbox_file,
        "task_id": task_record.get("task_id") if isinstance(task_record, dict) else None,
        "task_digest": task_digest,
        "autonomy_zone": task_record.get("autonomy_zone") if isinstance(task_record, dict) else None,
        "approval_required": bool(task_record.get("approval_required")) if isinstance(task_record, dict) else False,
        "read_only": True,
        "effective_authorization": False,
        "executes_commands": False,
        "calls_harness": False,
        "executes_tools": False,
        "dispatches_adapter": False,
        "issues_grants": False,
        "consumes_grants": False,
        "uses_credentials": False,
        "sends_messages": False,
        "publishes": False,
        "merges_main": False,
        "external_side_effects": False,
        "checks": checks,
    }


def render_local_task_review_gate(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway local-task-review-gate: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        f"task_file: {payload.get('task_file', 'unknown')}",
        f"outbox_file: {payload.get('outbox_file', 'unknown')}",
        f"task_digest: {payload.get('task_digest', 'unknown')}",
        "read_only: true",
        "effective_authorization: false",
        "executes_commands: false",
        "calls_harness: false",
        "executes_tools: false",
        "dispatches_adapter: false",
        "issues_grants: false",
        "consumes_grants: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
        "merges_main: false",
        "external_side_effects: false",
    ]

    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    if checks:
        lines.append("checks:")
        for check in checks:
            lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")

    return "\n".join(lines)
