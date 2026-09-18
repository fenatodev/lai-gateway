from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from . import __version__
from .local_operator_runtime import collect_local_operator_runtime
from .local_task_green_executor import _ALLOWED_EXACT_COMMANDS

_SCHEMA_VERSION = "workbench-local-operator/v1"

_PROFILE_COMMANDS: dict[str, tuple[str, ...]] = {
    "status": (
        "git status --short --branch",
    ),
    "diff-check": (
        "git diff --check",
    ),
    "diff-stat": (
        "git diff --stat",
    ),
    "compile": (
        "python3 -m compileall -q lai_gateway tests",
    ),
    "gate-tests": (
        "python3 -m unittest tests.test_local_task_review_gate -v",
        "python3 -m unittest tests.test_local_task_approval_gate -v",
        "python3 -m unittest tests.test_local_task_green_executor -v",
    ),
    "full-check": (
        "make check",
    ),
}

_PROFILE_DESCRIPTIONS = {
    "status": "Inspect repository branch and working-tree status.",
    "diff-check": "Check the current diff for whitespace and patch errors.",
    "diff-stat": "Show the current bounded Git diff summary.",
    "compile": "Compile the LAI Gateway package and tests without changing source.",
    "gate-tests": "Run the existing review, approval and green executor gate tests.",
    "full-check": "Run the existing repository make check validation suite.",
}

WORKBENCH_LOCAL_OPERATOR_PROFILES = tuple(_PROFILE_COMMANDS)


def is_workbench_local_operator_profile(value: object) -> bool:
    return isinstance(value, str) and value in _PROFILE_COMMANDS


def workbench_local_operator_profile_commands(profile: str) -> tuple[str, ...]:
    return _PROFILE_COMMANDS.get(profile, ())


def _profile_is_exactly_allowlisted(profile: str) -> bool:
    commands = workbench_local_operator_profile_commands(profile)
    if not commands:
        return False

    for command in commands:
        try:
            argv = tuple(shlex.split(command))
        except ValueError:
            return False
        if argv not in _ALLOWED_EXACT_COMMANDS:
            return False

    return True


def _invalid_result(profile: object, reason: str) -> dict[str, Any]:
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "workbench-local-operator",
        "schema_version": _SCHEMA_VERSION,
        "overall": "invalid",
        "profile": profile if isinstance(profile, str) else None,
        "profile_description": None,
        "commands": [],
        "runtime": None,
        "executes_commands": False,
        "reason": reason,
        "security": {
            "arbitrary_command_input": False,
            "arbitrary_repo_root": False,
            "expands_executor_allowlist": False,
            "calls_harness": False,
            "dispatches_adapter": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "merges_main": False,
        },
    }


def collect_workbench_local_operator(
    *,
    repo: Path,
    profile: str,
    execute: bool = True,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    if not is_workbench_local_operator_profile(profile):
        return _invalid_result(profile, "unknown local operator profile")

    if not _profile_is_exactly_allowlisted(profile):
        return _invalid_result(
            profile,
            "profile is not composed exclusively from the PR127 exact allowlist",
        )

    commands = list(workbench_local_operator_profile_commands(profile))
    description = _PROFILE_DESCRIPTIONS[profile]

    runtime = collect_local_operator_runtime(
        repo=repo.resolve(),
        task_id=f"workbench-{profile}",
        domain="project-operations",
        channel="workbench",
        autonomy_zone="green",
        capability=f"local.operator.{profile}",
        intent=description,
        allowed_paths=["."],
        validation_plan=commands,
        proposed_commands=commands,
        commands=commands,
        output_root="state/local-operator",
        execute=execute,
        timeout_seconds=timeout_seconds,
    )

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "workbench-local-operator",
        "schema_version": _SCHEMA_VERSION,
        "overall": runtime.get("overall", "invalid"),
        "profile": profile,
        "profile_description": description,
        "commands": commands,
        "runtime": runtime,
        "executes_commands": bool(runtime.get("executes_commands")),
        "reason": runtime.get("error"),
        "security": {
            "arbitrary_command_input": False,
            "arbitrary_repo_root": False,
            "expands_executor_allowlist": False,
            "calls_harness": False,
            "dispatches_adapter": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "merges_main": False,
        },
    }
