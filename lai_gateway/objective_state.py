from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .document_text import _resolve_workspace_root

_OBJECTIVE_STATE_VERSION = "objective-state/v1"
_DEFAULT_STATE_FILE = ".lai/objective-state.json"
_MAX_STATE_FILE_BYTES = 64 * 1024
_MAX_TEXT_CHARS = 500
_MAX_TASKS = 25
_MAX_CHECKPOINTS = 25
_ALLOWED_OBJECTIVE_STATUSES = {"active", "blocked", "done", "paused", "unknown"}
_ALLOWED_TASK_STATUSES = {"blocked", "done", "doing", "todo", "unknown"}
_ALLOWED_RISKS = {"low", "medium", "high", "unknown"}
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
class ObjectiveTask:
    task_id: str
    title: str
    status: str
    domain: str
    channel: str
    autonomy: str
    capability: str
    target: str
    risk: str
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObjectiveCheckpoint:
    checkpoint_id: str
    summary: str
    created_at_utc: str | None
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bounded_text(value: Any, *, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text[:_MAX_TEXT_CHARS]


def _bounded_label(value: Any, *, default: str = "unknown") -> str:
    label = _bounded_text(value, default=default).lower().replace(" ", "-")
    return label or default


def _normalize_status(value: Any, allowed: set[str]) -> str:
    status = _bounded_label(value)
    return status if status in allowed else "unknown"


def _normalize_risk(value: Any) -> str:
    risk = _bounded_label(value)
    return risk if risk in _ALLOWED_RISKS else "unknown"


def _resolve_state_file(workspace: Path, state_file: str | Path | None) -> Path:
    raw = Path(str(state_file or _DEFAULT_STATE_FILE).strip() or _DEFAULT_STATE_FILE)
    if raw.is_absolute():
        raise ValueError("state_file must be relative to workspace_root")
    if any(part in {"", ".."} for part in raw.parts):
        raise ValueError("state_file must not contain traversal")
    lexical = workspace / raw
    current = lexical
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("state_file path must not include symlinks")
        if current == workspace:
            break
        if current.parent == current:
            break
        current = current.parent
    resolved = lexical.resolve(strict=False)
    if workspace != resolved and workspace not in resolved.parents:
        raise ValueError("state_file must stay inside workspace_root")
    return resolved


def _normalize_task(raw: Any, index: int) -> ObjectiveTask:
    item = raw if isinstance(raw, dict) else {}
    return ObjectiveTask(
        task_id=_bounded_text(item.get("id") or item.get("task_id") or f"task-{index + 1}"),
        title=_bounded_text(item.get("title") or item.get("summary") or "untitled task"),
        status=_normalize_status(item.get("status"), _ALLOWED_TASK_STATUSES),
        domain=_bounded_label(item.get("domain"), default="project"),
        channel=_bounded_label(item.get("channel"), default="local"),
        autonomy=_bounded_label(item.get("autonomy"), default="none"),
        capability=_bounded_label(item.get("capability"), default="none"),
        target=_bounded_text(item.get("target"), default=""),
        risk=_normalize_risk(item.get("risk")),
    )


def _normalize_checkpoint(raw: Any, index: int) -> ObjectiveCheckpoint:
    item = raw if isinstance(raw, dict) else {}
    return ObjectiveCheckpoint(
        checkpoint_id=_bounded_text(item.get("id") or item.get("checkpoint_id") or f"checkpoint-{index + 1}"),
        summary=_bounded_text(item.get("summary") or item.get("title") or "checkpoint"),
        created_at_utc=_bounded_text(item.get("created_at_utc") or item.get("created_at"), default="") or None,
    )


def _empty_state(*, status: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": _OBJECTIVE_STATE_VERSION,
        "status": status,
        "project_id": None,
        "objective": "",
        "objective_status": "unknown",
        "tasks": [],
        "checkpoints": [],
        "reason": reason,
    }


def _load_state(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.exists():
        return _empty_state(status="needs_state", reason="objective state file not found"), {
            "content_read": False,
            "state_sha256": None,
            "size_bytes": None,
        }
    if not path.is_file():
        raise ValueError("state_file must point to a regular file")
    size = path.stat().st_size
    if size > _MAX_STATE_FILE_BYTES:
        raise ValueError("objective state file exceeds size limit")
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if _SECRET_RE.search(text):
        raise ValueError("objective state contains secret-shaped content and was not returned")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("objective state file must be valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("objective state file must contain a JSON object")
    if data.get("schema_version") not in {_OBJECTIVE_STATE_VERSION, None}:
        raise ValueError("objective state schema_version is unsupported")
    tasks = [_normalize_task(item, index) for index, item in enumerate(data.get("tasks") or [])][:_MAX_TASKS]
    checkpoints = [
        _normalize_checkpoint(item, index)
        for index, item in enumerate(data.get("checkpoints") or [])
    ][:_MAX_CHECKPOINTS]
    state = {
        "schema_version": _OBJECTIVE_STATE_VERSION,
        "status": "ready",
        "project_id": _bounded_text(data.get("project_id"), default="default") or "default",
        "objective": _bounded_text(data.get("objective") or data.get("summary"), default=""),
        "objective_status": _normalize_status(data.get("objective_status") or data.get("status"), _ALLOWED_OBJECTIVE_STATUSES),
        "tasks": [task.to_dict() for task in tasks],
        "checkpoints": [checkpoint.to_dict() for checkpoint in checkpoints],
        "reason": "objective state loaded read-only from explicit workspace",
    }
    return state, {"content_read": True, "state_sha256": _digest(raw), "size_bytes": size}


def collect_objective_state(
    *,
    workspace_root: str | Path | None,
    state_file: str | Path | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    display_workspace = str(workspace_root or "")
    display_state_file = str(state_file or _DEFAULT_STATE_FILE)
    try:
        workspace = _resolve_workspace_root(workspace_root, scope_root=scope_root)
        state_path = _resolve_state_file(workspace, state_file)
        state, evidence = _load_state(state_path)
        overall = state["status"]
        data_touched = {
            "workspace_root": str(workspace),
            "state_file": state_path.relative_to(workspace).as_posix(),
            "content_read": evidence["content_read"],
            "recursive_scan": False,
            "home_scan": False,
            "filesystem_write": False,
        }
        storage = {
            "state_file_exists": state_path.exists(),
            "state_sha256": evidence["state_sha256"],
            "size_bytes": evidence["size_bytes"],
            "resolved_state_path": str(state_path),
        }
    except (OSError, ValueError) as exc:
        overall = "blocked"
        state = _empty_state(status="blocked", reason=str(exc))
        data_touched = {
            "workspace_root": display_workspace,
            "state_file": display_state_file,
            "content_read": False,
            "recursive_scan": False,
            "home_scan": False,
            "filesystem_write": False,
        }
        storage = {
            "state_file_exists": False,
            "state_sha256": None,
            "size_bytes": None,
            "resolved_state_path": None,
        }
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "objective-state",
        "schema_version": _OBJECTIVE_STATE_VERSION,
        "overall": overall,
        "state": state,
        "data_touched": data_touched,
        "storage": storage,
        "limits": {
            "default_state_file": _DEFAULT_STATE_FILE,
            "max_state_file_bytes": _MAX_STATE_FILE_BYTES,
            "max_text_chars": _MAX_TEXT_CHARS,
            "max_tasks": _MAX_TASKS,
            "max_checkpoints": _MAX_CHECKPOINTS,
            "allowed_objective_statuses": sorted(_ALLOWED_OBJECTIVE_STATUSES),
            "allowed_task_statuses": sorted(_ALLOWED_TASK_STATUSES),
            "allowed_risks": sorted(_ALLOWED_RISKS),
        },
        "security": {
            "read_only": True,
            "untrusted_content": True,
            "content_grants_authority": False,
            "approval_inferred": False,
            "capabilities_granted": [],
            "issues_grants": False,
            "consumes_grants": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "network_access": False,
            "shell_execution": False,
            "filesystem_write": False,
            "starts_server": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
        },
    }


def render_objective_state(payload: dict[str, Any]) -> str:
    state = payload.get("state", {})
    data = payload.get("data_touched", {})
    lines = [
        f"lai-gateway objective-state: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _OBJECTIVE_STATE_VERSION)}",
        f"project_id: {state.get('project_id') or 'missing'}",
        f"objective_status: {state.get('objective_status') or 'unknown'}",
        f"task_count: {len(state.get('tasks') or [])}",
        f"checkpoint_count: {len(state.get('checkpoints') or [])}",
        f"state_file: {data.get('state_file') or 'missing'}",
        "read_only: true",
        "filesystem_write: false",
        "issues_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "implicit_ingestion: false",
        f"reason: {state.get('reason', '')}",
    ]
    objective = state.get("objective") or ""
    if objective:
        lines.append(f"objective: {objective}")
    for task in (state.get("tasks") or [])[:5]:
        lines.append(f"task: {task.get('task_id')} [{task.get('status')}] {task.get('title')}")
    return "\n".join(lines)
