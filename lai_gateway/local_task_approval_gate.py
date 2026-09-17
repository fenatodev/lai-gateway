from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import __version__

_SCHEMA_VERSION = "local-task-approval-gate/v1"
_REVIEW_SCHEMA_VERSION = "local-task-review-gate/v1"

_FALSE_AUTHORITY_FIELDS = (
    "effective_authorization",
    "executes_commands",
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

_REQUIRED_REVIEW_FIELDS = (
    "schema_version",
    "overall",
    "decision",
    "task_id",
    "read_only",
    "checks",
    *_FALSE_AUTHORITY_FIELDS,
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


def _read_json(repo: Path, rel: Path | None, label: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
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
        parsed = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [_check(f"json:{label}", "invalid", f"invalid JSON: {exc.msg}")]
    except OSError as exc:
        return None, [_check(f"json:{label}", "invalid", f"cannot read file: {exc}")]

    if not isinstance(parsed, dict):
        return None, [_check(f"json:{label}", "invalid", "JSON root must be an object")]

    return parsed, [_check(f"json:{label}", "ok", "valid JSON object")]


def _required_field_checks(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    if payload is None:
        return [_check("review:required_fields", "invalid", "review payload is missing")]

    missing = [field for field in _REQUIRED_REVIEW_FIELDS if field not in payload]
    if missing:
        return [_check("review:required_fields", "invalid", f"missing required fields: {', '.join(missing)}")]

    return [_check("review:required_fields", "ok", "required review fields are present")]


def _schema_check(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("review:schema", "invalid", "review payload is missing")
    actual = payload.get("schema_version")
    if actual != _REVIEW_SCHEMA_VERSION:
        return _check("review:schema", "invalid", f"expected {_REVIEW_SCHEMA_VERSION}, got {actual!r}")
    return _check("review:schema", "ok", f"{_REVIEW_SCHEMA_VERSION} present")


def _read_only_check(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("review:read_only", "invalid", "review payload is missing")
    if payload.get("read_only") is True:
        return _check("review:read_only", "ok", "review is read-only")
    return _check("review:read_only", "blocked", "review payload is not read-only")


def _authority_checks(payload: dict[str, Any] | None) -> list[dict[str, str]]:
    if payload is None:
        return [_check("review:authority", "invalid", "review payload is missing")]

    findings: list[dict[str, str]] = []
    for field in _FALSE_AUTHORITY_FIELDS:
        if field not in payload:
            findings.append(_check(f"review:authority:{field}", "invalid", f"{field} is missing"))
            continue
        value = payload.get(field)
        if value is False:
            continue
        if value is True:
            findings.append(_check(f"review:authority:{field}", "blocked", f"{field} claims authority"))
        else:
            findings.append(_check(f"review:authority:{field}", "invalid", f"{field} must be boolean false"))

    if not findings:
        findings.append(_check("review:authority", "ok", "no effective authority claims"))
    return findings


def _checks_shape(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("review:checks", "invalid", "review payload is missing")
    checks = payload.get("checks")
    if isinstance(checks, list):
        return _check("review:checks", "ok", "review checks are present")
    return _check("review:checks", "invalid", "review checks must be a list")


def _review_decision_check(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("review:decision", "invalid", "review payload is missing")

    overall = payload.get("overall")
    decision = payload.get("decision")
    if overall != decision:
        return _check("review:decision", "invalid", "overall and decision must match")

    if decision == "ready":
        return _check("review:decision", "ok", "review gate is ready")
    if decision == "blocked":
        return _check("review:decision", "blocked", "review gate blocked the task")
    if decision == "invalid":
        return _check("review:decision", "invalid", "review gate marked the task invalid")

    return _check("review:decision", "invalid", f"unexpected review decision: {decision!r}")


def _green_zone_evidence_check(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("approval:green_zone_evidence", "invalid", "review payload is missing")

    zone = payload.get("autonomy_zone")
    if zone == "green":
        return _check("approval:green_zone_evidence", "ok", "explicit green-zone evidence is present")
    if zone == "yellow":
        return _check("approval:green_zone_evidence", "needs_approval", "yellow-zone task requires human approval")
    if zone == "red":
        return _check("approval:green_zone_evidence", "blocked", "red-zone task is blocked at this gate")
    if zone is None:
        return _check("approval:green_zone_evidence", "needs_approval", "green-zone evidence is missing from review payload")

    return _check("approval:green_zone_evidence", "invalid", f"unknown autonomy_zone: {zone!r}")


def _explicit_approval_check(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return _check("approval:required", "invalid", "review payload is missing")

    if payload.get("approval_required") is True:
        return _check("approval:required", "needs_approval", "review payload explicitly requires approval")
    return _check("approval:required", "ok", "no explicit approval requirement in review payload")


def collect_local_task_approval_gate(
    *,
    repo: Path | None = None,
    review_file: str | None = None,
    review_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = (repo or Path.cwd()).resolve()

    checks: list[dict[str, str]] = []
    review_record: dict[str, Any] | None

    if review_payload is None:
        review_rel, review_path_check = _safe_relative_path(review_file, "review_file")
        checks.append(review_path_check)
        review_record, json_checks = _read_json(repo_root, review_rel, "review_file")
        checks.extend(json_checks)
        review_file_label = str(review_rel) if review_rel is not None else review_file
    elif isinstance(review_payload, dict):
        review_record = review_payload
        review_file_label = review_file
        checks.append(_check("review:payload", "ok", "review payload provided in memory"))
    else:
        review_record = None
        review_file_label = review_file
        checks.append(_check("review:payload", "invalid", "review payload must be an object"))

    checks.extend(_required_field_checks(review_record))
    checks.append(_schema_check(review_record))
    checks.append(_read_only_check(review_record))
    checks.extend(_authority_checks(review_record))
    checks.append(_checks_shape(review_record))
    checks.append(_review_decision_check(review_record))
    checks.append(_green_zone_evidence_check(review_record))
    checks.append(_explicit_approval_check(review_record))

    has_invalid = any(check["status"] == "invalid" for check in checks)
    has_blocked = any(check["status"] == "blocked" for check in checks)
    needs_approval = any(check["status"] == "needs_approval" for check in checks)

    if has_invalid:
        overall = "invalid"
    elif has_blocked:
        overall = "blocked"
    elif needs_approval:
        overall = "needs_approval"
    else:
        overall = "ready_without_approval"

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-task-approval-gate",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "decision": overall,
        "summary": "PR126 classifies reviewed local task readiness without granting execution.",
        "repo_root": str(repo_root),
        "review_file": review_file_label,
        "task_id": review_record.get("task_id") if isinstance(review_record, dict) else None,
        "read_only": True,
        "requires_human_approval": overall == "needs_approval",
        "approval_effective": False,
        "execution_authorized": False,
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


def render_local_task_approval_gate(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway local-task-approval-gate: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"decision: {payload.get('decision', 'unknown')}",
        f"review_file: {payload.get('review_file', 'unknown')}",
        f"task_id: {payload.get('task_id', 'unknown')}",
        f"requires_human_approval: {str(bool(payload.get('requires_human_approval'))).lower()}",
        "read_only: true",
        "approval_effective: false",
        "execution_authorized: false",
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
