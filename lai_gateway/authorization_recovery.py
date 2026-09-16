from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import __version__
from .effective_authorization import collect_effective_authorization

_AUTHORIZATION_RECOVERY_VERSION = "authorization-recovery/v1"
_DEFAULT_AUTHORIZATION_DIR = ".lai/authorization"
_LOG_FILENAME = "authorization-events.jsonl"
_LOCK_FILENAME = "authorization-events.lock"
_LOCAL_STATUS_SCOPE = "local-status-read"
_LOCAL_STATUS_ADAPTER = "local_status"
_LOCAL_STATUS_CAPABILITY = "local_status.status"
_MAX_TTL_SECONDS = 3600
_DEFAULT_TTL_SECONDS = 300


@dataclass(frozen=True)
class AuthorizationRecoveryEvent:
    event_id: str
    schema_version: str
    event_type: str
    authorization_grant_id: str
    operation_scope: str
    adapter_id: str | None
    requested_capability: str
    identity_binding_id: str | None
    effective_authorization_id: str | None
    action_sha256: str
    issued_at_utc: str | None
    expires_at_utc: str | None
    event_at_utc: str
    actor: str
    channel: str
    domain: str
    status: str
    dispatch_allowed: bool = False
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(UTC)


def _action_sha256(action: str | None) -> str:
    return hashlib.sha256((action or "").encode("utf-8")).hexdigest()


def _event_id(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]
    return f"are-{digest}"


def _bounded_ttl_seconds(value: int | None) -> int:
    if value is None:
        return _DEFAULT_TTL_SECONDS
    return max(0, min(int(value), _MAX_TTL_SECONDS))


def _resolve_scoped_dir(directory: str | Path | None, *, scope_root: Path | None = None) -> Path:
    root = (scope_root or Path.cwd()).resolve()
    raw = Path(directory or _DEFAULT_AUTHORIZATION_DIR).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve(strict=False)
    if root != resolved and root not in resolved.parents:
        raise ValueError("authorization_dir must stay inside the configured LAI scope root")
    return resolved


def _reject_symlink_path(path: Path, *, scope_root: Path) -> None:
    root = scope_root.resolve()
    current = path
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("authorization path must not include symlinks")
        if current == root:
            return
        if current.parent == current:
            return
        current = current.parent


def _prepare_paths(directory: str | Path | None, *, scope_root: Path | None = None) -> tuple[Path, Path]:
    root = (scope_root or Path.cwd()).resolve()
    resolved = _resolve_scoped_dir(directory, scope_root=root)
    _reject_symlink_path(resolved, scope_root=root)
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("authorization_dir must be a directory")
    resolved.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(resolved, 0o700)
    except PermissionError:
        pass
    log_path = resolved / _LOG_FILENAME
    lock_path = resolved / _LOCK_FILENAME
    if log_path.exists() and log_path.is_symlink():
        raise ValueError("authorization log file must not be a symlink")
    if lock_path.exists() and lock_path.is_symlink():
        raise ValueError("authorization lock file must not be a symlink")
    return log_path, lock_path


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("schema_version") == _AUTHORIZATION_RECOVERY_VERSION:
                events.append(item)
    return events


def _append_event(path: Path, event: AuthorizationRecoveryEvent) -> tuple[int, str]:
    payload = event.to_dict()
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
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return written, digest


def _with_lock(lock_path: Path) -> int:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(lock_path, flags, 0o600)


def _release_lock(fd: int, lock_path: Path) -> None:
    os.close(fd)
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def _state_for(events: list[dict[str, Any]], grant_id: str | None, *, now: datetime) -> dict[str, Any]:
    matching = [event for event in events if event.get("authorization_grant_id") == grant_id]
    issued = next((event for event in matching if event.get("event_type") == "issued"), None)
    revoked = next((event for event in reversed(matching) if event.get("event_type") == "revoked"), None)
    consumed = next((event for event in reversed(matching) if event.get("event_type") == "consumed"), None)
    if not grant_id:
        status, reason = "blocked", "authorization grant id is required"
    elif issued is None:
        status, reason = "missing", "authorization grant was not found"
    else:
        expires_at = _parse_iso(issued.get("expires_at_utc"))
        expired = bool(expires_at and now >= expires_at)
        if revoked:
            status, reason = "revoked", "authorization grant was revoked"
        elif consumed:
            status, reason = "consumed", "authorization grant was already consumed"
        elif expired:
            status, reason = "expired", "authorization grant expired"
        else:
            status, reason = "active", "authorization grant recovered as active"
    return {
        "authorization_grant_id": grant_id,
        "status": status,
        "reason": reason,
        "issued": issued,
        "revoked": revoked,
        "consumed": consumed,
        "active": status == "active",
        "event_count": len(matching),
    }


def _exact_match(issued: dict[str, Any], effective: dict[str, Any]) -> tuple[bool, str]:
    expected = {
        "operation_scope": _LOCAL_STATUS_SCOPE,
        "adapter_id": _LOCAL_STATUS_ADAPTER,
        "requested_capability": _LOCAL_STATUS_CAPABILITY,
        "identity_binding_id": effective.get("identity_binding_id"),
        "action_sha256": _action_sha256(effective.get("action")),
        "effective_authorization_id": effective.get("effective_authorization_id"),
    }
    for key, value in expected.items():
        if issued.get(key) != value:
            return False, f"authorization grant does not match current {key}"
    return True, "authorization grant matches current request"


def _build_event(
    *,
    event_type: str,
    grant_id: str,
    effective: dict[str, Any] | None,
    issued: dict[str, Any] | None,
    now: datetime,
    expires_at: datetime | None = None,
    status: str,
    dispatch_allowed: bool = False,
) -> AuthorizationRecoveryEvent:
    source = effective or issued or {}
    issued_at = issued.get("issued_at_utc") if issued else (_iso(now) if event_type == "issued" else None)
    expiry = issued.get("expires_at_utc") if issued else (_iso(expires_at) if expires_at else None)
    base = {
        "schema_version": _AUTHORIZATION_RECOVERY_VERSION,
        "event_type": event_type,
        "authorization_grant_id": grant_id,
        "operation_scope": source.get("operation_scope") or _LOCAL_STATUS_SCOPE,
        "adapter_id": source.get("adapter_id"),
        "requested_capability": source.get("requested_capability") or "missing",
        "identity_binding_id": source.get("identity_binding_id"),
        "effective_authorization_id": source.get("effective_authorization_id"),
        "action_sha256": source.get("action_sha256") or _action_sha256(source.get("action")),
        "issued_at_utc": issued_at,
        "expires_at_utc": expiry,
        "event_at_utc": _iso(now),
        "actor": source.get("actor") or "user",
        "channel": source.get("channel") or "gateway",
        "domain": source.get("domain") or "governance",
        "status": status,
        "dispatch_allowed": dispatch_allowed,
        "grants_permission": False,
        "executes_tools": False,
        "external_side_effects": False,
        "modifies_files": False,
        "starts_server": False,
    }
    return AuthorizationRecoveryEvent(event_id=_event_id(base), **base)


def _effective_for_request(
    **kwargs: Any,
) -> dict[str, Any]:
    return collect_effective_authorization(operation_scope=_LOCAL_STATUS_SCOPE, **kwargs)


def collect_authorization_recovery(
    *,
    recovery_action: str = "check",
    authorization_grant_id: str | None = None,
    ttl_seconds: int | None = None,
    authorization_dir: str | Path | None = None,
    scope_root: Path | None = None,
    now_utc: datetime | None = None,
    requested_capability: str | None = None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
    user_id: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    service_id: str | None = None,
    identity_source: str | None = None,
    expected_identity_binding_id: str | None = None,
    claimed_user_id: str | None = None,
    claimed_client_id: str | None = None,
    claimed_agent_id: str | None = None,
    claimed_service_id: str | None = None,
) -> dict[str, Any]:
    now = _now(now_utc)
    action_name = (recovery_action or "check").strip().lower()
    log_path, lock_path = _prepare_paths(authorization_dir, scope_root=scope_root)
    effective_payload = _effective_for_request(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
        user_id=user_id,
        client_id=client_id,
        agent_id=agent_id,
        service_id=service_id,
        identity_source=identity_source,
        expected_identity_binding_id=expected_identity_binding_id,
        claimed_user_id=claimed_user_id,
        claimed_client_id=claimed_client_id,
        claimed_agent_id=claimed_agent_id,
        claimed_service_id=claimed_service_id,
    )
    effective = effective_payload["effective"]
    events = _read_events(log_path)
    status = "blocked"
    reason = "unsupported authorization recovery action"
    persisted = False
    dispatch_allowed = False
    bytes_appended = 0
    record_digest = ""
    state = _state_for(events, authorization_grant_id, now=now)
    event_payload: dict[str, Any] | None = None

    if action_name == "issue":
        if not effective.get("effective_authorization") or not effective.get("local_non_dry_run_authorized"):
            status = "blocked"
            reason = "only effective local-status-read authorization can be persisted"
        else:
            ttl = _bounded_ttl_seconds(ttl_seconds)
            issued_at = now
            expires_at = issued_at + timedelta(seconds=ttl)
            grant_id = f"agr-{uuid.uuid4().hex[:16]}"
            event = _build_event(
                event_type="issued",
                grant_id=grant_id,
                effective=effective,
                issued=None,
                now=issued_at,
                expires_at=expires_at,
                status="issued",
            )
            bytes_appended, record_digest = _append_event(log_path, event)
            persisted = True
            status = "issued"
            reason = "single-use local authorization grant persisted"
            authorization_grant_id = grant_id
            event_payload = event.to_dict()
            events = _read_events(log_path)
            state = _state_for(events, grant_id, now=now)
    elif action_name in {"check", "recover"}:
        status = state["status"]
        reason = state["reason"]
    elif action_name == "revoke":
        if not state["issued"]:
            status, reason = "blocked", state["reason"]
        elif state["consumed"]:
            status, reason = "blocked", "consumed authorization grant cannot be revoked"
        elif state["revoked"]:
            status, reason = "revoked", "authorization grant was already revoked"
        else:
            event = _build_event(
                event_type="revoked",
                grant_id=authorization_grant_id or "missing",
                effective=None,
                issued=state["issued"],
                now=now,
                status="revoked",
            )
            bytes_appended, record_digest = _append_event(log_path, event)
            persisted = True
            status, reason = "revoked", "authorization grant revoked"
            event_payload = event.to_dict()
            events = _read_events(log_path)
            state = _state_for(events, authorization_grant_id, now=now)
    elif action_name == "consume":
        fd = _with_lock(lock_path)
        try:
            events = _read_events(log_path)
            state = _state_for(events, authorization_grant_id, now=now)
            if not state["active"]:
                status, reason = "blocked", state["reason"]
            elif not effective.get("effective_authorization") or not effective.get("local_non_dry_run_authorized"):
                status, reason = "blocked", "current request is not effectively authorized for local-status-read"
            else:
                ok, match_reason = _exact_match(state["issued"], effective)
                if not ok:
                    status, reason = "blocked", match_reason
                else:
                    event = _build_event(
                        event_type="consumed",
                        grant_id=authorization_grant_id or "missing",
                        effective=None,
                        issued=state["issued"],
                        now=now,
                        status="consumed_for_single_use",
                        dispatch_allowed=True,
                    )
                    bytes_appended, record_digest = _append_event(log_path, event)
                    persisted = True
                    dispatch_allowed = True
                    status, reason = "consumed_for_single_use", "authorization grant consumed exactly once before dispatch"
                    event_payload = event.to_dict()
                    events = _read_events(log_path)
                    state = _state_for(events, authorization_grant_id, now=now)
        finally:
            _release_lock(fd, lock_path)

    display_path = str(log_path.relative_to((scope_root or Path.cwd()).resolve())) if log_path.is_absolute() else str(log_path)
    effective_public = dict(effective_payload["effective"])
    if "action" in effective_public:
        effective_public["action_sha256"] = _action_sha256(str(effective_public.pop("action")))
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "authorization-recovery",
        "overall": "ready",
        "authorization_recovery_version": _AUTHORIZATION_RECOVERY_VERSION,
        "recovery_action": action_name,
        "status": status,
        "reason": reason,
        "authorization_grant_id": authorization_grant_id,
        "authorization_persisted": bool(persisted or state.get("issued")),
        "authorization_active": bool(state.get("active")),
        "authorization_consumed": bool(state.get("consumed")),
        "authorization_revoked": bool(state.get("revoked")),
        "dispatch_allowed": dispatch_allowed,
        "recovered_after_restart": action_name in {"check", "recover", "consume"} and bool(state.get("issued")),
        "retry_automatic": False,
        "unknown_after_consume_without_result": bool(dispatch_allowed),
        "append_only": True,
        "log_format": "jsonl",
        "log_path": display_path,
        "bytes_appended": bytes_appended,
        "record_digest_sha256": record_digest,
        "state": {
            "status": state["status"],
            "reason": state["reason"],
            "event_count": state["event_count"],
            "issued_at_utc": (state.get("issued") or {}).get("issued_at_utc"),
            "expires_at_utc": (state.get("issued") or {}).get("expires_at_utc"),
        },
        "event": event_payload,
        "effective": effective_public,
        "security": {
            "prints_tokens": False,
            "stores_raw_parameters": False,
            "stores_raw_action": False,
            "confines_to_scope_root": True,
            "append_only": True,
            "single_use": True,
            "supports_expiration": True,
            "supports_revocation": True,
            "blocks_replay": True,
            "retry_automatic": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "grants_permissions": False,
        },
    }


def render_authorization_recovery(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"lai-gateway authorization-recovery: {payload['overall']}",
            f"version: {payload['version']}",
            f"authorization_recovery_version: {payload['authorization_recovery_version']}",
            f"recovery_action: {payload['recovery_action']}",
            f"status: {payload['status']}",
            f"authorization_grant_id: {payload.get('authorization_grant_id') or 'none'}",
            f"authorization_persisted: {str(payload['authorization_persisted']).lower()}",
            f"authorization_active: {str(payload['authorization_active']).lower()}",
            f"authorization_consumed: {str(payload['authorization_consumed']).lower()}",
            f"authorization_revoked: {str(payload['authorization_revoked']).lower()}",
            f"dispatch_allowed: {str(payload['dispatch_allowed']).lower()}",
            f"recovered_after_restart: {str(payload['recovered_after_restart']).lower()}",
            f"retry_automatic: {str(payload['retry_automatic']).lower()}",
            f"log_path: {payload['log_path']}",
            f"reason: {payload['reason']}",
            "executes_tools: false",
            "external_side_effects: false",
            "grants_permissions: false",
        ]
    )
