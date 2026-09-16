from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .document_text import collect_document_text_local, _resolve_workspace_root
from .memory_context import collect_memory_context
from .objective_state import collect_objective_state

_CONTEXT_PACK_VERSION = "context-pack/v1"
_DEFAULT_STATE_FILE = ".lai/objective-state.json"
_DEFAULT_MEMORY_DIR = ".lai/memory"
_DEFAULT_CONTEXT_KIND = "project"
_MAX_DOCUMENTS = 5
_DEFAULT_MAX_DOCUMENT_CHARS = 2000
_MAX_DOCUMENT_CHARS = 8000
_DEFAULT_MEMORY_LIMIT = 5
_MAX_MEMORY_LIMIT = 20
_MAX_SOURCE_TEXT_CHARS = 2000
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
class ContextPackSource:
    source_id: str
    source_type: str
    status: str
    title: str
    content: str
    metadata: dict[str, Any]
    untrusted_content: bool = True
    grants_permission: bool = False
    grants_authority: bool = False
    approval_inferred: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _bounded_int(value: int | None, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, *, limit: int = _MAX_SOURCE_TEXT_CHARS) -> tuple[str, bool]:
    text = str(value if value is not None else "").strip()
    if _SECRET_RE.search(text):
        return "[redacted]", True
    return text[:limit], False


def _safe_label(value: Any, *, default: str = "default") -> tuple[str, bool]:
    text, redacted = _safe_text(value, limit=96)
    label = text.lower().replace(" ", "-") if text != "[redacted]" else text
    return label or default, redacted


def _normalize_documents(documents: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if documents is None:
        return []
    raw_items: list[str]
    if isinstance(documents, str):
        raw_items = [documents]
    else:
        raw_items = list(documents)
    normalized: list[str] = []
    for item in raw_items:
        for part in str(item or "").split(","):
            candidate = part.strip()
            if candidate and candidate not in normalized:
                normalized.append(candidate)
            if len(normalized) >= _MAX_DOCUMENTS:
                return normalized
    return normalized


def _select_task(tasks: list[dict[str, Any]], task_id: str | None) -> dict[str, Any] | None:
    if task_id:
        for task in tasks:
            if str(task.get("task_id") or task.get("id") or "") == task_id:
                return task
        return None
    for task in tasks:
        if str(task.get("status") or "unknown") not in {"done", "blocked"}:
            return task
    return tasks[0] if tasks else None


def _source(source_type: str, status: str, title: str, content: Any, metadata: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    safe_title, title_redacted = _safe_text(title, limit=160)
    safe_content, content_redacted = _safe_text(content)
    source_id = "ctx-" + _digest((_CONTEXT_PACK_VERSION, source_type, status, safe_title, safe_content))
    item = ContextPackSource(
        source_id=source_id,
        source_type=source_type,
        status=status,
        title=safe_title,
        content=safe_content,
        metadata=metadata,
    ).to_dict()
    return item, title_redacted or content_redacted


def _objective_sources(payload: dict[str, Any], task_id: str | None) -> tuple[list[dict[str, Any]], bool, str | None]:
    state = payload.get("state") or {}
    sources: list[dict[str, Any]] = []
    redacted = False
    project_id = state.get("project_id")
    if state.get("objective"):
        item, item_redacted = _source(
            "objective",
            str(state.get("status") or payload.get("overall") or "unknown"),
            "objective",
            state.get("objective"),
            {"project_id": project_id, "objective_status": state.get("objective_status")},
        )
        sources.append(item)
        redacted = redacted or item_redacted
    task = _select_task(list(state.get("tasks") or []), task_id)
    if task:
        item, item_redacted = _source(
            "objective-task",
            str(task.get("status") or "unknown"),
            task.get("title") or "task",
            task.get("target") or task.get("title") or "",
            {
                "task_id": task.get("task_id"),
                "domain": task.get("domain"),
                "channel": task.get("channel"),
                "autonomy": task.get("autonomy"),
                "capability": task.get("capability"),
                "risk": task.get("risk"),
            },
        )
        sources.append(item)
        redacted = redacted or item_redacted
    return sources, redacted, str(project_id or "") or None


def _memory_sources(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    sources: list[dict[str, Any]] = []
    redacted = False
    for entry in payload.get("entries") or []:
        content = entry.get("content") or ""
        item, item_redacted = _source(
            "memory",
            "ready",
            entry.get("memory_id") or "memory",
            content,
            {
                "memory_id": entry.get("memory_id"),
                "context_kind": entry.get("context_kind"),
                "project_id": entry.get("project_id"),
                "content_sha256": entry.get("content_sha256"),
                "created_at_utc": entry.get("created_at_utc"),
            },
        )
        sources.append(item)
        redacted = redacted or item_redacted
    return sources, redacted


def _document_source(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    doc = payload.get("document") or {}
    if payload.get("overall") == "blocked":
        return None, False
    item, redacted = _source(
        "document",
        str(payload.get("overall") or doc.get("status") or "unknown"),
        doc.get("relative_path") or "document",
        doc.get("text_preview") or "",
        {
            "relative_path": doc.get("relative_path"),
            "extension": doc.get("extension"),
            "size_bytes": doc.get("size_bytes"),
            "sha256": doc.get("sha256"),
            "text_truncated": doc.get("text_truncated"),
        },
    )
    return item, redacted


def collect_context_pack(
    *,
    workspace_root: str | Path | None = ".",
    state_file: str | Path | None = None,
    task_id: str | None = None,
    project_id: str | None = None,
    context_kind: str | None = _DEFAULT_CONTEXT_KIND,
    memory_dir: str | Path | None = None,
    documents: list[str] | tuple[str, ...] | str | None = None,
    max_document_chars: int | None = None,
    memory_limit: int | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    doc_limit = _bounded_int(max_document_chars, default=_DEFAULT_MAX_DOCUMENT_CHARS, maximum=_MAX_DOCUMENT_CHARS)
    mem_limit = _bounded_int(memory_limit, default=_DEFAULT_MEMORY_LIMIT, maximum=_MAX_MEMORY_LIMIT)
    selected_documents = _normalize_documents(documents)
    display_workspace = str(workspace_root or "")
    try:
        workspace = _resolve_workspace_root(workspace_root, scope_root=scope_root)
        objective_payload = collect_objective_state(
            workspace_root=str(workspace),
            state_file=state_file,
            scope_root=workspace,
        )
        objective_source_items, objective_redacted, objective_project = _objective_sources(objective_payload, task_id)
        context_project, project_redacted = _safe_label(project_id or objective_project or "default", default="default")
        memory_payload = collect_memory_context(
            memory_action="show",
            context_kind=context_kind or _DEFAULT_CONTEXT_KIND,
            project_id=context_project,
            memory_dir=memory_dir or _DEFAULT_MEMORY_DIR,
            scope_root=workspace,
            limit=mem_limit,
            actor="user",
            channel="context-pack",
            domain="local_context",
        )
        memory_source_items, memory_redacted = _memory_sources(memory_payload)
        document_payloads = []
        document_source_items: list[dict[str, Any]] = []
        document_redacted = False
        blocked_reasons = []
        for relative_path in selected_documents:
            document_payload = collect_document_text_local(
                workspace_root=str(workspace),
                relative_path=relative_path,
                max_chars=doc_limit,
                scope_root=workspace,
            )
            document_payloads.append(document_payload)
            if document_payload.get("overall") == "blocked":
                blocked_reasons.append((document_payload.get("document") or {}).get("reason") or "document blocked")
                continue
            item, item_redacted = _document_source(document_payload)
            if item:
                document_source_items.append(item)
            document_redacted = document_redacted or item_redacted
        sources = objective_source_items + memory_source_items + document_source_items
        if objective_payload.get("overall") == "blocked":
            overall = "blocked"
            reason = "objective state source is blocked; context pack not trusted"
        elif memory_payload.get("overall") == "blocked":
            overall = "blocked"
            reason = "memory context source is blocked; context pack not trusted"
        elif blocked_reasons:
            overall = "blocked"
            reason = "selected document source is blocked: " + "; ".join(blocked_reasons[:3])
        else:
            overall = "ready"
            reason = "context pack built from explicit local project, memory and document selections"
        redacted_any = objective_redacted or memory_redacted or document_redacted or project_redacted
        pack_id = "cp-" + _digest((
            _CONTEXT_PACK_VERSION,
            overall,
            str(workspace),
            context_project,
            ",".join(selected_documents),
            str(len(sources)),
        ))
        workspace_display = str(workspace)
    except (OSError, ValueError) as exc:
        objective_payload = None
        memory_payload = None
        document_payloads = []
        sources = []
        context_project = str(project_id or "default")
        overall = "blocked"
        reason = str(exc)
        redacted_any = False
        pack_id = "cp-" + _digest((_CONTEXT_PACK_VERSION, "blocked", display_workspace, reason))
        workspace_display = display_workspace
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "context-pack",
        "schema_version": _CONTEXT_PACK_VERSION,
        "overall": overall,
        "reason": reason,
        "context_pack": {
            "context_pack_id": pack_id,
            "status": overall,
            "workspace_root": workspace_display,
            "project_id": context_project,
            "context_kind": context_kind or _DEFAULT_CONTEXT_KIND,
            "task_id": task_id,
            "source_count": len(sources),
            "sources": sources,
            "untrusted_content": True,
            "explicit_selection_required": True,
            "embeddings_required": False,
        },
        "sources": {
            "objective_state": {
                "included": objective_payload is not None,
                "overall": objective_payload.get("overall") if objective_payload else None,
                "state_file": state_file or _DEFAULT_STATE_FILE,
            },
            "memory_context": {
                "included": memory_payload is not None,
                "overall": memory_payload.get("overall") if memory_payload else None,
                "project_id": context_project,
                "entry_count": memory_payload.get("entry_count") if memory_payload else 0,
            },
            "documents": {
                "requested": selected_documents,
                "included_count": len(document_source_items) if 'document_source_items' in locals() else 0,
                "results": [
                    {
                        "overall": item.get("overall"),
                        "relative_path": (item.get("document") or {}).get("relative_path"),
                        "reason": (item.get("document") or {}).get("reason"),
                    }
                    for item in document_payloads
                ],
            },
        },
        "data_touched": {
            "workspace_root": workspace_display,
            "state_file": str(state_file or _DEFAULT_STATE_FILE),
            "memory_dir": str(memory_dir or _DEFAULT_MEMORY_DIR),
            "project_id": context_project,
            "selected_documents": selected_documents,
            "objective_state_read": bool(objective_payload and objective_payload.get("overall") != "needs_state"),
            "memory_entries_read": int(memory_payload.get("entry_count") if memory_payload else 0),
            "document_count_read": len(document_payloads),
            "filesystem_write": False,
            "recursive_scan": False,
            "home_scan": False,
            "implicit_ingestion": False,
            "network_access": False,
        },
        "limits": {
            "max_documents": _MAX_DOCUMENTS,
            "max_document_chars": doc_limit,
            "memory_limit": mem_limit,
            "embeddings_required": False,
            "top_level_listing": False,
            "recursive_scan": False,
        },
        "security": {
            "read_only": True,
            "untrusted_content": True,
            "content_grants_authority": False,
            "memory_grants_authority": False,
            "document_grants_authority": False,
            "approval_inferred": False,
            "effective_authorization": False,
            "capabilities_granted": [],
            "grants_permission": False,
            "grants_permissions": False,
            "issues_grants": False,
            "consumes_grants": False,
            "dispatch_enabled": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "calls_harness": False,
            "starts_server": False,
            "network_access": False,
            "shell_execution": False,
            "filesystem_write": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
            "embeddings_required": False,
            "embedding_generation": False,
            "secret_redacted": redacted_any,
        },
    }


def render_context_pack(payload: dict[str, Any]) -> str:
    pack = payload.get("context_pack") or {}
    lines = [
        f"lai-gateway context-pack: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _CONTEXT_PACK_VERSION)}",
        f"context_pack_id: {pack.get('context_pack_id') or 'none'}",
        f"project_id: {pack.get('project_id') or 'default'}",
        f"source_count: {pack.get('source_count', 0)}",
        "read_only: true",
        "untrusted_content: true",
        "content_grants_authority: false",
        "effective_authorization: false",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "external_side_effects: false",
        "filesystem_write: false",
        "recursive_scan: false",
        "home_scan: false",
        "implicit_ingestion: false",
        "embeddings_required: false",
        f"reason: {payload.get('reason', '')}",
    ]
    for source in (pack.get("sources") or [])[:8]:
        title = source.get("title") or source.get("source_type") or "source"
        lines.append(f"source: {source.get('source_type')} {source.get('status')} {title}")
    return "\n".join(lines)
