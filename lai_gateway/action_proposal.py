from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .objective_state import collect_objective_state

_ACTION_PROPOSAL_VERSION = "action-proposal/v1"
_MAX_TEXT_CHARS = 500
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
_EXTERNAL_EFFECT_RE = re.compile(
    r"(?i)\b(send|publish|post|submit|buy|purchase|email|telegram|slack|webhook|external|login|credential|deploy|release)\b"
)


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    schema_version: str
    status: str
    reason: str
    actor: str
    domain: str
    channel: str
    autonomy: str
    capability: str
    action: str
    target: str
    data: str
    effect: str
    risk: str
    source: str
    objective_task_id: str | None
    selected_from_objective_state: bool
    proposed_external_effect: bool
    requires_human_approval_before_execution: bool = True
    effective_authorization: bool = False
    proposal_only: bool = True
    grants_permission: bool = False
    issues_grants: bool = False
    consumes_grants: bool = False
    dispatch_enabled: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    calls_harness: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _safe_text(value: Any, *, default: str = "", limit: int = _MAX_TEXT_CHARS) -> tuple[str, bool]:
    text = str(value if value is not None else default).strip()
    redacted = False
    if _SECRET_RE.search(text):
        text = "[redacted]"
        redacted = True
    return text[:limit], redacted


def _safe_label(value: Any, *, default: str = "unknown") -> tuple[str, bool]:
    text, redacted = _safe_text(value, default=default, limit=96)
    label = text.lower().replace(" ", "-") if text != "[redacted]" else text
    return label or default, redacted


def _safe_risk(value: Any) -> tuple[str, bool]:
    risk, redacted = _safe_label(value, default="unknown")
    return (risk if risk in _ALLOWED_RISKS else "unknown"), redacted


def _first_useful_task(tasks: list[dict[str, Any]], task_id: str | None) -> dict[str, Any] | None:
    if task_id:
        for task in tasks:
            if str(task.get("task_id") or task.get("id") or "") == task_id:
                return task
        return None
    for task in tasks:
        if str(task.get("status") or "unknown") not in {"done", "blocked"}:
            return task
    return tasks[0] if tasks else None


def _coalesce_text(explicit: Any, fallback: Any, *, default: str = "") -> tuple[str, bool]:
    value = explicit if explicit not in {None, ""} else fallback
    return _safe_text(value, default=default)


def _coalesce_label(explicit: Any, fallback: Any, *, default: str = "unknown") -> tuple[str, bool]:
    value = explicit if explicit not in {None, ""} else fallback
    return _safe_label(value, default=default)


def _proposal_status(*, action: str, domain: str, channel: str, autonomy: str, capability: str, target: str, data: str, effect: str, risk: str) -> tuple[str, str]:
    missing = []
    checks = {
        "action": action,
        "domain": domain,
        "channel": channel,
        "autonomy": autonomy,
        "capability": capability,
        "target": target,
        "data": data,
        "effect": effect,
        "risk": risk,
    }
    for key, value in checks.items():
        if not value or value == "[redacted]":
            missing.append(key)
            continue
        if key in {"domain", "channel"} and value == "unknown":
            missing.append(key)
        elif key == "capability" and value in {"unknown", "none"}:
            missing.append(key)
        elif key in {"action", "target", "data", "effect"} and value in {"unknown", "none"}:
            missing.append(key)
    if missing:
        return "needs_input", "proposal is missing explicit fields: " + ", ".join(missing)
    return "ready", "proposal declares domain, channel, autonomy, capability, target, data, effect and risk"


def collect_action_proposal(
    *,
    workspace_root: str | Path | None = ".",
    state_file: str | Path | None = None,
    task_id: str | None = None,
    actor: str | None = None,
    domain: str | None = None,
    channel: str | None = None,
    autonomy: str | None = None,
    capability: str | None = None,
    target: str | None = None,
    action: str | None = None,
    data: str | None = None,
    effect: str | None = None,
    risk: str | None = None,
    scope_root: Path | None = None,
) -> dict[str, Any]:
    objective_payload = collect_objective_state(
        workspace_root=workspace_root,
        state_file=state_file,
        scope_root=scope_root,
    )
    selected_task = _first_useful_task(objective_payload.get("state", {}).get("tasks") or [], task_id)
    selected = selected_task or {}
    redacted_flags = []

    actor_value, redacted = _safe_label(actor, default="user")
    redacted_flags.append(redacted)
    domain_value, redacted = _coalesce_label(domain, selected.get("domain"), default="unknown")
    redacted_flags.append(redacted)
    channel_value, redacted = _coalesce_label(channel, selected.get("channel"), default="unknown")
    redacted_flags.append(redacted)
    autonomy_value, redacted = _coalesce_label(autonomy, selected.get("autonomy"), default="unknown")
    redacted_flags.append(redacted)
    capability_value, redacted = _coalesce_label(capability, selected.get("capability"), default="none")
    redacted_flags.append(redacted)
    target_value, redacted = _coalesce_text(target, selected.get("target"), default="")
    redacted_flags.append(redacted)
    action_value, redacted = _coalesce_text(action, selected.get("title"), default="")
    redacted_flags.append(redacted)
    data_value, redacted = _safe_text(data, default="")
    redacted_flags.append(redacted)
    effect_value, redacted = _safe_text(effect, default="")
    redacted_flags.append(redacted)
    risk_value, redacted = _safe_risk(risk if risk not in {None, ""} else selected.get("risk"))
    redacted_flags.append(redacted)

    status, reason = _proposal_status(
        action=action_value,
        domain=domain_value,
        channel=channel_value,
        autonomy=autonomy_value,
        capability=capability_value,
        target=target_value,
        data=data_value,
        effect=effect_value,
        risk=risk_value,
    )
    if objective_payload.get("overall") == "blocked":
        status = "blocked"
        reason = "objective state source is blocked; proposal remains non-authorizing"

    proposed_external_effect = bool(_EXTERNAL_EFFECT_RE.search(effect_value) or _EXTERNAL_EFFECT_RE.search(action_value))
    proposal_id = "ap-" + _digest((
        _ACTION_PROPOSAL_VERSION,
        status,
        actor_value,
        domain_value,
        channel_value,
        autonomy_value,
        capability_value,
        action_value,
        target_value,
        data_value,
        effect_value,
        risk_value,
        str(selected.get("task_id") or ""),
    ))
    proposal = ActionProposal(
        proposal_id=proposal_id,
        schema_version=_ACTION_PROPOSAL_VERSION,
        status=status,
        reason=reason,
        actor=actor_value,
        domain=domain_value,
        channel=channel_value,
        autonomy=autonomy_value,
        capability=capability_value,
        action=action_value,
        target=target_value,
        data=data_value,
        effect=effect_value,
        risk=risk_value,
        source="objective-state-untrusted" if selected_task else "explicit-input",
        objective_task_id=str(selected.get("task_id") or "") or None,
        selected_from_objective_state=bool(selected_task),
        proposed_external_effect=proposed_external_effect,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "action-proposal",
        "schema_version": _ACTION_PROPOSAL_VERSION,
        "overall": status,
        "proposal_only": True,
        "effective_authorization": False,
        "proposal": proposal.to_dict(),
        "objective_state": {
            "operation": objective_payload.get("operation"),
            "overall": objective_payload.get("overall"),
            "schema_version": objective_payload.get("schema_version"),
            "state_file": objective_payload.get("data_touched", {}).get("state_file"),
            "content_read": objective_payload.get("data_touched", {}).get("content_read", False),
            "selected_task_id": proposal.objective_task_id,
            "untrusted_content": True,
            "content_grants_authority": False,
        },
        "data_touched": {
            "workspace_root": objective_payload.get("data_touched", {}).get("workspace_root", str(workspace_root or "")),
            "state_file": objective_payload.get("data_touched", {}).get("state_file", str(state_file or ".lai/objective-state.json")),
            "objective_state_read": bool(objective_payload.get("data_touched", {}).get("content_read", False)),
            "proposal_fields_read": True,
            "filesystem_write": False,
            "recursive_scan": False,
            "home_scan": False,
            "implicit_ingestion": False,
        },
        "security": {
            "read_only": True,
            "untrusted_content": True,
            "content_grants_authority": False,
            "approval_inferred": False,
            "requires_human_approval_before_execution": True,
            "capabilities_granted": [],
            "grants_permission": False,
            "grants_permissions": False,
            "issues_grants": False,
            "consumes_grants": False,
            "dispatches_adapter": False,
            "dispatch_enabled": False,
            "executes_tools": False,
            "external_side_effects": False,
            "proposed_external_effect": proposed_external_effect,
            "network_access": False,
            "shell_execution": False,
            "filesystem_write": False,
            "starts_server": False,
            "calls_harness": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
            "secret_redacted": any(redacted_flags),
        },
    }


def render_action_proposal(payload: dict[str, Any]) -> str:
    proposal = payload.get("proposal", {})
    lines = [
        f"lai-gateway action-proposal: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _ACTION_PROPOSAL_VERSION)}",
        f"proposal_id: {proposal.get('proposal_id') or 'missing'}",
        f"status: {proposal.get('status') or 'unknown'}",
        f"domain: {proposal.get('domain') or 'unknown'}",
        f"channel: {proposal.get('channel') or 'unknown'}",
        f"autonomy: {proposal.get('autonomy') or 'unknown'}",
        f"capability: {proposal.get('capability') or 'none'}",
        f"target: {proposal.get('target') or 'missing'}",
        f"data: {proposal.get('data') or 'missing'}",
        f"effect: {proposal.get('effect') or 'missing'}",
        f"risk: {proposal.get('risk') or 'unknown'}",
        f"source: {proposal.get('source') or 'unknown'}",
        f"requires_human_approval_before_execution: {str(proposal.get('requires_human_approval_before_execution', True)).lower()}",
        "effective_authorization: false",
        "issues_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "external_side_effects: false",
        f"reason: {proposal.get('reason', '')}",
    ]
    action = proposal.get("action") or ""
    if action:
        lines.append(f"action: {action}")
    return "\n".join(lines)
