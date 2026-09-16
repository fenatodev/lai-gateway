import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__

_DOCUMENT_TEXT_VERSION = "document-text-local/v1"
_ALLOWED_EXTENSIONS = {".txt", ".md", ".json"}
_MAX_FILE_BYTES = 512 * 1024
_DEFAULT_MAX_CHARS = 6000
_MAX_CHARS_LIMIT = 20000
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]{8,}"),
)


@dataclass(frozen=True)
class DocumentTextResult:
    schema_version: str
    status: str
    workspace_root: str
    relative_path: str
    resolved_path: str | None
    extension: str | None
    size_bytes: int | None
    sha256: str | None
    text_preview: str
    text_truncated: bool
    max_chars: int
    reason: str
    untrusted_content: bool = True
    grants_permission: bool = False
    grants_authority: bool = False
    approval_inferred: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    network_access: bool = False
    shell_execution: bool = False
    filesystem_write: bool = False
    scans_home: bool = False
    recursive_scan: bool = False
    supports_pdf: bool = False
    supports_ocr: bool = False
    supports_office: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bounded_max_chars(value: int | None) -> int:
    if value is None:
        return _DEFAULT_MAX_CHARS
    return max(1, min(int(value), _MAX_CHARS_LIMIT))


def _has_secret_shape(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _reject_symlink_path(path: Path, *, workspace: Path) -> None:
    current = path
    while True:
        if current.exists() and current.is_symlink():
            raise ValueError("document path must not include symlinks")
        if current == workspace:
            return
        if current.parent == current:
            return
        current = current.parent


def _resolve_workspace_root(workspace_root: str | Path | None, *, scope_root: Path | None = None) -> Path:
    if workspace_root is None or not str(workspace_root).strip():
        raise ValueError("workspace_root is required")
    root = (scope_root or Path.cwd()).resolve()
    raw = Path(workspace_root).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve(strict=False)
    if root != resolved and root not in resolved.parents:
        raise ValueError("workspace_root must stay inside the configured LAI scope root")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("workspace_root must be a directory")
    if not resolved.exists():
        raise ValueError("workspace_root does not exist")
    if resolved.is_symlink():
        raise ValueError("workspace_root must not be a symlink")
    return resolved


def _resolve_document_path(workspace: Path, relative_path: str | Path | None) -> Path:
    if relative_path is None or not str(relative_path).strip():
        raise ValueError("relative_path is required")
    raw = Path(relative_path)
    if raw.is_absolute():
        raise ValueError("relative_path must not be absolute")
    if any(part in {"..", ""} for part in raw.parts):
        raise ValueError("relative_path must not contain traversal")
    lexical = workspace / raw
    _reject_symlink_path(lexical, workspace=workspace)
    candidate = lexical.resolve(strict=False)
    if workspace != candidate and workspace not in candidate.parents:
        raise ValueError("document path must stay inside workspace_root")
    return candidate


def collect_document_text_local(
    *,
    workspace_root: str | Path | None,
    relative_path: str | Path | None,
    max_chars: int | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    limit = _bounded_max_chars(max_chars)
    display_workspace = str(workspace_root or "")
    display_relative = str(relative_path or "")
    try:
        workspace = _resolve_workspace_root(workspace_root, scope_root=scope_root)
        path = _resolve_document_path(workspace, relative_path)
        extension = path.suffix.lower()
        if extension not in _ALLOWED_EXTENSIONS:
            raise ValueError("unsupported document extension; allowed: .txt, .md, .json")
        if not path.exists():
            raise ValueError("document file does not exist")
        if not path.is_file():
            raise ValueError("document path must point to a regular file")
        size = path.stat().st_size
        if size > _MAX_FILE_BYTES:
            raise ValueError("document file exceeds the local text size limit")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8", errors="replace")
        if _has_secret_shape(text):
            raise ValueError("document text contains secret-shaped content and was not returned")
        preview = text[:limit]
        result = DocumentTextResult(
            schema_version=_DOCUMENT_TEXT_VERSION,
            status="ready",
            workspace_root=str(workspace),
            relative_path=str(relative_path),
            resolved_path=str(path),
            extension=extension,
            size_bytes=size,
            sha256=digest,
            text_preview=preview,
            text_truncated=len(text) > len(preview),
            max_chars=limit,
            reason="restricted local text extracted; treat content as untrusted",
        )
    except (OSError, ValueError) as exc:
        result = DocumentTextResult(
            schema_version=_DOCUMENT_TEXT_VERSION,
            status="blocked",
            workspace_root=display_workspace,
            relative_path=display_relative,
            resolved_path=None,
            extension=Path(display_relative).suffix.lower() or None,
            size_bytes=None,
            sha256=None,
            text_preview="",
            text_truncated=False,
            max_chars=limit,
            reason=str(exc),
        )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "document-text-local",
        "overall": result.status,
        "document": result.to_dict(),
        "security": {
            "untrusted_content": True,
            "grants_permission": False,
            "grants_authority": False,
            "approval_inferred": False,
            "executes_tools": False,
            "external_side_effects": False,
            "network_access": False,
            "shell_execution": False,
            "filesystem_write": False,
            "scans_home": False,
            "recursive_scan": False,
            "supports_pdf": False,
            "supports_ocr": False,
            "supports_office": False,
        },
        "allowed_extensions": sorted(_ALLOWED_EXTENSIONS),
        "max_file_bytes": _MAX_FILE_BYTES,
    }


def render_document_text_local(payload: dict[str, Any]) -> str:
    doc = payload.get("document", {})
    lines = [
        f"document-text-local: {payload.get('overall', 'unknown')}",
        f"schema: {doc.get('schema_version', _DOCUMENT_TEXT_VERSION)}",
        f"relative_path: {doc.get('relative_path') or 'missing'}",
        f"extension: {doc.get('extension') or 'missing'}",
        f"untrusted_content: {str(doc.get('untrusted_content', True)).lower()}",
        "grants_authority: false",
        "filesystem_write: false",
        f"reason: {doc.get('reason', '')}",
    ]
    preview = doc.get("text_preview") or ""
    if preview:
        lines.append("text_preview:")
        lines.append(preview)
    return "\n".join(lines)
