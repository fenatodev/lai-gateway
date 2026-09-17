from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from .local_task_content_binding import (
    LocalTaskContentBindingError,
    compute_local_task_digest,
    is_valid_local_task_digest,
    parse_local_task_json,
)
from .tool_mediation import run_process

_SCHEMA_VERSION = "local-task-green-executor/v1"
_APPROVAL_SCHEMA_VERSION = "local-task-approval-gate/v1"
_TASK_SCHEMA_VERSION = "local-task/v1"

_FALSE_INPUT_AUTHORITY_FIELDS = (
    "approval_effective",
    "execution_authorized",
    "effective_authorization",
    "calls_harness",
    "executes_tools",
    "dispatches_adapter",
    "issues_grants",
    "consumes_grants",
    "uses_credentials",
    "sends_messages",
    "publishes",
    "merges_main",
    "external_side_effects",
)

_ALLOWED_EXACT_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("git", "--version"),
    ("git", "diff", "--check"),
    ("git", "status", "--short", "--branch"),
    ("git", "diff", "--stat"),
    ("python3", "-m", "compileall", "-q", "lai_gateway", "tests"),
    ("python3", "-m", "unittest", "tests.test_local_task_review_gate", "-v"),
    ("python3", "-m", "unittest", "tests.test_local_task_approval_gate", "-v"),
    ("python3", "-m", "unittest", "tests.test_local_task_green_executor", "-v"),
    ("python3", "-m", "unittest", "tests.test_product_docs", "-v"),
    ("make", "check"),
)

_BLOCKED_TOKENS = {
    "sudo",
    "su",
    "rm",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "gh",
    "git-credential",
    "docker",
    "podman",
    "npx",
    "npm",
    "pip",
    "pip3",
}


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


def _clean_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _limit_output(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n<truncated>"


def _tokens(command: str) -> tuple[tuple[str, ...] | None, dict[str, str]]:
    try:
        parsed = tuple(shlex.split(command))
    except ValueError as exc:
        return None, _check("command:parse", "invalid", f"cannot parse command: {exc}")

    if not parsed:
        return None, _check("command:parse", "invalid", "command is empty")

    return parsed, _check("command:parse", "ok", "command parsed without shell")


def _approval_checks(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    if payload is None:
        return [_check("approval:payload", "invalid", "approval payload is missing")]

    checks: list[dict[str, str]] = []

    if payload.get("schema_version") == _APPROVAL_SCHEMA_VERSION:
        checks.append(_check("approval:schema", "ok", f"{_APPROVAL_SCHEMA_VERSION} present"))
    else:
        checks.append(_check("approval:schema", "invalid", "approval gate schema is invalid"))

    if payload.get("overall") == payload.get("decision") == "ready_without_approval":
        checks.append(_check("approval:decision", "ok", "approval gate is ready_without_approval"))
    else:
        checks.append(_check("approval:decision", "blocked", "approval gate is not ready_without_approval"))

    if payload.get("requires_human_approval") is False:
        checks.append(_check("approval:human", "ok", "no human approval required by approval gate"))
    else:
        checks.append(_check("approval:human", "blocked", "approval gate requires human approval"))

    if payload.get("read_only") is True:
        checks.append(_check("approval:read_only", "ok", "approval gate output is read-only evidence"))
    else:
        checks.append(_check("approval:read_only", "invalid", "approval gate read_only flag is not true"))

    for field in _FALSE_INPUT_AUTHORITY_FIELDS:
        value = payload.get(field)
        if value is False:
            continue
        if value is True:
            checks.append(_check(f"approval:authority:{field}", "blocked", f"{field} claims authority"))
        else:
            checks.append(_check(f"approval:authority:{field}", "invalid", f"{field} must be boolean false"))

    return checks


def _task_checks(task: dict[str, Any] | None, approval: dict[str, Any] | None) -> list[dict[str, str]]:
    if task is None:
        return [_check("task:payload", "invalid", "task payload is missing")]

    checks: list[dict[str, str]] = []

    if task.get("schema_version") == _TASK_SCHEMA_VERSION:
        checks.append(_check("task:schema", "ok", f"{_TASK_SCHEMA_VERSION} present"))
    else:
        checks.append(_check("task:schema", "invalid", "task schema is invalid"))

    task_id = task.get("task_id")
    approval_task_id = approval.get("task_id") if isinstance(approval, dict) else None
    if task_id and approval_task_id and task_id == approval_task_id:
        checks.append(_check("task:identity", "ok", "task id matches approval gate output"))
    else:
        checks.append(_check("task:identity", "invalid", "task id is missing or does not match approval gate output"))

    if task.get("autonomy_zone") == "green":
        checks.append(_check("task:green_zone", "ok", "task is explicitly green-zone"))
    else:
        checks.append(_check("task:green_zone", "blocked", "executor only accepts green-zone tasks"))

    if task.get("requires_human_approval") is False:
        checks.append(_check("task:approval_required", "ok", "task does not require human approval"))
    else:
        checks.append(_check("task:approval_required", "blocked", "task requires human approval"))

    if task.get("effective_authorization") is True:
        checks.append(_check("task:false_authority", "blocked", "task record must not claim effective authorization"))
    else:
        checks.append(_check("task:false_authority", "ok", "task record does not claim effective authorization"))

    return checks


def _content_binding_checks(
    task: dict[str, Any] | None,
    approval: dict[str, Any] | None,
) -> tuple[list[dict[str, str]], str | None]:
    if task is None:
        return [_check("identity:task_digest", "invalid", "task payload is missing")], None

    try:
        task_digest = compute_local_task_digest(task)
    except LocalTaskContentBindingError as exc:
        return [_check("identity:task_digest", "invalid", str(exc))], None

    approval_digest = (
        approval.get("task_digest")
        if isinstance(approval, dict)
        else None
    )

    if not is_valid_local_task_digest(approval_digest):
        return [
            _check(
                "identity:task_digest",
                "invalid",
                "approval task_digest is missing or malformed",
            )
        ], task_digest

    if task_digest != approval_digest:
        return [
            _check(
                "identity:task_digest",
                "invalid",
                "task digest does not match approval gate output",
            )
        ], task_digest

    return [
        _check(
            "identity:task_digest",
            "ok",
            "task digest matches approval gate output",
        )
    ], task_digest


def _command_checks(task: dict[str, Any] | None, requested_commands: list[str]) -> tuple[list[dict[str, str]], list[tuple[str, tuple[str, ...]]]]:
    checks: list[dict[str, str]] = []
    accepted: list[tuple[str, tuple[str, ...]]] = []

    if task is None:
        return [_check("commands:task", "invalid", "task payload is missing")], accepted

    proposed = _clean_list(task.get("proposed_commands") if isinstance(task.get("proposed_commands"), list) else None)
    commands = _clean_list(requested_commands) if requested_commands else proposed

    if not commands:
        return [_check("commands:requested", "invalid", "no commands were requested or proposed")], accepted

    if len(commands) > 5:
        checks.append(_check("commands:count", "blocked", "at most five commands may be executed"))
        return checks, accepted

    checks.append(_check("commands:count", "ok", f"{len(commands)} command(s) requested"))

    for command in commands:
        if command not in proposed:
            checks.append(_check("commands:declared", "blocked", f"command not declared by task: {command}"))
            continue

        parsed, parse_check = _tokens(command)
        checks.append(parse_check)
        if parsed is None:
            continue

        blocked = sorted(set(parsed) & _BLOCKED_TOKENS)
        if blocked:
            checks.append(_check("commands:blocked_token", "blocked", f"blocked token(s): {', '.join(blocked)}"))
            continue

        if parsed not in _ALLOWED_EXACT_COMMANDS:
            checks.append(_check("commands:allowlist", "blocked", f"command is not exactly allowlisted: {command}"))
            continue

        checks.append(_check("commands:allowlist", "ok", f"command is task-declared and allowlisted: {command}"))
        accepted.append((command, parsed))

    return checks, accepted


def _run_commands(repo: Path, commands: list[tuple[str, tuple[str, ...]]], timeout_seconds: float) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command, argv in commands:
        try:
            completed = run_process(
                list(argv),
                capability="local_task_green_executor",
                cwd=repo,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
            status = "success" if completed.returncode == 0 else "failed"
            results.append({
                "command": command,
                "argv": list(argv),
                "status": status,
                "returncode": completed.returncode,
                "stdout": _limit_output(completed.stdout),
                "stderr": _limit_output(completed.stderr),
            })
        except subprocess.TimeoutExpired as exc:
            results.append({
                "command": command,
                "argv": list(argv),
                "status": "failed",
                "returncode": None,
                "stdout": _limit_output(exc.stdout or ""),
                "stderr": _limit_output(exc.stderr or "command timed out"),
            })
        except OSError as exc:
            results.append({
                "command": command,
                "argv": list(argv),
                "status": "failed",
                "returncode": None,
                "stdout": "",
                "stderr": str(exc),
            })
    return results


def collect_local_task_green_executor(
    *,
    repo: Path | None = None,
    approval_file: str | None = None,
    task_file: str | None = None,
    approval_payload: dict[str, Any] | None = None,
    task_payload: dict[str, Any] | None = None,
    commands: list[str] | tuple[str, ...] | None = None,
    execute: bool = False,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    repo_root = (repo or Path.cwd()).resolve()
    checks: list[dict[str, str]] = []

    approval_record: dict[str, Any] | None
    task_record: dict[str, Any] | None

    if approval_payload is None:
        approval_rel, approval_path_check = _safe_relative_path(approval_file, "approval_file")
        checks.append(approval_path_check)
        approval_record, approval_json_checks = _read_json(repo_root, approval_rel, "approval_file")
        checks.extend(approval_json_checks)
        approval_file_label = str(approval_rel) if approval_rel is not None else approval_file
    elif isinstance(approval_payload, dict):
        approval_record = approval_payload
        approval_file_label = approval_file
        checks.append(_check("approval:payload", "ok", "approval payload provided in memory"))
    else:
        approval_record = None
        approval_file_label = approval_file
        checks.append(_check("approval:payload", "invalid", "approval payload must be an object"))

    if task_payload is None:
        task_rel, task_path_check = _safe_relative_path(task_file, "task_file")
        checks.append(task_path_check)
        task_record, task_json_checks = _read_json(repo_root, task_rel, "task_file", strict_local_task=True)
        checks.extend(task_json_checks)
        task_file_label = str(task_rel) if task_rel is not None else task_file
    elif isinstance(task_payload, dict):
        task_record = task_payload
        task_file_label = task_file
        checks.append(_check("task:payload", "ok", "task payload provided in memory"))
    else:
        task_record = None
        task_file_label = task_file
        checks.append(_check("task:payload", "invalid", "task payload must be an object"))

    checks.extend(_approval_checks(approval_record))
    checks.extend(_task_checks(task_record, approval_record))

    content_binding_checks, task_digest = _content_binding_checks(
        task_record,
        approval_record,
    )
    checks.extend(content_binding_checks)

    command_checks, accepted_commands = _command_checks(task_record, list(commands or []))
    checks.extend(command_checks)

    has_invalid = any(check["status"] == "invalid" for check in checks)
    has_blocked = any(check["status"] == "blocked" for check in checks)

    command_results: list[dict[str, Any]] = []
    executed_commands = False

    if has_invalid:
        overall = "invalid"
    elif has_blocked:
        overall = "blocked"
    elif not execute:
        overall = "ready"
    else:
        command_results = _run_commands(repo_root, accepted_commands, timeout_seconds)
        executed_commands = bool(command_results)
        overall = "executed" if command_results and all(result["status"] == "success" for result in command_results) else "failed"

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-task-green-executor",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "decision": overall,
        "summary": "PR129 executes only content-bound task-declared exact allowlisted local commands for green tasks.",
        "repo_root": str(repo_root),
        "approval_file": approval_file_label,
        "task_file": task_file_label,
        "task_id": task_record.get("task_id") if isinstance(task_record, dict) else None,
        "task_digest": task_digest,
        "execute_requested": bool(execute),
        "planned_commands": [command for command, _ in accepted_commands],
        "command_results": command_results,
        "executes_commands": executed_commands,
        "requires_human_approval": False,
        "green_zone_only": True,
        "shell": False,
        "approval_effective": False,
        "effective_authorization": False,
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


def render_local_task_green_executor(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway local-task-green-executor: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        f"task_id: {payload.get('task_id', 'unknown')}",
        f"task_digest: {payload.get('task_digest', 'unknown')}",
        f"approval_file: {payload.get('approval_file', 'unknown')}",
        f"task_file: {payload.get('task_file', 'unknown')}",
        f"execute_requested: {str(bool(payload.get('execute_requested'))).lower()}",
        f"executes_commands: {str(bool(payload.get('executes_commands'))).lower()}",
        "green_zone_only: true",
        "shell: false",
        "approval_effective: false",
        "effective_authorization: false",
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

    planned = payload.get("planned_commands") if isinstance(payload.get("planned_commands"), list) else []
    if planned:
        lines.append("planned_commands:")
        for command in planned:
            lines.append(f"  - {command}")

    results = payload.get("command_results") if isinstance(payload.get("command_results"), list) else []
    if results:
        lines.append("command_results:")
        for result in results:
            lines.append(f"  - {result.get('command')}: {result.get('status')} ({result.get('returncode')})")

    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    if checks:
        lines.append("checks:")
        for check in checks:
            lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")

    return "\n".join(lines)
