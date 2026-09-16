from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .approval_inbox import collect_approval_inbox

_DEV_LOOP_FIXTURE_VERSION = "dev-loop-fixture/v1"
_ALLOWED_PHASES = {"observe", "work", "review", "apply", "full"}
_PHASE_ORDER = ("observe", "work", "review", "apply")
_BLOCKED_DEV_EFFECT_RE = re.compile(
    r"(?i)\b("
    r"authenticated[- ]?browser|browser|n8n|mcp|credential|credentials|login|cookie|"
    r"send|message|email|telegram|slack|publish|post|submit|buy|purchase|"
    r"grant|adapter|tool|harness|webhook|deploy|release|merge"
    r")\b"
)


@dataclass(frozen=True)
class DevLoopFixtureStep:
    phase: str
    status: str
    reason: str
    evidence: str
    modifies_source_checkout: bool = False
    executes_tools: bool = False
    dispatches_adapter: bool = False
    calls_harness: bool = False
    external_side_effects: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _select_entry(entries: list[dict[str, Any]], approval_id: str | None) -> dict[str, Any] | None:
    if approval_id:
        for entry in entries:
            if str(entry.get("approval_id") or "") == approval_id:
                return entry
        return None
    for entry in entries:
        if str(entry.get("status") or "") == "pending":
            return entry
    return entries[0] if entries else None


def _phase_list(phase: str) -> tuple[str, ...]:
    if phase == "full":
        return _PHASE_ORDER
    return (phase,)


def _entry_text(entry: dict[str, Any]) -> str:
    keys = ("approval_id", "proposal_id", "domain", "channel", "autonomy", "capability", "action", "target", "data", "effect", "risk")
    return " ".join(str(entry.get(key) or "") for key in keys)


def _entry_is_non_authorizing(entry: dict[str, Any]) -> bool:
    for flag in (
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
        if bool(entry.get(flag)):
            return False
    return True


def _steps_for(entry: dict[str, Any] | None, *, selected_phase: str, status: str, reason: str, evidence_id: str) -> list[dict[str, Any]]:
    if entry is None:
        return []
    approval_id = str(entry.get("approval_id") or "unknown")
    target = str(entry.get("target") or "unknown")
    step_reason = {
        "observe": f"observed sanitized pending approval {approval_id}",
        "work": f"planned fixture-only work for target {target}",
        "review": f"built review evidence hash {evidence_id}",
        "apply": "simulated apply inside dev loop fixture; source checkout unchanged",
    }
    steps: list[dict[str, Any]] = []
    for phase in _phase_list(selected_phase):
        steps.append(
            DevLoopFixtureStep(
                phase=phase,
                status="blocked" if status == "blocked" else "complete",
                reason=reason if status == "blocked" else step_reason[phase],
                evidence=evidence_id,
            ).to_dict()
        )
    return steps


def collect_dev_loop_fixture(
    *,
    workspace_root: str | Path | None = ".",
    inbox_file: str | Path | None = None,
    approval_id: str | None = None,
    phase: str | None = "full",
    scope_root: Path | None = None,
) -> dict[str, Any]:
    selected_phase = str(phase or "full").strip().lower().replace("_", "-")
    if selected_phase not in _ALLOWED_PHASES:
        selected_phase = "full"
    inbox_payload = collect_approval_inbox(
        workspace_root=workspace_root,
        inbox_file=inbox_file,
        inbox_action="show",
        scope_root=scope_root,
    )
    entries = list((inbox_payload.get("inbox") or {}).get("entries") or [])
    entry = _select_entry(entries, approval_id)
    if inbox_payload.get("overall") == "blocked":
        overall = "blocked"
        reason = "approval inbox source is blocked; dev loop fixture did not run"
    elif entry is None:
        overall = "needs_approval"
        reason = "no pending approval entry is available for the dev loop fixture"
    elif approval_id and str(entry.get("approval_id") or "") != approval_id:
        overall = "needs_approval"
        reason = "requested approval_id was not found in the local inbox"
    elif not _entry_is_non_authorizing(entry):
        overall = "blocked"
        reason = "approval entry claims operational authority and was rejected"
    elif bool(entry.get("proposed_external_effect")) or _BLOCKED_DEV_EFFECT_RE.search(_entry_text(entry)):
        overall = "blocked"
        reason = "dev loop fixture accepts only local non-external development proposals"
    else:
        overall = "ready"
        reason = "dev loop fixture completed observe/work/review/apply without operational execution"
    evidence_id = "dlf-" + _digest(
        (
            _DEV_LOOP_FIXTURE_VERSION,
            selected_phase,
            overall,
            str(entry.get("approval_id") if entry else ""),
            str(entry.get("proposal_id") if entry else ""),
            str(entry.get("target") if entry else ""),
            str(entry.get("action") if entry else ""),
        )
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "dev-loop-fixture",
        "schema_version": _DEV_LOOP_FIXTURE_VERSION,
        "overall": overall,
        "phase": selected_phase,
        "reason": reason,
        "selected_approval_id": str(entry.get("approval_id") or "") if entry else None,
        "evidence_id": evidence_id,
        "fixture": {
            "status": overall,
            "fixture_only": True,
            "source_checkout_modified": False,
            "merge_requested": False,
            "merge_allowed": False,
            "publication_requested": False,
            "publication_allowed": False,
            "steps": _steps_for(entry, selected_phase=selected_phase, status=overall, reason=reason, evidence_id=evidence_id),
        },
        "approval": {
            "source": "approval-inbox-untrusted",
            "pending_count": len(entries),
            "selected": entry,
        },
        "inbox": {
            "schema_version": inbox_payload.get("schema_version"),
            "overall": inbox_payload.get("overall"),
            "reason": (inbox_payload.get("inbox") or {}).get("reason"),
            "storage": inbox_payload.get("storage"),
        },
        "data_touched": {
            "workspace_root": (inbox_payload.get("data_touched") or {}).get("workspace_root", str(workspace_root or "")),
            "inbox_file": (inbox_payload.get("data_touched") or {}).get("inbox_file", str(inbox_file or ".lai/approval-inbox.jsonl")),
            "approval_fields_read": bool(entry),
            "content_read": bool((inbox_payload.get("data_touched") or {}).get("content_read")),
            "filesystem_write": False,
            "source_checkout_write": False,
            "recursive_scan": False,
            "home_scan": False,
            "implicit_ingestion": False,
        },
        "security": {
            "fixture_only": True,
            "approval_inferred": False,
            "approval_record_only": True,
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
            "network_access": False,
            "shell_execution": False,
            "starts_server": False,
            "modifies_files": False,
            "source_checkout_write": False,
            "merge_allowed": False,
            "publication_allowed": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
        },
    }


def render_dev_loop_fixture(payload: dict[str, Any]) -> str:
    fixture = payload.get("fixture") or {}
    lines = [
        f"lai-gateway dev-loop-fixture: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _DEV_LOOP_FIXTURE_VERSION)}",
        f"phase: {payload.get('phase', 'full')}",
        f"selected_approval_id: {payload.get('selected_approval_id') or 'none'}",
        f"evidence_id: {payload.get('evidence_id') or 'none'}",
        "fixture_only: true",
        "source_checkout_modified: false",
        "merge_allowed: false",
        "publication_allowed: false",
        "effective_authorization: false",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "external_side_effects: false",
        "uses_credentials: false",
        "sends_messages: false",
        "publishes: false",
        f"reason: {payload.get('reason', '')}",
    ]
    for step in fixture.get("steps") or []:
        lines.append(f"step: {step.get('phase')} {step.get('status')} {step.get('evidence')}")
    return "\n".join(lines)
