from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .authorization_record import collect_authorization_record

_ADAPTER_INVOCATION_PROPOSAL_VERSION = "adapter-invocation-proposal/v1"
_SECRET_MARKERS = (
    "bearer ",
    "authorization:",
    "api_key=",
    "apikey=",
    "password=",
    "secret=",
    "token=",
    "ghp_",
    "github_pat_",
    "sk-",
    "xoxb-",
    "xoxp-",
)


@dataclass(frozen=True)
class AdapterInvocationProposal:
    proposal_id: str
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
    decision_id: str
    evaluation_id: str
    authorization_record_id: str
    decision_outcome: str
    authorization_status: str
    requires_human_approval: bool
    effective_authorization: bool
    proposal_version: str
    proposal_only: bool = True
    dispatch_enabled: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    grants_permission: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_public_text(value: str | None, *, default: str, limit: int = 96) -> str:
    text = (value or default).strip()
    if not text:
        text = default
    lowered = text.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        return "[redacted]"
    return text[:limit]


def _safe_parameters(parameters: dict[str, str] | None) -> dict[str, str]:
    if not parameters:
        return {}
    safe: dict[str, str] = {}
    for raw_key, raw_value in sorted(parameters.items()):
        key = _safe_public_text(str(raw_key), default="param", limit=40)
        value = _safe_public_text(str(raw_value), default="", limit=120)
        lowered_key = key.lower()
        if any(marker.rstrip("=:") in lowered_key for marker in _SECRET_MARKERS):
            value = "[redacted]"
        safe[key] = value
    return safe


def _proposal_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"aip-{digest}"


def _adapter_status(adapter_id: str | None) -> str:
    if not adapter_id:
        return "missing"
    payload = collect_adapter_registry(adapter_id=adapter_id)
    if payload.get("overall") != "ready" or not payload.get("adapters"):
        return "missing"
    return str(payload["adapters"][0].get("status", "registered"))


def _proposal_status(record: dict[str, Any], adapter_status: str) -> tuple[str, str]:
    if adapter_status == "missing":
        return "blocked", "adapter contract is missing"
    authorization_status = record.get("status")
    if authorization_status == "requires_human_approval":
        return "requires_authorization", "adapter invocation requires human authorization before execution"
    if authorization_status == "blocked":
        return "blocked", "policy and authorization record blocked the proposed invocation"
    return "not_executable", "proposal is read-only and cannot dispatch adapter execution"


def build_adapter_invocation_proposal(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> tuple[AdapterInvocationProposal, dict[str, Any]]:
    safe_parameters = _safe_parameters(parameters)
    authorization = collect_authorization_record(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
    )
    record = authorization["record"]
    evaluation = authorization["evaluation"]
    decision = evaluation["decision"]
    adapter_status = _adapter_status(decision.get("adapter_id"))
    status, reason = _proposal_status(record, adapter_status)
    proposal_id = _proposal_id(
        (
            _ADAPTER_INVOCATION_PROPOSAL_VERSION,
            record["record_id"],
            evaluation["evaluation_id"],
            decision["decision_id"],
            status,
            decision["requested_capability"],
            decision.get("adapter_id") or "",
            decision["actor"],
            decision["channel"],
            decision["domain"],
            decision["action"],
            repr(tuple(sorted(safe_parameters.items()))),
        )
    )
    return (
        AdapterInvocationProposal(
            proposal_id=proposal_id,
            status=status,
            reason=reason,
            adapter_id=decision.get("adapter_id"),
            adapter_status=adapter_status,
            requested_capability=decision["requested_capability"],
            actor=decision["actor"],
            channel=decision["channel"],
            domain=decision["domain"],
            action=decision["action"],
            parameters=safe_parameters,
            decision_id=decision["decision_id"],
            evaluation_id=evaluation["evaluation_id"],
            authorization_record_id=record["record_id"],
            decision_outcome=decision["outcome"],
            authorization_status=record["status"],
            requires_human_approval=bool(record["requires_human_approval"]),
            effective_authorization=False,
            proposal_version=_ADAPTER_INVOCATION_PROPOSAL_VERSION,
            external_side_effects=False,
        ),
        authorization,
    )


def collect_adapter_invocation_proposal(
    *,
    requested_capability: str | None,
    adapter_id: str | None = None,
    actor: str | None = None,
    channel: str | None = None,
    domain: str | None = None,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    proposal, authorization = build_adapter_invocation_proposal(
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
        "operation": "adapter-invocation-proposal",
        "overall": "ready",
        "proposal_version": _ADAPTER_INVOCATION_PROPOSAL_VERSION,
        "proposal_only": True,
        "starts_server": False,
        "modifies_files": False,
        "executes_tools": False,
        "dispatch_enabled": False,
        "effective_authorization": False,
        "proposal": proposal.to_dict(),
        "authorization": authorization,
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "dispatches_adapter": False,
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "adapters_elevate_permissions": False,
            "content_elevates_permissions": False,
            "approval_text_elevates_permissions": False,
        },
    }


def render_adapter_invocation_proposal(payload: dict[str, Any]) -> str:
    proposal = payload["proposal"]
    lines = [
        f"lai-gateway adapter-invocation-proposal: {payload['overall']}",
        f"version: {payload['version']}",
        f"proposal_version: {payload['proposal_version']}",
        f"proposal_id: {proposal['proposal_id']}",
        f"status: {proposal['status']}",
        f"adapter_id: {proposal.get('adapter_id') or 'none'}",
        f"adapter_status: {proposal['adapter_status']}",
        f"requested_capability: {proposal['requested_capability']}",
        f"decision_outcome: {proposal['decision_outcome']}",
        f"authorization_status: {proposal['authorization_status']}",
        f"requires_human_approval: {str(proposal['requires_human_approval']).lower()}",
        f"effective_authorization: {str(proposal['effective_authorization']).lower()}",
        f"dispatch_enabled: {str(proposal['dispatch_enabled']).lower()}",
        f"executes_tools: {str(proposal['executes_tools']).lower()}",
        f"reason: {proposal['reason']}",
    ]
    if proposal.get("parameters"):
        lines.append("parameters:")
        for key, value in proposal["parameters"].items():
            lines.append(f"- {key}: {value}")
    lines.extend(["grants_permissions: false", "proposal_only: true"])
    return "\n".join(lines)
