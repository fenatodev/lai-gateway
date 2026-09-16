from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .permission_decision import PermissionDecision, build_permission_decision

_POLICY_EVALUATOR_VERSION = "policy-evaluator/v1"
_SECRET_MARKERS = (
    "bearer ",
    "authorization:",
    "api_key=",
    "apikey=",
    "password=",
    "secret=",
    "ghp_",
    "github_pat_",
    "sk-",
    "xoxb-",
    "xoxp-",
)


@dataclass(frozen=True)
class PolicyRuleResult:
    rule_id: str
    status: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _safe_public_text(value: str | None, *, default: str, limit: int = 96) -> str:
    text = (value or default).strip()
    if not text:
        text = default
    lowered = text.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        return "[redacted]"
    return text[:limit]


def _evaluation_id(decision: PermissionDecision, rules: tuple[PolicyRuleResult, ...]) -> str:
    material = "|".join(
        [
            _POLICY_EVALUATOR_VERSION,
            decision.decision_id,
            decision.outcome,
            decision.requested_capability,
            decision.adapter_id or "",
            *[f"{rule.rule_id}:{rule.status}" for rule in rules],
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"pe-{digest}"


def _adapter_contract(adapter_id: str | None) -> dict[str, Any] | None:
    if not adapter_id:
        return None
    payload = collect_adapter_registry(adapter_id=adapter_id)
    if payload.get("overall") != "ready" or not payload.get("adapters"):
        return None
    return payload["adapters"][0]


def _rule(rule_id: str, status: str, reason: str) -> PolicyRuleResult:
    return PolicyRuleResult(rule_id=rule_id, status=status, reason=reason)


def evaluate_policy_request(
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
) -> tuple[PermissionDecision, tuple[PolicyRuleResult, ...]]:
    capability = _safe_public_text(requested_capability, default="missing")
    adapter_value = _safe_public_text(adapter_id, default="") or None
    actor_value = _safe_public_text(actor, default="user")
    channel_value = _safe_public_text(channel, default="gateway")
    domain_value = _safe_public_text(domain, default="unknown")
    action_value = _safe_public_text(action, default="unspecified")

    decision = build_permission_decision(
        requested_capability=capability,
        adapter_id=adapter_value,
        actor=actor_value,
        channel=channel_value,
        domain=domain_value,
        action=action_value,
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
    adapter = _adapter_contract(adapter_value)
    declared = set(adapter.get("requested_capabilities", [])) if adapter else set()
    granted = set(adapter.get("granted_capabilities", [])) if adapter else set()
    approval_required = set(adapter.get("human_approval_required_for", [])) if adapter else set()

    rules: list[PolicyRuleResult] = [
        _rule("request.normalized", "pass", "request fields are bounded and secret-shaped values are redacted"),
    ]
    if decision.identity_verified:
        rules.append(_rule("identity.verified", "pass", "user/client/agent/service binding is verified from a trusted source"))
    else:
        rules.append(_rule("identity.verified", "fail", "identity binding is not trusted or drifted"))

    if capability == "missing":
        rules.append(_rule("capability.present", "fail", "requested capability is required"))
    else:
        rules.append(_rule("capability.present", "pass", "requested capability is present"))

    if adapter_value is None:
        rules.append(_rule("adapter.registered", "fail", "adapter id is required"))
    elif adapter is None:
        rules.append(_rule("adapter.registered", "fail", "adapter is not registered"))
    else:
        rules.append(_rule("adapter.registered", "pass", "adapter contract was found"))

    if adapter is None:
        rules.append(_rule("capability.declared", "fail", "no adapter contract can declare the requested capability"))
    elif capability in declared or capability in approval_required or capability in granted:
        rules.append(_rule("capability.declared", "pass", "capability is declared by the adapter contract"))
    else:
        rules.append(_rule("capability.declared", "fail", "capability is not declared by the adapter contract"))

    if capability in granted:
        rules.append(_rule("capability.granted", "pass", "capability is explicitly granted"))
    else:
        rules.append(_rule("capability.granted", "fail", "capability is not explicitly granted"))

    if decision.requires_human_approval:
        rules.append(_rule("human_approval.boundary", "requires_approval", "human approval is required before execution"))
    else:
        rules.append(_rule("human_approval.boundary", "pass", "no human approval can be inferred for this denied or allowed decision"))

    if adapter and adapter.get("grants_permissions"):
        rules.append(_rule("authority.boundary", "fail", "adapter contract must not grant permissions"))
    else:
        rules.append(_rule("authority.boundary", "pass", "adapter/channel/skill content does not grant permissions"))

    rules.append(_rule("execution.boundary", "pass", "policy evaluation is read-only and does not execute tools"))
    return decision, tuple(rules)


def collect_policy_evaluation(
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
    decision, rules = evaluate_policy_request(
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
        "operation": "policy-evaluator",
        "overall": "ready",
        "policy_version": _POLICY_EVALUATOR_VERSION,
        "policy_only": True,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "evaluation_id": _evaluation_id(decision, rules),
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
        "rules": [rule.to_dict() for rule in rules],
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


def render_policy_evaluation(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    lines = [
        f"lai-gateway policy-evaluator: {payload['overall']}",
        f"version: {payload['version']}",
        f"policy_version: {payload['policy_version']}",
        f"evaluation_id: {payload['evaluation_id']}",
        f"outcome: {decision['outcome']}",
        f"requested_capability: {decision['requested_capability']}",
        f"adapter_id: {decision.get('adapter_id') or 'none'}",
        f"risk_level: {decision['risk_level']}",
        f"requires_human_approval: {str(decision['requires_human_approval']).lower()}",
        f"identity_binding_id: {decision['identity_binding_id']}",
        f"identity_verified: {str(decision['identity_verified']).lower()}",
        "rules:",
    ]
    for rule in payload.get("rules", []):
        lines.append(f"- {rule['rule_id']}: {rule['status']} - {rule['reason']}")
    lines.extend(["grants_permissions: false", "executes_tools: false"])
    return "\n".join(lines)
