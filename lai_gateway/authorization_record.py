from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .policy_evaluator import collect_policy_evaluation

_AUTHORIZATION_RECORD_VERSION = "authorization-record/v1"
_TERMINAL_DECISION_OUTCOMES = {"allow", "deny", "requires_approval"}


@dataclass(frozen=True)
class AuthorizationRecord:
    record_id: str
    status: str
    reason: str
    decision_id: str
    evaluation_id: str
    decision_outcome: str
    requested_capability: str
    granted_capability: str | None
    adapter_id: str | None
    identity_binding_id: str
    identity_verified: bool
    identity_source: str
    user_id: str
    client_id: str
    agent_id: str
    service_id: str
    actor: str
    channel: str
    domain: str
    action: str
    risk_level: int
    requires_human_approval: bool
    approval_captured: bool
    approved_by: str | None
    approved_at: str | None
    expires_at: str | None
    effective_authorization: bool
    record_persisted: bool
    authorization_version: str
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _record_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"ar-{digest}"


def _record_status(decision: dict[str, Any]) -> tuple[str, str]:
    outcome = decision.get("outcome")
    if outcome == "requires_approval":
        return "requires_human_approval", "human approval is required and has not been captured"
    if outcome == "deny":
        return "blocked", "denied policy decisions cannot produce an effective authorization"
    if outcome == "allow":
        return "not_required", "policy allowed the capability, but this record does not grant execution authority"
    return "blocked", "unknown decision outcome cannot produce an effective authorization"


def build_authorization_record(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    user_id: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    service_id: str | None = None,
    identity_source: str | None = None,
    expected_identity_binding_id: str | None = None,
    claimed_user_id: str | None = None,
    claimed_client_id: str | None = None,
    claimed_agent_id: str | None = None,
    claimed_service_id: str | None = None,
) -> tuple[AuthorizationRecord, dict[str, Any]]:
    evaluation = collect_policy_evaluation(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        user_id=user_id,
        client_id=client_id,
        agent_id=agent_id,
        service_id=service_id,
        identity_source=identity_source,
        expected_identity_binding_id=expected_identity_binding_id,
        claimed_user_id=claimed_user_id,
        claimed_client_id=claimed_client_id,
        claimed_agent_id=claimed_agent_id,
        claimed_service_id=claimed_service_id,
    )
    decision = evaluation["decision"]
    status, reason = _record_status(decision)
    outcome = decision.get("outcome", "deny")
    if outcome not in _TERMINAL_DECISION_OUTCOMES:
        outcome = "deny"
    record_id = _record_id(
        (
            _AUTHORIZATION_RECORD_VERSION,
            evaluation["evaluation_id"],
            decision["decision_id"],
            outcome,
            decision["requested_capability"],
            decision.get("adapter_id") or "",
            decision["actor"],
            decision["channel"],
            decision["domain"],
            decision["action"],
            decision["identity_binding_id"],
            status,
        )
    )
    return (
        AuthorizationRecord(
            record_id=record_id,
            status=status,
            reason=reason,
            decision_id=decision["decision_id"],
            evaluation_id=evaluation["evaluation_id"],
            decision_outcome=outcome,
            requested_capability=decision["requested_capability"],
            granted_capability=decision.get("granted_capability"),
            adapter_id=decision.get("adapter_id"),
            identity_binding_id=decision["identity_binding_id"],
            identity_verified=decision["identity_verified"],
            identity_source=decision["identity_source"],
            user_id=decision["user_id"],
            client_id=decision["client_id"],
            agent_id=decision["agent_id"],
            service_id=decision["service_id"],
            actor=decision["actor"],
            channel=decision["channel"],
            domain=decision["domain"],
            action=decision["action"],
            risk_level=int(decision["risk_level"]),
            requires_human_approval=bool(decision["requires_human_approval"]),
            approval_captured=False,
            approved_by=None,
            approved_at=None,
            expires_at=None,
            effective_authorization=False,
            record_persisted=False,
            authorization_version=_AUTHORIZATION_RECORD_VERSION,
            external_side_effects=bool(decision.get("external_side_effects", False)),
        ),
        evaluation,
    )


def collect_authorization_record(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    user_id: str | None = None,
    client_id: str | None = None,
    agent_id: str | None = None,
    service_id: str | None = None,
    identity_source: str | None = None,
    expected_identity_binding_id: str | None = None,
    claimed_user_id: str | None = None,
    claimed_client_id: str | None = None,
    claimed_agent_id: str | None = None,
    claimed_service_id: str | None = None,
) -> dict[str, Any]:
    record, evaluation = build_authorization_record(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        user_id=user_id,
        client_id=client_id,
        agent_id=agent_id,
        service_id=service_id,
        identity_source=identity_source,
        expected_identity_binding_id=expected_identity_binding_id,
        claimed_user_id=claimed_user_id,
        claimed_client_id=claimed_client_id,
        claimed_agent_id=claimed_agent_id,
        claimed_service_id=claimed_service_id,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "authorization-record",
        "overall": "ready",
        "authorization_version": _AUTHORIZATION_RECORD_VERSION,
        "policy_only": True,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "record_persisted": False,
        "effective_authorization": False,
        "identity_verified": record.identity_verified,
        "identity_binding_id": record.identity_binding_id,
        "identity": {
            "identity_binding_id": record.identity_binding_id,
            "identity_verified": record.identity_verified,
            "identity_source": record.identity_source,
            "user_id": record.user_id,
            "client_id": record.client_id,
            "agent_id": record.agent_id,
            "service_id": record.service_id,
        },
        "record": record.to_dict(),
        "evaluation": evaluation,
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "adapters_elevate_permissions": False,
            "content_elevates_permissions": False,
            "approval_text_elevates_permissions": False,
            "identity_elevates_permissions": False,
        },
    }


def render_authorization_record(payload: dict[str, Any]) -> str:
    record = payload["record"]
    return "\n".join(
        [
            f"lai-gateway authorization-record: {payload['overall']}",
            f"version: {payload['version']}",
            f"authorization_version: {payload['authorization_version']}",
            f"record_id: {record['record_id']}",
            f"status: {record['status']}",
            f"decision_outcome: {record['decision_outcome']}",
            f"decision_id: {record['decision_id']}",
            f"evaluation_id: {record['evaluation_id']}",
            f"requested_capability: {record['requested_capability']}",
            f"granted_capability: {record.get('granted_capability') or 'none'}",
            f"adapter_id: {record.get('adapter_id') or 'none'}",
            f"identity_binding_id: {record['identity_binding_id']}",
            f"identity_verified: {str(record['identity_verified']).lower()}",
            f"risk_level: {record['risk_level']}",
            f"requires_human_approval: {str(record['requires_human_approval']).lower()}",
            f"approval_captured: {str(record['approval_captured']).lower()}",
            f"effective_authorization: {str(record['effective_authorization']).lower()}",
            f"record_persisted: {str(record['record_persisted']).lower()}",
            f"reason: {record['reason']}",
            "grants_permissions: false",
            "executes_tools: false",
        ]
    )
