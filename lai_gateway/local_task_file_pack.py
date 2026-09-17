from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import __version__
from .local_task_dry_run import collect_local_task_dry_run

_SCHEMA_VERSION = "local-task-file-pack/v1"
_DEFAULT_OUTPUT_ROOT = ".lai-ai"


def _slugify_task_id(task_id: str | None) -> str:
    raw = (task_id or "dry-run-task").strip().lower()
    raw = re.sub(r"[^a-z0-9_.-]+", "-", raw).strip(".-_")
    return raw or "dry-run-task"


def _check_output_root(output_root: str | None) -> tuple[Path, dict[str, str]]:
    raw = (output_root or _DEFAULT_OUTPUT_ROOT).strip() or _DEFAULT_OUTPUT_ROOT
    path = Path(raw)

    if path.is_absolute():
        return path, {
            "name": "path_policy:output_root",
            "status": "blocked",
            "detail": "output root must be repository-relative, not absolute",
        }

    if ".." in path.parts:
        return path, {
            "name": "path_policy:output_root",
            "status": "blocked",
            "detail": "output root must not contain parent traversal",
        }

    return path, {
        "name": "path_policy:output_root",
        "status": "ok",
        "detail": "output root is repository-relative and bounded",
    }


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def collect_local_task_file_pack(
    *,
    repo: Path | None = None,
    task_id: str | None = None,
    domain: str | None = None,
    channel: str | None = None,
    autonomy_zone: str | None = None,
    capability: str | None = None,
    intent: str | None = None,
    allowed_paths: list[str] | tuple[str, ...] | None = None,
    denied_paths: list[str] | tuple[str, ...] | None = None,
    validation_plan: list[str] | tuple[str, ...] | None = None,
    proposed_commands: list[str] | tuple[str, ...] | None = None,
    output_root: str | None = _DEFAULT_OUTPUT_ROOT,
    write: bool = False,
) -> dict[str, Any]:
    repo_root = (repo or Path.cwd()).resolve()
    root_path, root_check = _check_output_root(output_root)
    slug = _slugify_task_id(task_id)

    dry_run = collect_local_task_dry_run(
        task_id=task_id or slug,
        domain=domain,
        channel=channel,
        autonomy_zone=autonomy_zone,
        capability=capability,
        intent=intent,
        allowed_paths=allowed_paths,
        denied_paths=denied_paths,
        validation_plan=validation_plan,
        proposed_commands=proposed_commands,
    )

    task_rel = root_path / "tasks" / f"{slug}.task.json"
    outbox_rel = root_path / "outbox" / f"{slug}.outbox.json"

    checks = [
        root_check,
        {
            "name": "schema:local_task_file_pack",
            "status": "ok",
            "detail": "local-task-file-pack/v1 wraps dry-run task and outbox records",
        },
        {
            "name": "execution:disabled",
            "status": "ok",
            "detail": "file pack does not execute commands, call Harness, call tools or dispatch adapters",
        },
        {
            "name": "authorization:separate",
            "status": "ok",
            "detail": "task and outbox files never equal authorization",
        },
    ]

    if dry_run.get("overall") == "blocked":
        checks.append({
            "name": "dry_run:blocked",
            "status": "blocked",
            "detail": "underlying dry-run is blocked",
        })

    blocked = any(check["status"] == "blocked" for check in checks)

    task_record = dict(dry_run.get("task", {}))
    task_record.update({
        "file_pack_schema_version": _SCHEMA_VERSION,
        "task_file": str(task_rel),
        "outbox_file": str(outbox_rel),
        "dry_run_only": True,
        "effective_authorization": False,
    })

    outbox_record = dict(dry_run.get("outbox", {}))
    outbox_record.update({
        "file_pack_schema_version": _SCHEMA_VERSION,
        "task_file": str(task_rel),
        "outbox_file": str(outbox_rel),
        "dry_run_only": True,
        "effective_authorization": False,
        "next_action": "review file pack; execution remains unavailable",
    })

    written_files: list[str] = []
    created_dirs: list[str] = []

    if write and not blocked:
        task_abs = repo_root / task_rel
        outbox_abs = repo_root / outbox_rel
        task_abs.parent.mkdir(parents=True, exist_ok=True)
        outbox_abs.parent.mkdir(parents=True, exist_ok=True)
        task_abs.write_text(_json_text(task_record), encoding="utf-8")
        outbox_abs.write_text(_json_text(outbox_record), encoding="utf-8")
        created_dirs = [str(task_rel.parent), str(outbox_rel.parent)]
        written_files = [str(task_rel), str(outbox_rel)]

    overall = "blocked" if blocked else ("written" if write else "planned")

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-task-file-pack",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "summary": "PR124 plans or writes local task/outbox JSON files without execution.",
        "repo_root": str(repo_root),
        "output_root": str(root_path),
        "task_file": str(task_rel),
        "outbox_file": str(outbox_rel),
        "write_requested": bool(write),
        "wrote_files": bool(written_files),
        "written_files": written_files,
        "created_dirs": created_dirs,
        "task_record": task_record,
        "outbox_record": outbox_record,
        "dry_run_only": True,
        "effective_authorization": False,
        "would_execute_commands": False,
        "would_call_harness": False,
        "would_call_tools": False,
        "would_dispatch_adapter": False,
        "would_issue_grants": False,
        "would_consume_grants": False,
        "would_use_credentials": False,
        "would_send_messages": False,
        "would_publish": False,
        "would_merge_main": False,
        "checks": checks,
    }


def render_local_task_file_pack(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway local-task-file-pack: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"output_root: {payload.get('output_root', _DEFAULT_OUTPUT_ROOT)}",
        f"task_file: {payload.get('task_file', 'unknown')}",
        f"outbox_file: {payload.get('outbox_file', 'unknown')}",
        f"write_requested: {str(bool(payload.get('write_requested'))).lower()}",
        f"wrote_files: {str(bool(payload.get('wrote_files'))).lower()}",
        "dry_run_only: true",
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
    ]

    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    if checks:
        lines.append("checks:")
        for check in checks:
            lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")

    return "\n".join(lines)
