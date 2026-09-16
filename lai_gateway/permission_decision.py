from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .identity import build_principal_identity

_DECISION_OUTCOMES = {"allow", "deny", "requires_approval"}
_RISK_LEVELS = {0, 1, 2, 3, 4, 5}
_POLICY_VERSION = "permission-decision/v1"


@dataclass(frozen=True)
class PermissionDecision:
    decision_id: str
    outcome: str
    reason: str
    requested_capability: str
    granted_capability: str | None
    risk_level: int
    requires_human_approval: bool
    actor: str
    channel: str
    domain: str
    action: str
    adapter_id: str | None
    identity_binding_id: str
    identity_verified: bool
    identity_source: str
    user_id: str
    client_id: str
    agent_id: str
    service_id: str
    policy_version: str
    grants_permission: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    starts_server: bool = False
    modifies_files: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bounded_text(value: str | None, *, default: str, limit: int = 96) -> str:
    text = (value or default).strip()
    if not text:
        text = default
    return text[:limit]


def _decision_id(parts: tuple[str, ...]) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"pd-{digest}"


def build_permission_decision(
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
) -> PermissionDecision:
    capability = _bounded_text(requested_capability, default="missing")
    actor_value = _bounded_text(actor, default="user")
    channel_value = _bounded_text(channel, default="gateway")
    domain_value = _bounded_text(domain, default="unknown")
    action_value = _bounded_text(action, default="unspecified")
    adapter_value = _bounded_text(adapter_id, default="") or None
    identity = build_principal_identity(
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

    outcome = "deny"
    reason = "requested capability is missing"
    granted_capability: str | None = None
    risk_level = 0
    requires_human_approval = False
    external_side_effects = False

    adapter: dict[str, Any] | None = None
    if capability != "missing" and adapter_value:
        registry = collect_adapter_registry(adapter_id=adapter_value)
        if registry["overall"] == "ready" and registry.get("adapters"):
            adapter = registry["adapters"][0]
        else:
            reason = "adapter is not registered"
            risk_level = 1
    elif capability != "missing":
        reason = "adapter id is required for capability decisions"
        risk_level = 1

    if adapter is not None:
        granted = set(adapter.get("granted_capabilities", []))
        requested = set(adapter.get("requested_capabilities", []))
        approval = set(adapter.get("human_approval_required_for", []))
        if capability in granted:
            outcome = "allow"
            reason = "requested capability is explicitly granted"
            granted_capability = capability
            risk_level = 1
        elif capability in approval or capability in requested:
            outcome = "requires_approval"
            reason = "requested capability is declared but not granted"
            risk_level = 4 if capability in approval else 3
            requires_human_approval = True
        else:
            outcome = "deny"
            reason = "requested capability is not declared by adapter contract"
            risk_level = 2
        external_side_effects = bool(
            adapter.get("external_side_effects_enabled")
            or adapter.get("network_access_enabled")
            or adapter.get("workflow_execution_enabled")
            or adapter.get("publication_enabled")
            or adapter.get("message_sending_enabled")
            or adapter.get("form_submission_enabled")
            or adapter.get("application_submission_enabled")
        )

    if not identity.identity_verified:
        outcome = "deny"
        reason = identity.reason
        granted_capability = None
        risk_level = max(risk_level, 4)
        requires_human_approval = False

    if outcome not in _DECISION_OUTCOMES:
        outcome = "deny"
    if risk_level not in _RISK_LEVELS:
        risk_level = 5

    decision_id = _decision_id(
        (
            _POLICY_VERSION,
            outcome,
            capability,
            adapter_value or "",
            actor_value,
            channel_value,
            domain_value,
            action_value,
            identity.identity_binding_id,
        )
    )
    return PermissionDecision(
        decision_id=decision_id,
        outcome=outcome,
        reason=reason,
        requested_capability=capability,
        granted_capability=granted_capability,
        risk_level=risk_level,
        requires_human_approval=requires_human_approval,
        actor=actor_value,
        channel=channel_value,
        domain=domain_value,
        action=action_value,
        adapter_id=adapter_value,
        identity_binding_id=identity.identity_binding_id,
        identity_verified=identity.identity_verified,
        identity_source=identity.identity_source,
        user_id=identity.user_id,
        client_id=identity.client_id,
        agent_id=identity.agent_id,
        service_id=identity.service_id,
        policy_version=_POLICY_VERSION,
        external_side_effects=external_side_effects,
    )


def collect_permission_decision(
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
    decision = build_permission_decision(
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
        "operation": "permission-decision",
        "overall": "ready",
        "policy_only": True,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "identity_verified": decision.identity_verified,
        "identity_binding_id": decision.identity_binding_id,
        "identity": {
            "identity_binding_id": decision.identity_binding_id,
            "identity_verified": decision.identity_verified,
            "identity_source": decision.identity_source,
            "user_id": decision.user_id,
            "client_id": decision.client_id,
            "agent_id": decision.agent_id,
            "service_id": decision.service_id,
        },
        "decision": decision.to_dict(),
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "adapters_elevate_permissions": False,
            "content_elevates_permissions": False,
            "identity_elevates_permissions": False,
        },
    }


def render_permission_decision(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    return "\n".join(
        [
            f"lai-gateway permission-decision: {payload['overall']}",
            f"version: {payload['version']}",
            f"decision_id: {decision['decision_id']}",
            f"outcome: {decision['outcome']}",
            f"requested_capability: {decision['requested_capability']}",
            f"granted_capability: {decision.get('granted_capability') or 'none'}",
            f"risk_level: {decision['risk_level']}",
            f"requires_human_approval: {str(decision['requires_human_approval']).lower()}",
            f"adapter_id: {decision.get('adapter_id') or 'none'}",
            f"identity_binding_id: {decision['identity_binding_id']}",
            f"identity_verified: {str(decision['identity_verified']).lower()}",
            f"reason: {decision['reason']}",
            "grants_permissions: false",
            "executes_tools: false",
        ]
    )
