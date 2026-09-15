from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapter_invocation import collect_adapter_invocation_proposal

_AUDIT_EVENTS_VERSION = "audit-events/v1"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    sequence: int
    event_type: str
    status: str
    subject_id: str
    message: str
    adapter_id: str | None
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action: str
    proposal_id: str | None
    authorization_record_id: str | None
    evaluation_id: str | None
    decision_id: str | None
    risk_level: int
    requires_human_approval: bool
    effective_authorization: bool
    dispatch_enabled: bool
    proposal_only: bool
    persisted: bool
    executes_tools: bool
    grants_permission: bool
    external_side_effects: bool
    parameter_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _event_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"ae-{digest}"


def _bounded(value: Any, *, default: str, limit: int = 96) -> str:
    text = str(value if value is not None else default).strip()
    if not text:
        text = default
    return text[:limit]


def _make_event(
    *,
    sequence: int,
    event_type: str,
    status: str,
    subject_id: str,
    message: str,
    base: dict[str, Any],
    risk_level: int,
    requires_human_approval: bool,
    effective_authorization: bool,
    dispatch_enabled: bool,
    parameter_count: int,
) -> AuditEvent:
    proposal_id = base.get("proposal_id")
    authorization_record_id = base.get("authorization_record_id")
    evaluation_id = base.get("evaluation_id")
    decision_id = base.get("decision_id")
    event_id = _event_id(
        (
            _AUDIT_EVENTS_VERSION,
            str(sequence),
            event_type,
            status,
            subject_id,
            proposal_id or "",
            authorization_record_id or "",
            evaluation_id or "",
            decision_id or "",
            base.get("requested_capability") or "",
            base.get("adapter_id") or "",
        )
    )
    return AuditEvent(
        event_id=event_id,
        sequence=sequence,
        event_type=event_type,
        status=status,
        subject_id=subject_id,
        message=message,
        adapter_id=base.get("adapter_id"),
        requested_capability=base["requested_capability"],
        actor=base["actor"],
        channel=base["channel"],
        domain=base["domain"],
        action=base["action"],
        proposal_id=proposal_id,
        authorization_record_id=authorization_record_id,
        evaluation_id=evaluation_id,
        decision_id=decision_id,
        risk_level=risk_level,
        requires_human_approval=requires_human_approval,
        effective_authorization=effective_authorization,
        dispatch_enabled=dispatch_enabled,
        proposal_only=True,
        persisted=False,
        executes_tools=False,
        grants_permission=False,
        external_side_effects=False,
        parameter_count=parameter_count,
    )


def build_audit_events(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> tuple[tuple[AuditEvent, ...], dict[str, Any]]:
    proposal_payload = collect_adapter_invocation_proposal(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
    )
    proposal = proposal_payload["proposal"]
    authorization = proposal_payload["authorization"]
    record = authorization["record"]
    evaluation = authorization["evaluation"]
    decision = evaluation["decision"]
    base = {
        "proposal_id": proposal["proposal_id"],
        "authorization_record_id": record["record_id"],
        "evaluation_id": evaluation["evaluation_id"],
        "decision_id": decision["decision_id"],
        "adapter_id": proposal.get("adapter_id"),
        "requested_capability": proposal["requested_capability"],
        "actor": proposal["actor"],
        "channel": proposal["channel"],
        "domain": proposal["domain"],
        "action": proposal["action"],
    }
    risk_level = int(decision.get("risk_level", 0))
    requires_human_approval = bool(proposal.get("requires_human_approval", False))
    effective_authorization = False
    dispatch_enabled = False
    parameter_count = len(proposal.get("parameters", {}))
    events = (
        _make_event(
            sequence=1,
            event_type="permission_decision",
            status=decision["outcome"],
            subject_id=decision["decision_id"],
            message=decision["reason"],
            base=base,
            risk_level=risk_level,
            requires_human_approval=bool(decision.get("requires_human_approval", False)),
            effective_authorization=effective_authorization,
            dispatch_enabled=dispatch_enabled,
            parameter_count=parameter_count,
        ),
        _make_event(
            sequence=2,
            event_type="policy_evaluation",
            status=evaluation["overall"],
            subject_id=evaluation["evaluation_id"],
            message="policy rules evaluated without executing tools",
            base=base,
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
            effective_authorization=effective_authorization,
            dispatch_enabled=dispatch_enabled,
            parameter_count=parameter_count,
        ),
        _make_event(
            sequence=3,
            event_type="authorization_record",
            status=record["status"],
            subject_id=record["record_id"],
            message=record["reason"],
            base=base,
            risk_level=int(record.get("risk_level", risk_level)),
            requires_human_approval=bool(record.get("requires_human_approval", requires_human_approval)),
            effective_authorization=effective_authorization,
            dispatch_enabled=dispatch_enabled,
            parameter_count=parameter_count,
        ),
        _make_event(
            sequence=4,
            event_type="adapter_invocation_proposal",
            status=proposal["status"],
            subject_id=proposal["proposal_id"],
            message=proposal["reason"],
            base=base,
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
            effective_authorization=effective_authorization,
            dispatch_enabled=dispatch_enabled,
            parameter_count=parameter_count,
        ),
    )
    return events, proposal_payload


def collect_audit_events(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    events, proposal_payload = build_audit_events(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
    )
    material = "|".join(event.event_id for event in events)
    log_id = f"ael-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "audit-events",
        "overall": "ready",
        "audit_events_version": _AUDIT_EVENTS_VERSION,
        "log_id": log_id,
        "event_count": len(events),
        "read_only": True,
        "derived_from_current_request": True,
        "persisted": False,
        "writes_log_file": False,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "dispatch_enabled": False,
        "effective_authorization": False,
        "proposal": proposal_payload["proposal"],
        "events": [event.to_dict() for event in events],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "dispatches_adapter": False,
            "persists_audit_log": False,
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "adapters_elevate_permissions": False,
            "content_elevates_permissions": False,
            "audit_events_elevate_permissions": False,
        },
    }


def render_audit_events(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway audit-events: {payload['overall']}",
        f"version: {payload['version']}",
        f"audit_events_version: {payload['audit_events_version']}",
        f"log_id: {payload['log_id']}",
        f"event_count: {payload['event_count']}",
        f"persisted: {str(payload['persisted']).lower()}",
        f"writes_log_file: {str(payload['writes_log_file']).lower()}",
        f"dispatch_enabled: {str(payload['dispatch_enabled']).lower()}",
        f"effective_authorization: {str(payload['effective_authorization']).lower()}",
        "events:",
    ]
    for event in payload.get("events", []):
        lines.append(
            "- "
            f"{event['sequence']} {event['event_type']} "
            f"status={event['status']} "
            f"subject={event['subject_id']} "
            f"persisted={str(event['persisted']).lower()} "
            f"executes_tools={str(event['executes_tools']).lower()}"
        )
    lines.extend(["grants_permissions: false", "read_only: true"])
    return "\n".join(lines)
