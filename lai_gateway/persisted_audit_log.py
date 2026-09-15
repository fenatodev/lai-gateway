from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .effective_authorization import collect_effective_authorization

_PERSISTED_AUDIT_LOG_VERSION = "persisted-audit-log/v1"
_DEFAULT_AUDIT_DIR = ".lai/audit"
_LOG_FILENAME = "governance-audit.jsonl"


@dataclass(frozen=True)
class PersistedAuditLogRecord:
    record_id: str
    schema_version: str
    status: str
    operation: str
    operation_scope: str
    adapter_id: str | None
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action_sha256: str
    effective_authorization_id: str
    validation_id: str
    capture_id: str
    dry_run_id: str
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    approval_captured: bool
    approval_validated: bool
    scope_authorized: bool
    adapter_capability_authorized: bool
    effective_authorization: bool
    dispatch_enabled: bool
    adapter_dispatched: bool
    adapter_executed: bool
    executes_tools: bool
    external_side_effects: bool
    grants_permission: bool
    source_event_count: int
    written_at_utc: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_json(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _action_sha256(action: str | None) -> str:
    text = (action or "").encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _record_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"pal-{digest}"


def _resolve_scoped_dir(audit_dir: str | Path | None, *, scope_root: Path | None = None) -> Path:
    root = (scope_root or Path.cwd()).resolve()
    raw = Path(audit_dir or _DEFAULT_AUDIT_DIR).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve(strict=False)
    if root != resolved and root not in resolved.parents:
        raise ValueError("audit_dir must stay inside the configured LAI scope root")
    return resolved


def _reject_symlink_path(path: Path, *, scope_root: Path) -> None:
    root = scope_root.resolve()
    current = path
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("audit path must not include symlinks")
        if current == root:
            return
        if current.parent == current:
            return
        current = current.parent


def _prepare_log_path(audit_dir: str | Path | None, *, scope_root: Path | None = None) -> Path:
    root = (scope_root or Path.cwd()).resolve()
    directory = _resolve_scoped_dir(audit_dir, scope_root=root)
    _reject_symlink_path(directory, scope_root=root)
    if directory.exists() and not directory.is_dir():
        raise ValueError("audit_dir must be a directory")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except PermissionError:
        pass
    log_path = directory / _LOG_FILENAME
    if log_path.exists() and log_path.is_symlink():
        raise ValueError("audit log file must not be a symlink")
    return log_path

def _build_sanitized_record(effective_payload: dict[str, Any]) -> PersistedAuditLogRecord:
    effective = effective_payload["effective"]
    source_events = effective_payload.get("audit", {}).get("events", [])
    base = {
        "schema_version": _PERSISTED_AUDIT_LOG_VERSION,
        "operation": effective_payload["operation"],
        "operation_scope": effective["operation_scope"],
        "adapter_id": effective.get("adapter_id"),
        "requested_capability": effective["requested_capability"],
        "actor": effective["actor"],
        "channel": effective["channel"],
        "domain": effective["domain"],
        "action_sha256": _action_sha256(effective.get("action")),
        "effective_authorization_id": effective["effective_authorization_id"],
        "validation_id": effective["validation_id"],
        "capture_id": effective["capture_id"],
        "dry_run_id": effective["dry_run_id"],
        "proposal_id": effective["proposal_id"],
        "authorization_record_id": effective["authorization_record_id"],
        "evaluation_id": effective["evaluation_id"],
        "decision_id": effective["decision_id"],
        "audit_log_id": effective["audit_log_id"],
        "approval_captured": bool(effective["approval_captured"]),
        "approval_validated": bool(effective["approval_validated"]),
        "scope_authorized": bool(effective["scope_authorized"]),
        "adapter_capability_authorized": bool(effective["adapter_capability_authorized"]),
        "effective_authorization": bool(effective["effective_authorization"]),
        "dispatch_enabled": bool(effective["dispatch_enabled"]),
        "adapter_dispatched": bool(effective["adapter_dispatched"]),
        "adapter_executed": bool(effective["adapter_executed"]),
        "executes_tools": bool(effective["executes_tools"]),
        "external_side_effects": bool(effective["external_side_effects"]),
        "grants_permission": bool(effective["grants_permission"]),
        "source_event_count": len(source_events),
    }
    rid = _record_id((_PERSISTED_AUDIT_LOG_VERSION, _digest_json(base)))
    return PersistedAuditLogRecord(record_id=rid, status="planned", written_at_utc=None, **base)


def _write_jsonl(path: Path, record: PersistedAuditLogRecord) -> tuple[int, str]:
    payload = record.to_dict() | {
        "status": "written",
        "written_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    line = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        written = os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    try:
        os.chmod(path, 0o600)
    except PermissionError:
        pass
    return written, _digest_json(payload)


def collect_persisted_audit_log(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
    operation_scope: str | None = None,
    audit_dir: str | Path | None = None,
    write: bool = False,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    effective_payload = collect_effective_authorization(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
        operation_scope=operation_scope,
    )
    record = _build_sanitized_record(effective_payload)
    status = "planned"
    reason = "audit record built but not persisted; pass explicit write flag to append locally"
    persisted = False
    bytes_appended = 0
    record_digest = _digest_json(record.to_dict())
    log_path: Path | None = None
    if write:
        try:
            log_path = _prepare_log_path(audit_dir, scope_root=scope_root)
            bytes_appended, record_digest = _write_jsonl(log_path, record)
            status = "written"
            reason = "sanitized audit record appended to scoped local JSONL log"
            persisted = True
        except OSError as exc:
            status = "blocked"
            reason = f"audit persistence blocked: {exc.__class__.__name__}"
        except ValueError as exc:
            status = "blocked"
            reason = str(exc)
    display_path = str(log_path.relative_to((scope_root or Path.cwd()).resolve())) if log_path and log_path.is_absolute() else str(log_path or _DEFAULT_AUDIT_DIR)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "persisted-audit-log",
        "overall": "ready",
        "audit_log_version": _PERSISTED_AUDIT_LOG_VERSION,
        "status": status,
        "reason": reason,
        "write_requested": bool(write),
        "persisted": persisted,
        "append_only": True,
        "log_format": "jsonl",
        "log_path": display_path,
        "bytes_appended": bytes_appended,
        "record_digest_sha256": record_digest,
        "record": record.to_dict() | {"status": status if persisted else record.status},
        "security": {
            "prints_tokens": False,
            "stores_raw_parameters": False,
            "stores_raw_action": False,
            "uses_fixed_filename": True,
            "requires_explicit_write": True,
            "confines_to_scope_root": True,
            "append_only": True,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "grants_permissions": False,
        },
    }


def render_persisted_audit_log(payload: dict[str, Any]) -> str:
    record = payload["record"]
    lines = [
        f"lai-gateway persisted-audit-log: {payload['overall']}",
        f"version: {payload['version']}",
        f"audit_log_version: {payload['audit_log_version']}",
        f"status: {payload['status']}",
        f"persisted: {str(payload['persisted']).lower()}",
        f"write_requested: {str(payload['write_requested']).lower()}",
        f"append_only: {str(payload['append_only']).lower()}",
        f"log_format: {payload['log_format']}",
        f"log_path: {payload['log_path']}",
        f"record_id: {record['record_id']}",
        f"operation_scope: {record['operation_scope']}",
        f"adapter_id: {record.get('adapter_id') or 'none'}",
        f"requested_capability: {record['requested_capability']}",
        f"effective_authorization: {str(record['effective_authorization']).lower()}",
        f"adapter_capability_authorized: {str(record['adapter_capability_authorized']).lower()}",
        f"dispatch_enabled: {str(record['dispatch_enabled']).lower()}",
        f"stores_raw_parameters: {str(payload['security']['stores_raw_parameters']).lower()}",
        f"reason: {payload['reason']}",
    ]
    return "\n".join(lines)
