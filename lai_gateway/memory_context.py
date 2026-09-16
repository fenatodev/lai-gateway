import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__

_MEMORY_CONTEXT_VERSION = "memory-context/v1"
_DEFAULT_MEMORY_DIR = ".lai/memory"
_ALLOWED_ACTIONS = {"show", "remember", "forget"}
_ALLOWED_CONTEXT_KINDS = {"project", "personal"}
_MAX_NOTE_CHARS = 1000
_MAX_PROJECT_ID_CHARS = 64
_MAX_LIMIT = 100
_LOG_FILENAME = "memory-context.jsonl"
_PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SECRET_RE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+/=-]{12,}|"
    r"api[_-]?key\s*[:=]\s*[^\s]{8,}|"
    r"token\s*[:=]\s*[^\s]{8,}|"
    r"password\s*[:=]\s*[^\s]{4,}|"
    r"secret\s*[:=]\s*[^\s]{4,}|"
    r"sk-[a-z0-9]{16,}|"
    r"gh[pousr]_[a-z0-9_]{16,})"
)


@dataclass(frozen=True)
class MemoryContextEvent:
    event_id: str
    schema_version: str
    event_type: str
    memory_id: str
    context_kind: str
    project_id: str
    content: str | None
    content_sha256: str | None
    event_at_utc: str
    actor: str
    channel: str
    domain: str
    grants_permission: bool = False
    memory_grants_authority: bool = False
    approval_from_memory: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    starts_server: bool = False
    downloads_models: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event_id(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"mce-{hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]}"


def _memory_id(*, context_kind: str, project_id: str, content: str, now: datetime) -> str:
    seed = f"{context_kind}|{project_id}|{_iso(now)}|{_digest(content)}|{uuid.uuid4().hex}"
    return f"mem-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _normalize_action(action: str | None) -> str:
    value = (action or "show").strip().lower()
    if value not in _ALLOWED_ACTIONS:
        raise ValueError("memory_action must be one of: forget, remember, show")
    return value


def _normalize_context_kind(context_kind: str | None) -> str:
    value = (context_kind or "project").strip().lower()
    if value not in _ALLOWED_CONTEXT_KINDS:
        raise ValueError("context_kind must be project or personal")
    return value


def _normalize_project_id(project_id: str | None, *, context_kind: str) -> str:
    raw = "personal" if context_kind == "personal" and not project_id else (project_id or "default")
    value = raw.strip()
    if len(value) > _MAX_PROJECT_ID_CHARS or not _PROJECT_RE.fullmatch(value) or ".." in value:
        raise ValueError("project_id must be a bounded label without path traversal")
    return value


def _bounded_limit(value: int | None) -> int:
    if value is None:
        return 20
    return max(1, min(int(value), _MAX_LIMIT))


def _resolve_scoped_dir(directory: str | Path | None, *, scope_root: Path | None = None) -> Path:
    root = (scope_root or Path.cwd()).resolve()
    raw = Path(directory or _DEFAULT_MEMORY_DIR).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve(strict=False)
    if root != resolved and root not in resolved.parents:
        raise ValueError("memory_dir must stay inside the configured LAI scope root")
    return resolved


def _reject_symlink_path(path: Path, *, scope_root: Path) -> None:
    root = scope_root.resolve()
    current = path
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("memory path must not include symlinks")
        if current == root:
            return
        if current.parent == current:
            return
        current = current.parent


def _prepare_memory_file(
    memory_dir: str | Path | None,
    *,
    context_kind: str,
    project_id: str,
    scope_root: Path | None = None,
    create: bool = False,
) -> Path:
    root = (scope_root or Path.cwd()).resolve()
    base = _resolve_scoped_dir(memory_dir, scope_root=root)
    directory = base / context_kind / project_id
    _reject_symlink_path(directory, scope_root=root)
    if directory.exists() and not directory.is_dir():
        raise ValueError("memory_dir must resolve to a directory")
    if create:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(directory, 0o700)
        except PermissionError:
            pass
    path = directory / _LOG_FILENAME
    if path.exists() and path.is_symlink():
        raise ValueError("memory context log must not be a symlink")
    return path


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("schema_version") == _MEMORY_CONTEXT_VERSION:
                events.append(payload)
    return events


def _active_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    forgotten = {event.get("memory_id") for event in events if event.get("event_type") == "forgotten"}
    remembered = [event for event in events if event.get("event_type") == "remembered"]
    entries = []
    for event in remembered:
        if event.get("memory_id") in forgotten:
            continue
        entries.append({
            "memory_id": event.get("memory_id"),
            "context_kind": event.get("context_kind"),
            "project_id": event.get("project_id"),
            "content": event.get("content") or "",
            "content_sha256": event.get("content_sha256"),
            "created_at_utc": event.get("event_at_utc"),
        })
    return entries


def _contains_secret(text: str) -> bool:
    return bool(_SECRET_RE.search(text or ""))


def _append_event(path: Path, event: MemoryContextEvent) -> tuple[int, str]:
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
    return written, _digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _build_event(
    *,
    event_type: str,
    memory_id: str,
    context_kind: str,
    project_id: str,
    content: str | None,
    now: datetime,
    actor: str | None,
    channel: str | None,
    domain: str | None,
) -> MemoryContextEvent:
    base = {
        "schema_version": _MEMORY_CONTEXT_VERSION,
        "event_type": event_type,
        "memory_id": memory_id,
        "context_kind": context_kind,
        "project_id": project_id,
        "content": content,
        "content_sha256": _digest(content) if content is not None else None,
        "event_at_utc": _iso(now),
        "actor": actor or "user",
        "channel": channel or "gateway",
        "domain": domain or "memory_context",
        "grants_permission": False,
        "memory_grants_authority": False,
        "approval_from_memory": False,
        "executes_tools": False,
        "external_side_effects": False,
        "starts_server": False,
        "downloads_models": False,
    }
    return MemoryContextEvent(event_id=_event_id(base), **base)


def collect_memory_context(
    *,
    memory_action: str = "show",
    context_kind: str | None = "project",
    project_id: str | None = "default",
    note: str | None = None,
    memory_id: str | None = None,
    memory_dir: str | Path | None = None,
    scope_root: Path | None = None,
    limit: int | None = 20,
    now_utc: datetime | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    try:
        action_name = _normalize_action(memory_action)
        kind = _normalize_context_kind(context_kind)
        project = _normalize_project_id(project_id, context_kind=kind)
        bounded_limit = _bounded_limit(limit)
        create = action_name in {"remember", "forget"}
        path = _prepare_memory_file(memory_dir, context_kind=kind, project_id=project, scope_root=scope_root, create=create)
    except ValueError as exc:
        return _blocked_payload(reason=str(exc), action=memory_action, context_kind=context_kind, project_id=project_id)

    now = _now(now_utc)
    status = "empty"
    reason = "memory context has no stored entries for this scope"
    persisted = False
    bytes_appended = 0
    record_digest: str | None = None
    created_memory_id: str | None = None
    try:
        events = _read_events(path)
        entries = _active_entries(events)
        if action_name == "remember":
            content = (note or "").strip()
            if not content:
                return _blocked_payload(reason="note is required for memory remember", action=action_name, context_kind=kind, project_id=project)
            if len(content) > _MAX_NOTE_CHARS:
                return _blocked_payload(reason="note exceeds memory context size limit", action=action_name, context_kind=kind, project_id=project)
            if _contains_secret(content):
                return _blocked_payload(reason="memory context rejected secret-shaped content", action=action_name, context_kind=kind, project_id=project)
            created_memory_id = _memory_id(context_kind=kind, project_id=project, content=content, now=now)
            event = _build_event(
                event_type="remembered", memory_id=created_memory_id, context_kind=kind,
                project_id=project, content=content, now=now, actor=actor, channel=channel, domain=domain,
            )
            bytes_appended, record_digest = _append_event(path, event)
            events = _read_events(path)
            entries = _active_entries(events)
            status = "written"
            reason = "memory context appended to scoped local JSONL store"
            persisted = True
        elif action_name == "forget":
            target_id = (memory_id or "").strip()
            if not target_id:
                return _blocked_payload(reason="memory_id is required for memory forget", action=action_name, context_kind=kind, project_id=project)
            if not any(entry.get("memory_id") == target_id for entry in entries):
                status = "missing"
                reason = "memory_id was not active in this context scope"
            else:
                event = _build_event(
                    event_type="forgotten", memory_id=target_id, context_kind=kind,
                    project_id=project, content=None, now=now, actor=actor, channel=channel, domain=domain,
                )
                bytes_appended, record_digest = _append_event(path, event)
                events = _read_events(path)
                entries = _active_entries(events)
                status = "forgotten"
                reason = "memory context tombstone appended; original event was not rewritten"
                persisted = True
        else:
            status = "ready" if entries else "empty"
            reason = "memory context loaded from scoped local store" if entries else reason
    except OSError as exc:
        return _blocked_payload(reason=f"memory context persistence blocked: {exc.__class__.__name__}", action=action_name, context_kind=kind, project_id=project)
    entries = entries[-bounded_limit:]
    display_path = _display_path(path, scope_root=scope_root)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "memory-context",
        "schema_version": _MEMORY_CONTEXT_VERSION,
        "status": status,
        "overall": "blocked" if status == "blocked" else ("ready" if entries or persisted else "empty"),
        "reason": reason,
        "memory_action": action_name,
        "context_kind": kind,
        "project_id": project,
        "memory_id": created_memory_id or memory_id,
        "path": display_path,
        "entries": entries,
        "entry_count": len(entries),
        "limit": bounded_limit,
        "persisted": persisted,
        "bytes_appended": bytes_appended,
        "record_digest": record_digest,
        "modifies_files": persisted,
        "security": _security_flags(),
    }


def _display_path(path: Path, *, scope_root: Path | None = None) -> str:
    root = (scope_root or Path.cwd()).resolve()
    try:
        return str(path.resolve(strict=False).relative_to(root))
    except ValueError:
        return str(path)


def _security_flags() -> dict[str, bool]:
    return {
        "local_only": True,
        "rejects_secret_shaped_content": True,
        "memory_grants_authority": False,
        "approval_from_memory": False,
        "grants_permission": False,
        "executes_tools": False,
        "external_side_effects": False,
        "starts_server": False,
        "downloads_models": False,
        "network_calls": False,
    }


def _blocked_payload(*, reason: str, action: str | None, context_kind: str | None, project_id: str | None) -> dict[str, Any]:
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "memory-context",
        "schema_version": _MEMORY_CONTEXT_VERSION,
        "status": "blocked",
        "overall": "blocked",
        "reason": reason,
        "memory_action": action or "show",
        "context_kind": context_kind or "project",
        "project_id": project_id or "default",
        "entries": [],
        "entry_count": 0,
        "persisted": False,
        "modifies_files": False,
        "security": _security_flags(),
    }


def render_memory_context(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway memory-context: {payload['overall']}",
        f"version: {payload['version']}",
        f"schema_version: {payload['schema_version']}",
        f"action: {payload['memory_action']}",
        f"context_kind: {payload['context_kind']}",
        f"project_id: {payload['project_id']}",
        f"modifies_files: {str(bool(payload.get('modifies_files'))).lower()}",
        "memory_grants_authority: false",
        "approval_from_memory: false",
        f"status: {payload['status']}",
        f"reason: {payload['reason']}",
    ]
    if payload.get("path"):
        lines.append(f"path: {payload['path']}")
    if payload.get("memory_id"):
        lines.append(f"memory_id: {payload['memory_id']}")
    lines.append(f"entry_count: {payload.get('entry_count', 0)}")
    for entry in payload.get("entries", []):
        lines.append(f"- {entry.get('memory_id')}: {entry.get('content', '')}")
    return "\n".join(lines)
