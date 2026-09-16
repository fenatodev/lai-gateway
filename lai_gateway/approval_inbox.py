from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .action_proposal import collect_action_proposal
from .document_text import _resolve_workspace_root

_APPROVAL_INBOX_VERSION = "approval-inbox/v1"
_DEFAULT_INBOX_FILE = ".lai/approval-inbox.jsonl"
_MAX_INBOX_FILE_BYTES = 128 * 1024
_MAX_ENTRIES = 50
_MAX_TEXT_CHARS = 500
_ALLOWED_INBOX_ACTIONS = {"show", "enqueue"}
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
class ApprovalInboxEntry:
    approval_id: str
    schema_version: str
    status: str
    reason: str
    created_at_utc: str
    proposal_id: str
    actor: str
    domain: str
    channel: str
    autonomy: str
    capability: str
    action: str
    target: str
    data: str
    effect: str
    risk: str
    proposed_external_effect: bool
    requires_human_approval_before_execution: bool = True
    approval_record_only: bool = True
    effective_authorization: bool = False
    grants_permission: bool = False
    issues_grants: bool = False
    consumes_grants: bool = False
    dispatch_enabled: bool = False
    dispatches_adapter: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    uses_credentials: bool = False
    sends_messages: bool = False
    publishes: bool = False
    starts_server: bool = False
    calls_harness: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _safe_text(value: Any, *, default: str = "", limit: int = _MAX_TEXT_CHARS) -> tuple[str, bool]:
    text = str(value if value is not None else default).strip()
    redacted = False
    if _SECRET_RE.search(text):
        text = "[redacted]"
        redacted = True
    return text[:limit], redacted


def _safe_bool(value: Any) -> bool:
    return bool(value) is True


def _resolve_inbox_file(workspace: Path, inbox_file: str | Path | None) -> Path:
    raw = Path(str(inbox_file or _DEFAULT_INBOX_FILE).strip() or _DEFAULT_INBOX_FILE)
    if raw.is_absolute():
        raise ValueError("inbox_file must be relative to workspace_root")
    if any(part in {"", ".."} for part in raw.parts):
        raise ValueError("inbox_file must not contain traversal")
    lexical = workspace / raw
    current = lexical
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("inbox_file path must not include symlinks")
        if current == workspace:
            break
        if current.parent == current:
            break
        current = current.parent
    resolved = lexical.resolve(strict=False)
    if workspace != resolved and workspace not in resolved.parents:
        raise ValueError("inbox_file must stay inside workspace_root")
    return resolved


def _entry_from_raw(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("schema_version") != _APPROVAL_INBOX_VERSION:
        return None
    redacted_any = False
    safe: dict[str, Any] = {
        "approval_id": "",
        "schema_version": _APPROVAL_INBOX_VERSION,
        "status": "pending",
        "reason": "pending human review; not an authorization grant",
        "created_at_utc": "",
        "proposal_id": "",
        "actor": "user",
        "domain": "unknown",
        "channel": "unknown",
        "autonomy": "unknown",
        "capability": "none",
        "action": "",
        "target": "",
        "data": "",
        "effect": "",
        "risk": "unknown",
    }
    for key in tuple(safe):
        if key == "schema_version":
            continue
        safe[key], redacted = _safe_text(raw.get(key), default=str(safe[key]))
        redacted_any = redacted_any or redacted
    for flag in (
        "proposed_external_effect",
        "requires_human_approval_before_execution",
        "approval_record_only",
        "effective_authorization",
        "grants_permission",
        "issues_grants",
        "consumes_grants",
        "dispatch_enabled",
        "dispatches_adapter",
        "executes_tools",
        "external_side_effects",
        "uses_credentials",
        "sends_messages",
        "publishes",
        "starts_server",
        "calls_harness",
    ):
        safe[flag] = _safe_bool(raw.get(flag))
    safe["requires_human_approval_before_execution"] = True
    safe["approval_record_only"] = True
    for blocked_flag in (
        "effective_authorization",
        "grants_permission",
        "issues_grants",
        "consumes_grants",
        "dispatch_enabled",
        "dispatches_adapter",
        "executes_tools",
        "external_side_effects",
        "uses_credentials",
        "sends_messages",
        "publishes",
        "starts_server",
        "calls_harness",
    ):
        safe[blocked_flag] = False
    safe["secret_redacted"] = redacted_any
    return safe


def _load_entries(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not path.exists():
        return [], {"content_read": False, "inbox_sha256": None, "size_bytes": None}
    if not path.is_file():
        raise ValueError("inbox_file must point to a regular file")
    size = path.stat().st_size
    if size > _MAX_INBOX_FILE_BYTES:
        raise ValueError("approval inbox file exceeds size limit")
    raw = path.read_bytes()
    if _SECRET_RE.search(raw.decode("utf-8", errors="replace")):
        raise ValueError("approval inbox contains secret-shaped content and was not returned")
    entries: list[dict[str, Any]] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("approval inbox file must contain JSONL objects") from exc
        entry = _entry_from_raw(item)
        if entry is not None:
            entries.append(entry)
    digest = hashlib.sha256(raw).hexdigest()
    return entries[-_MAX_ENTRIES:], {"content_read": True, "inbox_sha256": digest, "size_bytes": size}


def _entry_from_proposal(proposal_payload: dict[str, Any], existing_count: int) -> ApprovalInboxEntry:
    proposal = proposal_payload.get("proposal") or {}
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    material = (
        _APPROVAL_INBOX_VERSION,
        str(proposal.get("proposal_id") or ""),
        str(existing_count),
        created,
        str(proposal.get("action") or ""),
        str(proposal.get("target") or ""),
    )
    return ApprovalInboxEntry(
        approval_id="ai-" + _digest(material),
        schema_version=_APPROVAL_INBOX_VERSION,
        status="pending",
        reason="pending human review; not an authorization grant",
        created_at_utc=created,
        proposal_id=str(proposal.get("proposal_id") or ""),
        actor=str(proposal.get("actor") or "user"),
        domain=str(proposal.get("domain") or "unknown"),
        channel=str(proposal.get("channel") or "unknown"),
        autonomy=str(proposal.get("autonomy") or "unknown"),
        capability=str(proposal.get("capability") or "none"),
        action=str(proposal.get("action") or ""),
        target=str(proposal.get("target") or ""),
        data=str(proposal.get("data") or ""),
        effect=str(proposal.get("effect") or ""),
        risk=str(proposal.get("risk") or "unknown"),
        proposed_external_effect=bool(proposal.get("proposed_external_effect")),
    )


def _proposal_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    proposal = payload.get("proposal") or {}
    return {
        "operation": payload.get("operation"),
        "schema_version": payload.get("schema_version"),
        "overall": payload.get("overall"),
        "proposal_id": proposal.get("proposal_id"),
        "status": proposal.get("status"),
        "reason": proposal.get("reason"),
        "domain": proposal.get("domain"),
        "channel": proposal.get("channel"),
        "autonomy": proposal.get("autonomy"),
        "capability": proposal.get("capability"),
        "action": proposal.get("action"),
        "target": proposal.get("target"),
        "data": proposal.get("data"),
        "effect": proposal.get("effect"),
        "risk": proposal.get("risk"),
        "proposed_external_effect": bool(proposal.get("proposed_external_effect")),
        "effective_authorization": False,
        "issues_grants": False,
        "consumes_grants": False,
        "dispatch_enabled": False,
        "executes_tools": False,
        "external_side_effects": False,
    }


def collect_approval_inbox(
    *,
    workspace_root: str | Path | None = ".",
    inbox_file: str | Path | None = None,
    inbox_action: str | None = "show",
    state_file: str | Path | None = None,
    task_id: str | None = None,
    actor: str | None = None,
    domain: str | None = None,
    channel: str | None = None,
    autonomy: str | None = None,
    capability: str | None = None,
    target: str | None = None,
    action: str | None = None,
    data: str | None = None,
    effect: str | None = None,
    risk: str | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    selected_action = str(inbox_action or "show").strip().lower().replace("_", "-")
    if selected_action not in _ALLOWED_INBOX_ACTIONS:
        selected_action = "show"
    display_workspace = str(workspace_root or "")
    display_inbox_file = str(inbox_file or _DEFAULT_INBOX_FILE)
    proposal_payload: dict[str, Any] | None = None
    try:
        workspace = _resolve_workspace_root(workspace_root, scope_root=scope_root)
        inbox_path = _resolve_inbox_file(workspace, inbox_file)
        entries, evidence = _load_entries(inbox_path)
        wrote = False
        reason = "approval inbox loaded from explicit workspace"
        overall = "ready" if entries else "empty"
        if selected_action == "enqueue":
            proposal_payload = collect_action_proposal(
                workspace_root=workspace,
                state_file=state_file,
                task_id=task_id,
                actor=actor,
                domain=domain,
                channel=channel,
                autonomy=autonomy,
                capability=capability,
                action=action,
                target=target,
                data=data,
                effect=effect,
                risk=risk,
                scope_root=scope_root,
            )
            proposal = proposal_payload.get("proposal", {})
            if proposal_payload.get("overall") == "blocked" or proposal.get("status") != "ready":
                overall = "needs_proposal"
                reason = "proposal must be ready before it can enter approval inbox"
            else:
                entry = _entry_from_proposal(proposal_payload, len(entries))
                inbox_path.parent.mkdir(parents=True, exist_ok=True)
                serialized = json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True)
                if _SECRET_RE.search(serialized):
                    raise ValueError("approval entry contains secret-shaped content and was not persisted")
                with inbox_path.open("a", encoding="utf-8") as handle:
                    handle.write(serialized + "\n")
                wrote = True
                entries, evidence = _load_entries(inbox_path)
                overall = "ready"
                reason = "pending approval persisted as sanitized inbox record"
        data_touched = {
            "workspace_root": str(workspace),
            "inbox_file": inbox_path.relative_to(workspace).as_posix(),
            "content_read": evidence["content_read"],
            "proposal_fields_read": selected_action == "enqueue",
            "filesystem_write": wrote,
            "recursive_scan": False,
            "home_scan": False,
            "implicit_ingestion": False,
        }
        storage = {
            "inbox_file_exists": inbox_path.exists(),
            "inbox_sha256": evidence["inbox_sha256"],
            "size_bytes": evidence["size_bytes"],
            "resolved_inbox_path": str(inbox_path),
        }
    except (OSError, ValueError) as exc:
        entries = []
        overall = "blocked"
        reason = str(exc)
        wrote = False
        data_touched = {
            "workspace_root": display_workspace,
            "inbox_file": display_inbox_file,
            "content_read": False,
            "proposal_fields_read": selected_action == "enqueue",
            "filesystem_write": False,
            "recursive_scan": False,
            "home_scan": False,
            "implicit_ingestion": False,
        }
        storage = {
            "inbox_file_exists": False,
            "inbox_sha256": None,
            "size_bytes": None,
            "resolved_inbox_path": None,
        }
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "approval-inbox",
        "schema_version": _APPROVAL_INBOX_VERSION,
        "overall": overall,
        "inbox_action": selected_action,
        "inbox": {
            "status": overall,
            "reason": reason,
            "pending_count": len(entries),
            "entries": entries,
        },
        "proposal": _proposal_summary(proposal_payload),
        "data_touched": data_touched,
        "storage": storage,
        "limits": {
            "default_inbox_file": _DEFAULT_INBOX_FILE,
            "max_inbox_file_bytes": _MAX_INBOX_FILE_BYTES,
            "max_entries": _MAX_ENTRIES,
            "max_text_chars": _MAX_TEXT_CHARS,
            "allowed_inbox_actions": sorted(_ALLOWED_INBOX_ACTIONS),
        },
        "security": {
            "read_only_when_showing": selected_action == "show",
            "filesystem_write": wrote,
            "approval_record_only": True,
            "approval_inferred": False,
            "content_grants_authority": False,
            "effective_authorization": False,
            "capabilities_granted": [],
            "issues_grants": False,
            "consumes_grants": False,
            "grants_permission": False,
            "grants_permissions": False,
            "dispatch_enabled": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "calls_harness": False,
            "network_access": False,
            "shell_execution": False,
            "starts_server": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
            "secret_redacted": False,
        },
    }


def render_approval_inbox(payload: dict[str, Any]) -> str:
    inbox = payload.get("inbox", {})
    lines = [
        f"lai-gateway approval-inbox: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _APPROVAL_INBOX_VERSION)}",
        f"inbox_action: {payload.get('inbox_action', 'show')}",
        f"pending_count: {inbox.get('pending_count', 0)}",
        "approval_record_only: true",
        "effective_authorization: false",
        f"filesystem_write: {str(payload.get('data_touched', {}).get('filesystem_write', False)).lower()}",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "external_side_effects: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
        f"reason: {inbox.get('reason', '')}",
    ]
    for entry in (inbox.get("entries") or [])[:5]:
        lines.append(
            f"pending: {entry.get('approval_id')} {entry.get('capability')} [{entry.get('risk')}] {entry.get('target')}"
        )
    return "\n".join(lines)
