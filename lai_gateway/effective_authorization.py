from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .authorization_validation import collect_authorization_validation_gate

_EFFECTIVE_AUTHORIZATION_VERSION = "effective-authorization/v1"
_DRY_RUN_SAFE_SCOPE = "adapter-dry-run"


@dataclass(frozen=True)
class EffectiveAuthorization:
    effective_authorization_id: str
    status: str
    reason: str
    operation_scope: str
    scope_authorized: bool
    adapter_capability_authorized: bool
    adapter_id: str | None
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action: str
    validation_id: str
    capture_id: str
    dry_run_id: str
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    approval_intent: bool
    approval_captured: bool
    approval_validated: bool
    validation_status: str
    dry_run_status: str
    proposal_status: str
    decision_outcome: str
    authorization_status: str
    effective_authorization: bool
    effective_authorization_version: str
    authorization_persisted: bool = False
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


def _effective_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"eaz-{digest}"
def _bool(value: Any) -> bool:
    return bool(value)


def _unsafe_flags(validation: dict[str, Any], dry_run: dict[str, Any]) -> bool:
    return any(
        _bool(value)
        for value in (
            validation.get("effective_authorization"),
            validation.get("dispatch_enabled"),
            validation.get("adapter_dispatched"),
            validation.get("adapter_executed"),
            validation.get("executes_tools"),
            validation.get("external_side_effects"),
            validation.get("modifies_files"),
            validation.get("starts_server"),
            dry_run.get("effective_authorization"),
            dry_run.get("dispatch_enabled"),
            dry_run.get("adapter_dispatched"),
            dry_run.get("adapter_executed"),
            dry_run.get("executes_tools"),
        )
    )
def _scope_status(
    *,
    operation_scope: str,
    validation: dict[str, Any],
    dry_run: dict[str, Any],
) -> tuple[str, str, bool]:
    if operation_scope != _DRY_RUN_SAFE_SCOPE:
        return "blocked", "effective authorization is limited to adapter-dry-run scope", False
    if _unsafe_flags(validation, dry_run):
        return "blocked", "effective authorization blocked by unsafe invariant", False
    if validation.get("status") == "blocked" or dry_run.get("status") == "blocked":
        return "blocked", "effective authorization blocked by validation or dry-run state", False
    if not validation.get("approval_validated"):
        return "pending", "effective authorization waits for validated captured approval", False
    if validation.get("status") != "validated_non_effective":
        return "blocked", "effective authorization requires validated non-effective gate", False
    if dry_run.get("status") != "simulated" or not dry_run.get("dry_run_executed"):
        return "blocked", "effective authorization requires successful dry-run simulation", False
    return "effective_for_dry_run_safe_operation", "dry-run-safe operation authorized without adapter dispatch", True
def build_effective_authorization(
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
    operation_scope: str | None = None,
) -> tuple[EffectiveAuthorization, dict[str, Any]]:
    scope = (operation_scope or _DRY_RUN_SAFE_SCOPE).strip() or _DRY_RUN_SAFE_SCOPE
    gate_payload = collect_authorization_validation_gate(
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
    validation = gate_payload["validation"]
    dry_run = gate_payload["dry_run"]
    status, reason, authorized = _scope_status(
        operation_scope=scope,
        validation=validation,
        dry_run=dry_run,
    )
    effective_id = _effective_id(
        (
            _EFFECTIVE_AUTHORIZATION_VERSION,
            validation["validation_id"],
            dry_run["dry_run_id"],
            scope,
            status,
            str(authorized).lower(),
            validation["requested_capability"],
            validation.get("adapter_id") or "",
        )
    )
    result = EffectiveAuthorization(
        effective_authorization_id=effective_id,
        status=status,
        reason=reason,
        operation_scope=scope,
        scope_authorized=authorized,
        adapter_capability_authorized=False,
        adapter_id=validation.get("adapter_id"),
        requested_capability=validation["requested_capability"],
        actor=validation["actor"],
        channel=validation["channel"],
        domain=validation["domain"],
        action=validation["action"],
        validation_id=validation["validation_id"],
        capture_id=validation["capture_id"],
        dry_run_id=dry_run["dry_run_id"],
        proposal_id=dry_run["proposal_id"],
        authorization_record_id=dry_run["authorization_record_id"],
        evaluation_id=dry_run["evaluation_id"],
        decision_id=dry_run["decision_id"],
        audit_log_id=dry_run["audit_log_id"],
        approval_intent=bool(validation["approval_intent"]),
        approval_captured=bool(validation["approval_captured"]),
        approval_validated=bool(validation["approval_validated"]),
        validation_status=validation["status"],
        dry_run_status=dry_run["status"],
        proposal_status=validation["proposal_status"],
        decision_outcome=validation["decision_outcome"],
        authorization_status=validation["authorization_status"],
        effective_authorization=authorized,
        effective_authorization_version=_EFFECTIVE_AUTHORIZATION_VERSION,
    )
    return result, gate_payload
def collect_effective_authorization(
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
    operation_scope: str | None = None,
) -> dict[str, Any]:
    effective, gate_payload = build_effective_authorization(
        requested_capability=requested_capability,
        adapter_id=adapter_id,
        actor=actor,
        channel=channel,
        domain=domain,
        action=action,
        parameters=parameters,
        approval_intent=approval_intent,
        approved_by=approved_by,
        operation_scope=operation_scope,
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "effective-authorization",
        "overall": "ready",
        "effective_authorization_version": _EFFECTIVE_AUTHORIZATION_VERSION,
        "dry_run_safe_scope": _DRY_RUN_SAFE_SCOPE,
        "effective_authorization": effective.effective_authorization,
        "scope_authorized": effective.scope_authorized,
        "adapter_capability_authorized": False,
        "authorization_persisted": False,
        "dispatch_enabled": False,
        "adapter_dispatched": False,
        "adapter_executed": False,
        "executes_tools": False,
        "external_side_effects": False,
        "effective": effective.to_dict(),
        "validation": gate_payload["validation"],
        "capture": gate_payload["capture"],
        "dry_run": gate_payload["dry_run"],
        "audit": gate_payload["audit"],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "adapter_capability_elevated": False,
            "effective_authorization_scope_limited": True,
            "approval_text_elevates_permissions": False,
            "persists_authorization": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
        },
    }


def render_effective_authorization(payload: dict[str, Any]) -> str:
    effective = payload["effective"]
    lines = [
        f"lai-gateway effective-authorization: {payload['overall']}",
        f"version: {payload['version']}",
        f"effective_authorization_version: {payload['effective_authorization_version']}",
        f"effective_authorization_id: {effective['effective_authorization_id']}",
        f"status: {effective['status']}",
        f"operation_scope: {effective['operation_scope']}",
        f"scope_authorized: {str(effective['scope_authorized']).lower()}",
        f"adapter_capability_authorized: {str(effective['adapter_capability_authorized']).lower()}",
        f"adapter_id: {effective.get('adapter_id') or 'none'}",
        f"requested_capability: {effective['requested_capability']}",
        f"approval_validated: {str(effective['approval_validated']).lower()}",
        f"effective_authorization: {str(effective['effective_authorization']).lower()}",
        f"authorization_persisted: {str(effective['authorization_persisted']).lower()}",
        f"dispatch_enabled: {str(effective['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(effective['adapter_dispatched']).lower()}",
        f"adapter_executed: {str(effective['adapter_executed']).lower()}",
        f"executes_tools: {str(effective['executes_tools']).lower()}",
        f"reason: {effective['reason']}",
        "grants_permissions: false",
        "adapter_capability_authorized: false",
    ]
    return "\n".join(lines)
