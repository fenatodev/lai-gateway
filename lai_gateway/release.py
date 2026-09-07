from __future__ import annotations

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _run_git(args: list[str], repo: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _project_version(repo: Path) -> str:
    with (repo / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml project.version is missing")
    return version


def _head(repo: Path) -> str | None:
    code, out, _err = _run_git(["rev-parse", "HEAD"], repo)
    return out if code == 0 else None


def _branch(repo: Path) -> str | None:
    code, out, _err = _run_git(["branch", "--show-current"], repo)
    return out if code == 0 else None


def _origin_main(repo: Path) -> str | None:
    code, out, _err = _run_git(["rev-parse", "origin/main"], repo)
    return out if code == 0 else None


def _tag_target(repo: Path, tag: str) -> str | None:
    code, out, _err = _run_git(["rev-list", "-n", "1", tag], repo)
    return out if code == 0 else None


def _status(repo: Path) -> str:
    code, out, err = _run_git(["status", "--short"], repo)
    if code != 0:
        return err or "git status failed"
    return out or "[clean]"


def collect_release_check(target: str, repo: Path | None = None) -> dict[str, Any]:
    repo = (repo or Path.cwd()).resolve()
    expected_tag = f"v{target}"
    version = __version__
    pyproject_version = _project_version(repo)
    branch = _branch(repo)
    head = _head(repo)
    origin = _origin_main(repo)
    status = _status(repo)
    tag_target = _tag_target(repo, expected_tag)

    checks: list[Check] = []
    if not _VERSION_RE.match(target):
        checks.append(Check("target_version", "fail", f"invalid target {target!r}"))
    else:
        checks.append(Check("target_version", "ok", target))

    if version == target and pyproject_version == target:
        checks.append(Check("version_match", "ok", f"package={version} pyproject={pyproject_version}"))
    else:
        checks.append(Check("version_match", "fail", f"package={version} pyproject={pyproject_version} target={target}"))

    if status == "[clean]":
        checks.append(Check("git_status", "ok", status))
    else:
        checks.append(Check("git_status", "fail", status))

    if branch == "main":
        if head and origin and head == origin:
            checks.append(Check("main_sync", "ok", "local main matches origin/main"))
        elif head and origin:
            checks.append(Check("main_sync", "fail", f"HEAD={head} origin/main={origin}"))
        else:
            checks.append(Check("main_sync", "fail", "could not resolve HEAD or origin/main"))
    else:
        checks.append(Check("main_sync", "ok", f"candidate branch {branch}; merge through protected main before tagging"))

    if tag_target is None:
        if branch == "main" and head and origin and head == origin and status == "[clean]":
            checks.append(Check("tag_state", "ok", f"{expected_tag} does not exist; main can be tagged after CI"))
        else:
            checks.append(Check("tag_state", "ok", f"{expected_tag} does not exist; candidate must integrate before tagging"))
    elif head and tag_target == head:
        checks.append(Check("tag_state", "ok", f"{expected_tag} points at HEAD"))
    else:
        checks.append(Check("tag_state", "fail", f"{expected_tag} points at {tag_target}, HEAD={head}"))

    validation_commands = ["make check", "make milestone-gate"]
    validation_command = "; ".join(validation_commands)
    checks.append(Check("validation_command", "ok", validation_command))
    checks.append(Check("release_safety", "ok", "read-only check; no tag, push, release, or file mutation executed"))

    hard_fail = any(check.status == "fail" for check in checks)
    tag_exists_on_head = tag_target is not None and head is not None and tag_target == head
    clean_main = branch == "main" and head is not None and origin is not None and head == origin and status == "[clean]"
    version_ok = version == target and pyproject_version == target

    if hard_fail:
        phase = "blocked"
        overall = "blocked"
    elif tag_exists_on_head:
        phase = "tagged"
        overall = "ready"
    elif clean_main and version_ok:
        phase = "ready_to_tag"
        overall = "ready"
    else:
        phase = "ready_for_integration"
        overall = "ready"

    return {
        "product": "lai-gateway",
        "version": version,
        "pyproject_version": pyproject_version,
        "target_version": target,
        "expected_tag": expected_tag,
        "release_channel": "stable",
        "expected_prerelease": False,
        "repository": str(repo),
        "branch": branch,
        "head": head,
        "origin_main": origin,
        "tag_target": tag_target,
        "tag_ready": phase == "ready_to_tag",
        "validation_command": validation_command,
        "validation_commands": validation_commands,
        "overall": overall,
        "phase": phase,
        "checks": [check.as_dict() for check in checks],
    }


def render_release_check(payload: dict[str, Any]) -> str:
    lines = [
        f"product: {payload['product']}",
        f"version: {payload['version']}",
        f"target: {payload['target_version']}",
        f"expected_tag: {payload['expected_tag']}",
        f"overall: {payload['overall']}",
        f"phase: {payload['phase']}",
    ]
    for check in payload["checks"]:
        lines.append(f"- {check['name']}: {check['status']} ({check['detail']})")
    return "\n".join(lines)


def release_check_json(target: str, repo: Path | None = None) -> str:
    return json.dumps(collect_release_check(target, repo), indent=2, sort_keys=True)
