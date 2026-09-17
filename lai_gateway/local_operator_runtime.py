from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .local_task_approval_gate import collect_local_task_approval_gate
from .local_task_file_pack import collect_local_task_file_pack
from .local_task_green_executor import collect_local_task_green_executor
from .local_task_review_gate import collect_local_task_review_gate

_SCHEMA_VERSION = "local-operator-runtime/v1"


def _clean_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _stage_status(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("overall")
    return str(value) if value is not None else None


def _task_record(file_pack: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(file_pack, dict):
        return {}
    value = file_pack.get("task_record")
    return value if isinstance(value, dict) else {}


def _digest_from_stages(
    *,
    review: dict[str, Any] | None,
    approval: dict[str, Any] | None,
    executor: dict[str, Any] | None,
) -> str | None:
    for payload in (executor, approval, review):
        if not isinstance(payload, dict):
            continue
        value = payload.get("task_digest")
        if isinstance(value, str) and value:
            return value
    return None


def _result(
    *,
    repo_root: Path,
    overall: str,
    task_id: str | None,
    execute: bool,
    requested_commands: list[str],
    file_pack: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    approval: dict[str, Any] | None = None,
    executor: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    task = _task_record(file_pack)
    command_results = (
        list(executor.get("command_results") or [])
        if isinstance(executor, dict)
        else []
    )
    planned_commands = (
        list(executor.get("planned_commands") or [])
        if isinstance(executor, dict)
        else []
    )
    executed = bool(
        isinstance(executor, dict)
        and executor.get("executes_commands") is True
    )
    wrote_files = bool(
        isinstance(file_pack, dict)
        and file_pack.get("wrote_files") is True
    )

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "local-operator-runtime",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "decision": overall,
        "summary": (
            "PR130 composes the existing governed local-task chain without "
            "expanding authority or the green executor allowlist."
        ),
        "repo_root": str(repo_root),
        "task_id": task.get("task_id") or task_id,
        "task_digest": _digest_from_stages(
            review=review,
            approval=approval,
            executor=executor,
        ),
        "domain": task.get("domain"),
        "channel": task.get("channel"),
        "autonomy_zone": task.get("autonomy_zone"),
        "requested_capability": task.get("requested_capability"),
        "execute_requested": bool(execute),
        "requested_commands": requested_commands,
        "planned_commands": planned_commands,
        "command_results": command_results,
        "executes_commands": executed,
        "error": error,
        "stage_status": {
            "file_pack": _stage_status(file_pack),
            "review": _stage_status(review),
            "approval": _stage_status(approval),
            "executor": _stage_status(executor),
        },
        "stages": {
            "file_pack": file_pack,
            "review": review,
            "approval": approval,
            "executor": executor,
        },
        "security": {
            "operator_grants_authority": False,
            "effective_authorization": False,
            "issues_grants": False,
            "consumes_grants": False,
            "changes_autonomy_zone": False,
            "expands_executor_allowlist": False,
            "arbitrary_shell": False,
            "shell": False,
            "calls_harness": False,
            "dispatches_adapter": False,
            "executes_external_tools": False,
            "uses_credentials": False,
            "uses_authenticated_browser": False,
            "sends_messages": False,
            "publishes": False,
            "submits_forms": False,
            "purchases": False,
            "merges_main": False,
            "installs_software": False,
            "uses_sudo": False,
            "filesystem_write": wrote_files,
            "source_checkout_write": False,
            "external_side_effects": False,
            "content_is_authorization": False,
        },
    }


def collect_local_operator_runtime(
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
    commands: list[str] | tuple[str, ...] | None = None,
    output_root: str | None = ".lai-ai",
    execute: bool = False,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    repo_root = (repo or Path.cwd()).resolve()
    task_label = (task_id or "").strip()

    requested_commands = _clean_list(
        commands if commands is not None else proposed_commands
    )

    if not task_label:
        return _result(
            repo_root=repo_root,
            overall="invalid",
            task_id=task_id,
            execute=execute,
            requested_commands=requested_commands,
            error="task_id is required for local-operator-runtime/v1",
        )

    try:
        file_pack = collect_local_task_file_pack(
            repo=repo_root,
            task_id=task_label,
            domain=domain,
            channel=channel,
            autonomy_zone=autonomy_zone,
            capability=capability,
            intent=intent,
            allowed_paths=allowed_paths,
            denied_paths=denied_paths,
            validation_plan=validation_plan,
            proposed_commands=proposed_commands,
            output_root=output_root,
            write=True,
        )
    except (OSError, ValueError) as exc:
        return _result(
            repo_root=repo_root,
            overall="invalid",
            task_id=task_label,
            execute=execute,
            requested_commands=requested_commands,
            error=str(exc),
        )

    if file_pack.get("overall") == "blocked":
        return _result(
            repo_root=repo_root,
            overall="blocked",
            task_id=task_label,
            execute=execute,
            requested_commands=requested_commands,
            file_pack=file_pack,
        )

    if file_pack.get("wrote_files") is not True:
        return _result(
            repo_root=repo_root,
            overall="invalid",
            task_id=task_label,
            execute=execute,
            requested_commands=requested_commands,
            file_pack=file_pack,
            error="file pack did not materialize task/outbox records",
        )

    review = collect_local_task_review_gate(
        repo=repo_root,
        task_file=str(file_pack.get("task_file") or ""),
        outbox_file=str(file_pack.get("outbox_file") or ""),
    )

    if review.get("overall") != "ready":
        return _result(
            repo_root=repo_root,
            overall=str(review.get("overall") or "invalid"),
            task_id=task_label,
            execute=execute,
            requested_commands=requested_commands,
            file_pack=file_pack,
            review=review,
        )

    approval = collect_local_task_approval_gate(
        repo=repo_root,
        review_payload=review,
    )

    if approval.get("overall") != "ready_without_approval":
        return _result(
            repo_root=repo_root,
            overall=str(approval.get("overall") or "invalid"),
            task_id=task_label,
            execute=execute,
            requested_commands=requested_commands,
            file_pack=file_pack,
            review=review,
            approval=approval,
        )

    executor = collect_local_task_green_executor(
        repo=repo_root,
        approval_payload=approval,
        task_file=str(file_pack.get("task_file") or ""),
        commands=requested_commands,
        execute=execute,
        timeout_seconds=timeout_seconds,
    )

    return _result(
        repo_root=repo_root,
        overall=str(executor.get("overall") or "invalid"),
        task_id=task_label,
        execute=execute,
        requested_commands=requested_commands,
        file_pack=file_pack,
        review=review,
        approval=approval,
        executor=executor,
    )


def render_local_operator_runtime(payload: dict[str, Any]) -> str:
    stage_status = (
        payload.get("stage_status")
        if isinstance(payload.get("stage_status"), dict)
        else {}
    )

    lines = [
        f"lai-gateway local-operator-runtime: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        f"schema_version: {payload.get('schema_version', _SCHEMA_VERSION)}",
        f"task_id: {payload.get('task_id') or 'unknown'}",
        f"task_digest: {payload.get('task_digest') or 'none'}",
        f"domain: {payload.get('domain') or 'unknown'}",
        f"channel: {payload.get('channel') or 'unknown'}",
        f"autonomy_zone: {payload.get('autonomy_zone') or 'unknown'}",
        f"capability: {payload.get('requested_capability') or 'unknown'}",
        f"execute_requested: {str(bool(payload.get('execute_requested'))).lower()}",
        f"executes_commands: {str(bool(payload.get('executes_commands'))).lower()}",
        f"stage:file_pack: {stage_status.get('file_pack') or 'not-run'}",
        f"stage:review: {stage_status.get('review') or 'not-run'}",
        f"stage:approval: {stage_status.get('approval') or 'not-run'}",
        f"stage:executor: {stage_status.get('executor') or 'not-run'}",
        "operator_grants_authority: false",
        "effective_authorization: false",
        "expands_executor_allowlist: false",
        "arbitrary_shell: false",
        "calls_harness: false",
        "dispatches_adapter: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
        "merges_main: false",
        "external_side_effects: false",
    ]

    planned = (
        payload.get("planned_commands")
        if isinstance(payload.get("planned_commands"), list)
        else []
    )
    if planned:
        lines.append("planned_commands:")
        for command in planned:
            lines.append(f"  - {command}")

    results = (
        payload.get("command_results")
        if isinstance(payload.get("command_results"), list)
        else []
    )
    if results:
        lines.append("command_results:")
        for result in results:
            lines.append(
                f"  - {result.get('command')}: "
                f"{result.get('status')} ({result.get('returncode')})"
            )

    if payload.get("error"):
        lines.append(f"error: {payload['error']}")

    return "\n".join(lines)
