from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .authorization_capture import collect_authorization_capture_stub

_AUTHORIZATION_VALIDATION_VERSION = "authorization-validation-gate/v1"


@dataclass(frozen=True)
class AuthorizationValidationGate:
    validation_id: str
    status: str
    reason: str
    adapter_id: str | None
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action: str
    capture_id: str
    dry_run_id: str
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    decision_outcome: str
    authorization_status: str
    proposal_status: str
    dry_run_status: str
    capture_status: str
    approval_intent: bool
    approval_captured: bool
    approval_validated: bool
    validation_persisted: bool
    effective_authorization: bool
    validation_version: str
    dispatch_enabled: bool = False
    adapter_dispatched: bool = False
    adapter_executed: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    grants_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validation_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"avg-{digest}"


def _validation_status(capture: dict[str, Any], dry_run: dict[str, Any]) -> tuple[str, str, bool]:
    unsafe = (
        bool(capture.get("effective_authorization"))
        or bool(capture.get("dispatch_enabled"))
        or bool(capture.get("adapter_dispatched"))
        or bool(capture.get("adapter_executed"))
        or bool(capture.get("capture_persisted"))
        or bool(dry_run.get("effective_authorization"))
        or bool(dry_run.get("dispatch_enabled"))
        or bool(dry_run.get("adapter_dispatched"))
        or bool(dry_run.get("adapter_executed"))
    )
    if unsafe:
        return "blocked", "validation blocked unsafe non-effective invariants", False
    if capture.get("status") == "blocked" or dry_run.get("status") == "blocked":
        return "blocked", "validation blocked because capture or dry-run is blocked", False
    if not capture.get("approval_captured"):
        return "pending", "validation waits for explicit captured approval intent", False
    if capture.get("decision_outcome") != "requires_approval":
        return "blocked", "validation requires a permission decision that asks for approval", False
    if capture.get("authorization_status") != "requires_human_approval":
        return "blocked", "validation requires a matching authorization record", False
    if capture.get("proposal_status") != "requires_authorization":
        return "blocked", "validation requires a gated adapter invocation proposal", False
    if capture.get("dry_run_status") != "simulated" or dry_run.get("status") != "simulated":
        return "blocked", "validation requires a successful simulation-only dry-run", False
    if capture.get("requested_capability") != dry_run.get("requested_capability"):
        return "blocked", "validation detected capability drift between capture and dry-run", False
    return "validated_non_effective", "approval capture validated without effective authorization", True


def build_authorization_validation_gate(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
) -> tuple[AuthorizationValidationGate, dict[str, Any]]:
    capture_payload = collect_authorization_capture_stub(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
    )
    capture = capture_payload["capture"]
    dry_run = capture_payload["dry_run"]
    status, reason, validated = _validation_status(capture, dry_run)
    validation_id = _validation_id(
        (
            _AUTHORIZATION_VALIDATION_VERSION,
            capture["capture_id"],
            dry_run["dry_run_id"],
            dry_run["proposal_id"],
            dry_run["authorization_record_id"],
            dry_run["evaluation_id"],
            dry_run["decision_id"],
            status,
            str(validated).lower(),
        )
    )
    gate = AuthorizationValidationGate(
        validation_id=validation_id,
        status=status,
        reason=reason,
        adapter_id=capture.get("adapter_id"),
        requested_capability=capture["requested_capability"],
        actor=capture["actor"],
        channel=capture["channel"],
        domain=capture["domain"],
        action=capture["action"],
        capture_id=capture["capture_id"],
        dry_run_id=dry_run["dry_run_id"],
        proposal_id=dry_run["proposal_id"],
        authorization_record_id=dry_run["authorization_record_id"],
        evaluation_id=dry_run["evaluation_id"],
        decision_id=dry_run["decision_id"],
        audit_log_id=dry_run["audit_log_id"],
        decision_outcome=capture["decision_outcome"],
        authorization_status=capture["authorization_status"],
        proposal_status=capture["proposal_status"],
        dry_run_status=capture["dry_run_status"],
        capture_status=capture["status"],
        approval_intent=bool(capture["approval_intent"]),
        approval_captured=bool(capture["approval_captured"]),
        approval_validated=validated,
        validation_persisted=False,
        effective_authorization=False,
        validation_version=_AUTHORIZATION_VALIDATION_VERSION,
    )
    return gate, capture_payload

def collect_authorization_validation_gate(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
    approval_intent: bool = False,
    approved_by: str | None = None,
) -> dict[str, Any]:
    gate, capture_payload = build_authorization_validation_gate(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "authorization-validation-gate",
        "overall": "ready",
        "validation_version": _AUTHORIZATION_VALIDATION_VERSION,
        "approval_validated": gate.approval_validated,
        "validation_persisted": False,
        "effective_authorization": False,
        "dispatch_enabled": False,
        "adapter_dispatched": False,
        "adapter_executed": False,
        "executes_tools": False,
        "external_side_effects": False,
        "validation": gate.to_dict(),
        "capture": capture_payload["capture"],
        "dry_run": capture_payload["dry_run"],
        "audit": capture_payload["audit"],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "validation_elevates_permissions": False,
            "approval_text_elevates_permissions": False,
            "persists_authorization": False,
            "dispatches_adapter": False,
        },
    }

def render_authorization_validation_gate(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        f"lai-gateway authorization-validation-gate: {payload['overall']}",
        f"version: {payload['version']}",
        f"validation_version: {payload['validation_version']}",
        f"validation_id: {validation['validation_id']}",
        f"status: {validation['status']}",
        f"adapter_id: {validation.get('adapter_id') or 'none'}",
        f"requested_capability: {validation['requested_capability']}",
        f"approval_captured: {str(validation['approval_captured']).lower()}",
        f"approval_validated: {str(validation['approval_validated']).lower()}",
        f"effective_authorization: {str(validation['effective_authorization']).lower()}",
        f"validation_persisted: {str(validation['validation_persisted']).lower()}",
        f"dispatch_enabled: {str(validation['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(validation['adapter_dispatched']).lower()}",
        f"executes_tools: {str(validation['executes_tools']).lower()}",
        f"reason: {validation['reason']}",
        "grants_permissions: false",
        "gate_only: true",
    ]
    return "\n".join(lines)
