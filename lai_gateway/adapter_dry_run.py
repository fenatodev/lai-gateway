from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .audit_events import collect_audit_events

_ADAPTER_DRY_RUN_VERSION = "adapter-dry-run/v1"


@dataclass(frozen=True)
class AdapterDryRun:
    dry_run_id: str
    status: str
    reason: str
    adapter_id: str | None
    adapter_status: str
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action: str
    parameters: dict[str, str]
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    audit_event_ids: tuple[str, ...]
    decision_outcome: str
    authorization_status: str
    proposal_status: str
    requires_human_approval: bool
    dry_run_executed: bool
    simulated_result: str
    dry_run_version: str
    simulation_only: bool = True
    effective_authorization: bool = False
    dispatch_enabled: bool = False
    adapter_dispatched: bool = False
    adapter_executed: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    grants_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["audit_event_ids"] = list(self.audit_event_ids)
        return payload


def _dry_run_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"adr-{digest}"


def _adapter_kind(adapter_id: str | None) -> str:
    if not adapter_id:
        return "missing"
    payload = collect_adapter_registry(adapter_id=adapter_id)
    if payload.get("overall") != "ready" or not payload.get("adapters"):
        return "missing"
    return str(payload["adapters"][0].get("kind", "unknown"))


def _dry_run_status(proposal: dict[str, Any]) -> tuple[str, str, bool]:
    if proposal.get("status") == "blocked":
        return "blocked", "dry-run refused because proposal is blocked", False
    if proposal.get("adapter_status") == "missing":
        return "blocked", "dry-run refused because adapter contract is missing", False
    return "simulated", "adapter path simulated without dispatch or side effects", True


def build_adapter_dry_run(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> tuple[AdapterDryRun, dict[str, Any]]:
    audit_payload = collect_audit_events(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
    )
    proposal = audit_payload["proposal"]
    pid = proposal["proposal_id"]
    rid = proposal["authorization_record_id"]
    eid = proposal["evaluation_id"]
    did = proposal["decision_id"]
    status, reason, dry_run_executed = _dry_run_status(proposal)
    event_ids = tuple(str(event["event_id"]) for event in audit_payload.get("events", []))
    simulated_result = "not_run"
    if dry_run_executed:
        simulated_result = (
            f"planned {proposal.get('adapter_id') or 'adapter'} "
            f"{proposal['requested_capability']} via {_adapter_kind(proposal.get('adapter_id'))}"
        )
    dry_run_id = _dry_run_id(
        (
            _ADAPTER_DRY_RUN_VERSION,
            proposal["proposal_id"],
            proposal["authorization_record_id"],
            proposal["evaluation_id"],
            proposal["decision_id"],
            audit_payload["log_id"],
            status,
            proposal["requested_capability"],
            proposal.get("adapter_id") or "",
            repr(tuple(sorted(proposal.get("parameters", {}).items()))),
        )
    )
    return (
        AdapterDryRun(
            dry_run_id=dry_run_id,
            status=status,
            reason=reason,
            adapter_id=proposal.get("adapter_id"),
            adapter_status=proposal.get("adapter_status", "missing"),
            requested_capability=proposal["requested_capability"],
            actor=proposal["actor"],
            channel=proposal["channel"],
            domain=proposal["domain"],
            action=proposal["action"],
            parameters={},
            proposal_id=pid,
            authorization_record_id=rid,
            evaluation_id=eid,
            decision_id=did,
            audit_log_id=audit_payload["log_id"],
            audit_event_ids=event_ids,
            decision_outcome=proposal["decision_outcome"],
            authorization_status=proposal["authorization_status"],
            proposal_status=proposal["status"],
            requires_human_approval=bool(proposal["requires_human_approval"]),
            dry_run_executed=dry_run_executed,
            simulated_result=simulated_result,
            dry_run_version=_ADAPTER_DRY_RUN_VERSION,
        ),
        audit_payload,
    )


def collect_adapter_dry_run(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    dry_run, audit_payload = build_adapter_dry_run(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "adapter-dry-run",
        "overall": "ready",
        "dry_run_version": _ADAPTER_DRY_RUN_VERSION,
        "dry_run_only": True,
        "simulation_only": True,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "dispatch_enabled": False,
        "adapter_dispatched": False,
        "adapter_executed": False,
        "effective_authorization": False,
        "external_side_effects": False,
        "dry_run": dry_run.to_dict(),
        "audit": audit_payload,
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "captures_approval": False,
            "persists_authorization": False,
            "persists_audit_log": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "dry_run_elevates_permissions": False,
        },
    }


def render_adapter_dry_run(payload: dict[str, Any]) -> str:
    dry_run = payload["dry_run"]
    lines = [
        f"lai-gateway adapter-dry-run: {payload['overall']}",
        f"version: {payload['version']}",
        f"dry_run_version: {payload['dry_run_version']}",
        f"dry_run_id: {dry_run['dry_run_id']}",
        f"status: {dry_run['status']}",
        f"adapter_id: {dry_run.get('adapter_id') or 'none'}",
        f"adapter_status: {dry_run['adapter_status']}",
        f"requested_capability: {dry_run['requested_capability']}",
        f"proposal_status: {dry_run['proposal_status']}",
        f"decision_outcome: {dry_run['decision_outcome']}",
        f"authorization_status: {dry_run['authorization_status']}",
        f"requires_human_approval: {str(dry_run['requires_human_approval']).lower()}",
        f"dry_run_executed: {str(dry_run['dry_run_executed']).lower()}",
        f"simulation_only: {str(dry_run['simulation_only']).lower()}",
        f"dispatch_enabled: {str(dry_run['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(dry_run['adapter_dispatched']).lower()}",
        f"effective_authorization: {str(dry_run['effective_authorization']).lower()}",
        f"simulated_result: {dry_run['simulated_result']}",
        f"reason: {dry_run['reason']}",
    ]
    if dry_run.get("parameters"):
        lines.append("parameters:")
        for key, value in dry_run["parameters"].items():
            lines.append(f"- {key}: {value}")
    lines.extend([
        "executes_tools: false",
        "external_side_effects: false",
        "grants_permissions: false",
        "dry_run_only: true",
    ])
    return "\n".join(lines)
