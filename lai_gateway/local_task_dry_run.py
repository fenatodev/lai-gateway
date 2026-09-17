from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import __version__

_SCHEMA_VERSION = "local-task-dry-run/v1"
_TASK_SCHEMA_VERSION = "local-task/v1"
_OUTBOX_SCHEMA_VERSION = "local-task-outbox/v1"

_ALLOWED_ZONES = {"green", "yellow", "red"}

_DEFAULT_DENIED_PATHS = (
    ".ssh/**",
    "**/.env",
    "**/*token*",
    "**/*secret*",
    "**/credentials*",
)

_PROHIBITED_OPERATIONS = (
    "sudo",
    "software_install_or_removal",
    "credential_access",
    "authenticated_browser",
    "message_sending",
    "publication",
    "form_submission",
    "purchase",
    "delete_outside_workspace",
    "merge_to_main",
    "permission_expansion",
)


@dataclass(frozen=True)
class DryRunCheck:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _clean_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _normalize_zone(zone: str | None) -> str:
    value = (zone or "green").strip().lower()
    return value if value in _ALLOWED_ZONES else "red"


def collect_local_task_dry_run(
    *,
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
) -> dict[str, Any]:
    zone = _normalize_zone(autonomy_zone)
    allowed = _clean_list(allowed_paths)
    denied = _clean_list(denied_paths) or list(_DEFAULT_DENIED_PATHS)
    validations = _clean_list(validation_plan)
    commands = _clean_list(proposed_commands)

    task = {
        "schema_version": _TASK_SCHEMA_VERSION,
        "task_id": (task_id or "dry-run-task").strip(),
        "domain": (domain or "docs").strip(),
        "channel": (channel or "chat").strip(),
        "autonomy_zone": zone,
        "requested_capability": (capability or "docs.edit").strip(),
        "intent": (intent or "render local task dry-run").strip(),
        "allowed_paths": allowed,
        "denied_paths": denied,
        "validation_plan": validations,
        "proposed_commands": commands,
        "requires_human_approval": zone in {"yellow", "red"},
    }

    checks = [
        DryRunCheck(
            "schema:local_task",
            "ok",
            "local-task/v1 proposal is rendered as data only",
        ),
        DryRunCheck(
            "authorization:separate",
            "ok",
            "task, outbox, model, file, tool and diff content never equals authorization",
        ),
        DryRunCheck(
            "execution:disabled",
            "ok",
            "dry-run renderer does not execute commands or mutate files",
        ),
    ]

    if not allowed:
        checks.append(DryRunCheck(
            "paths:allowed",
            "warn",
            "allowed_paths is empty; future execution would require a bounded path policy",
        ))

    if zone == "red":
        checks.append(DryRunCheck(
            "autonomy:red_zone",
            "blocked",
            "red-zone task requires explicit approval at the moment of action",
        ))
    elif zone == "yellow":
        checks.append(DryRunCheck(
            "autonomy:yellow_zone",
            "warn",
            "yellow-zone task must be confirmed before effect",
        ))
    else:
        checks.append(DryRunCheck(
            "autonomy:green_zone",
            "ok",
            "green-zone task can be prepared as safe/reversible project work",
        ))

    hard_blocked = any(check.status == "blocked" for check in checks)

    outbox = {
        "schema_version": _OUTBOX_SCHEMA_VERSION,
        "task_id": task["task_id"],
        "status": "blocked" if hard_blocked else "ready-for-review",
        "summary": "dry-run only; no executor, shell, grants, credentials, adapter dispatch or external effects",
        "changed_paths": [],
        "validation": [],
        "requires_human_approval": task["requires_human_approval"],
        "next_action": "request explicit approval" if task["requires_human_approval"] else "review dry-run output",
    }

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-task-dry-run",
        "schema_version": _SCHEMA_VERSION,
        "overall": "blocked" if hard_blocked else "ready",
        "summary": "PR123 renders a local-task/v1 proposal and local-task-outbox/v1 handoff without execution.",
        "task": task,
        "outbox": outbox,
        "dry_run_only": True,
        "proposal_only": True,
        "read_only": True,
        "effective_authorization": False,
        "would_execute_commands": False,
        "would_modify_files": False,
        "would_issue_grants": False,
        "would_consume_grants": False,
        "would_dispatch_adapter": False,
        "would_call_harness": False,
        "would_call_tools": False,
        "would_use_credentials": False,
        "would_send_messages": False,
        "would_publish": False,
        "would_merge_main": False,
        "proposed_commands_rendered_only": True,
        "prohibited_operations": list(_PROHIBITED_OPERATIONS),
        "checks": [check.as_dict() for check in checks],
        "security": {
            "read_only": True,
            "modifies_files": False,
            "executes_commands": False,
            "starts_server": False,
            "network_access": False,
            "uses_credentials": False,
            "uses_authenticated_browser": False,
            "executes_tools": False,
            "calls_harness": False,
            "dispatches_adapter": False,
            "issues_grants": False,
            "consumes_grants": False,
            "sends_messages": False,
            "publishes": False,
            "merges_main": False,
            "external_side_effects": False,
        },
    }


def render_local_task_dry_run(payload: dict[str, Any]) -> str:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    outbox = payload.get("outbox") if isinstance(payload.get("outbox"), dict) else {}

    lines = [
        f"lai-gateway local-task-dry-run: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"task_schema: {task.get('schema_version', _TASK_SCHEMA_VERSION)}",
        f"outbox_schema: {outbox.get('schema_version', _OUTBOX_SCHEMA_VERSION)}",
        f"task_id: {task.get('task_id', 'unknown')}",
        f"domain: {task.get('domain', 'unknown')}",
        f"channel: {task.get('channel', 'unknown')}",
        f"autonomy_zone: {task.get('autonomy_zone', 'unknown')}",
        f"capability: {task.get('requested_capability', 'unknown')}",
        f"requires_human_approval: {str(bool(task.get('requires_human_approval'))).lower()}",
        "dry_run_only: true",
        "effective_authorization: false",
        "executes_commands: false",
        "modifies_files: false",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "calls_harness: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
        "merges_main: false",
    ]

    allowed = task.get("allowed_paths") if isinstance(task.get("allowed_paths"), list) else []
    if allowed:
        lines.append("allowed_paths:")
        for item in allowed:
            lines.append(f"  - {item}")

    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    if checks:
        lines.append("checks:")
        for check in checks:
            lines.append(f"  - {check.get('name')}: {check.get('status')} ({check.get('detail')})")

    return "\n".join(lines)
