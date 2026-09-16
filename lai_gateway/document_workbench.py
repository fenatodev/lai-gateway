from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .document_text import (
    _ALLOWED_EXTENSIONS,
    _MAX_FILE_BYTES,
    collect_document_text_local,
    _resolve_workspace_root,
)

_DOCUMENT_WORKBENCH_VERSION = "document-workbench/v1"
_DEFAULT_MAX_RESULTS = 25
_MAX_RESULTS_LIMIT = 50
_DEFAULT_INSPECTION_CHARS = 3000
_MAX_INSPECTION_CHARS = 20000


@dataclass(frozen=True)
class DocumentCandidate:
    relative_path: str
    extension: str
    size_bytes: int
    selectable: bool = True
    content_read: bool = False
    untrusted_content: bool = True
    grants_authority: bool = False
    grants_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bounded_max_results(value: int | None) -> int:
    if value is None:
        return _DEFAULT_MAX_RESULTS
    return max(1, min(int(value), _MAX_RESULTS_LIMIT))


def _bounded_max_chars(value: int | None) -> int:
    if value is None:
        return _DEFAULT_INSPECTION_CHARS
    return max(1, min(int(value), _MAX_INSPECTION_CHARS))


def _safe_relative(path: Path, workspace: Path) -> str:
    return path.relative_to(workspace).as_posix()


def _candidate_from_entry(entry: Path, workspace: Path) -> tuple[DocumentCandidate | None, str | None]:
    try:
        if entry.is_symlink():
            return None, "symlink skipped"
        if not entry.is_file():
            return None, "non-file skipped"
        extension = entry.suffix.lower()
        if extension not in _ALLOWED_EXTENSIONS:
            return None, "unsupported extension skipped"
        size = entry.stat().st_size
        if size > _MAX_FILE_BYTES:
            return None, "oversize file skipped"
        return DocumentCandidate(
            relative_path=_safe_relative(entry, workspace),
            extension=extension,
            size_bytes=size,
        ), None
    except OSError as exc:
        return None, f"file skipped: {exc.__class__.__name__}"


def _list_top_level_candidates(workspace: Path, *, max_results: int) -> tuple[list[DocumentCandidate], int]:
    candidates: list[DocumentCandidate] = []
    skipped = 0
    for entry in sorted(workspace.iterdir(), key=lambda item: item.name.lower()):
        candidate, reason = _candidate_from_entry(entry, workspace)
        if candidate is None:
            skipped += 1 if reason else 0
            continue
        candidates.append(candidate)
        if len(candidates) >= max_results:
            break
    return candidates, skipped


def collect_document_workbench(
    *,
    workspace_root: str | Path | None,
    selected_relative_path: str | Path | None = None,
    max_results: int | None = None,
    max_chars: int | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    result_limit = _bounded_max_results(max_results)
    char_limit = _bounded_max_chars(max_chars)
    display_workspace = str(workspace_root or "")
    selected = str(selected_relative_path or "").strip()
    try:
        workspace = _resolve_workspace_root(workspace_root, scope_root=scope_root)
        candidates, skipped = _list_top_level_candidates(workspace, max_results=result_limit)
        inspection = None
        status = "ready"
        reason = "restricted document workbench state built; selection is metadata-only"
        if selected:
            inspection = collect_document_text_local(
                workspace_root=str(workspace),
                relative_path=selected,
                max_chars=char_limit,
                scope_root=scope_root,
            )
            status = str(inspection.get("overall", "blocked"))
            reason = "selected document inspected through document-text-local/v1"
        workbench = {
            "schema_version": _DOCUMENT_WORKBENCH_VERSION,
            "status": status,
            "workspace_root": str(workspace),
            "selected_relative_path": selected or None,
            "candidate_count": len(candidates),
            "skipped_count": skipped,
            "reason": reason,
        }
        documents = [candidate.to_dict() for candidate in candidates]
    except (OSError, ValueError) as exc:
        status = "blocked"
        workbench = {
            "schema_version": _DOCUMENT_WORKBENCH_VERSION,
            "status": status,
            "workspace_root": display_workspace,
            "selected_relative_path": selected or None,
            "candidate_count": 0,
            "skipped_count": 0,
            "reason": str(exc),
        }
        documents = []
        inspection = None
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "document-workbench",
        "overall": status,
        "workbench": workbench,
        "documents": documents,
        "inspection": inspection,
        "limits": {
            "allowed_extensions": sorted(_ALLOWED_EXTENSIONS),
            "max_file_bytes": _MAX_FILE_BYTES,
            "max_results": result_limit,
            "max_chars": char_limit,
            "top_level_only": True,
            "recursive_listing": False,
            "metadata_only_selection": True,
        },
        "security": {
            "untrusted_content": True,
            "selection_grants_authority": False,
            "grants_permission": False,
            "approval_inferred": False,
            "executes_tools": False,
            "external_side_effects": False,
            "network_access": False,
            "shell_execution": False,
            "filesystem_write": False,
            "external_upload": False,
            "scans_home": False,
            "recursive_scan": False,
            "supports_pdf": False,
            "supports_ocr": False,
            "supports_office": False,
        },
    }
