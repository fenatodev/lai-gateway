from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .authorization_validation import collect_authorization_validation_gate
from .permission_decision import collect_permission_decision

_EFFECTIVE_AUTHORIZATION_VERSION = "effective-authorization/v2"
_DRY_RUN_SAFE_SCOPE = "adapter-dry-run"
_LOCAL_STATUS_READ_SCOPE = "local-status-read"
_LOCAL_STATUS_ADAPTER = "local_status"
_LOCAL_STATUS_STATUS_CAPABILITY = "local_status.status"
_LOCAL_MCP_SAFE_TOOL_SCOPE = "mcp-local-safe-tool"
_LOCAL_MCP_ADAPTER = "mcp_local"
_LOCAL_MCP_CAPABILITY = "mcp.local_echo_digest"


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
    permission_decision_id: str | None = None
    identity_binding_id: str | None = None
    identity_verified: bool = False
    local_non_dry_run_authorized: bool = False
    authorized_resource: str | None = None
    authorized_target: str | None = None

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


def _dry_run_scope_status(
    *,
    validation: dict[str, Any],
    dry_run: dict[str, Any],
) -> tuple[str, str, bool, bool, bool]:
    if _unsafe_flags(validation, dry_run):
        return "blocked", "effective authorization blocked by unsafe invariant", False, False, False
    if validation.get("status") == "blocked" or dry_run.get("status") == "blocked":
        return "blocked", "effective authorization blocked by validation or dry-run state", False, False, False
    if not validation.get("approval_validated"):
        return "pending", "effective authorization waits for validated captured approval", False, False, False
    if validation.get("status") != "validated_non_effective":
        return "blocked", "effective authorization requires validated non-effective gate", False, False, False
    if dry_run.get("status") != "simulated" or not dry_run.get("dry_run_executed"):
        return "blocked", "effective authorization requires successful dry-run simulation", False, False, False
    return "effective_for_dry_run_safe_operation", "dry-run-safe operation authorized without adapter dispatch", True, False, False


def _local_status_read_scope_status(
    *,
    permission: dict[str, Any],
    validation: dict[str, Any],
    dry_run: dict[str, Any],
) -> tuple[str, str, bool, bool, bool]:
    decision = permission["decision"]
    if _unsafe_flags(validation, dry_run):
        return "blocked", "local non-dry-run authorization blocked by unsafe invariant", False, False, False
    if not permission.get("identity_verified"):
        return "blocked", "local non-dry-run authorization requires verified principal identity", False, False, False
    if decision.get("adapter_id") != _LOCAL_STATUS_ADAPTER:
        return "blocked", "local non-dry-run authorization only permits local_status adapter", False, False, False
    if decision.get("requested_capability") != _LOCAL_STATUS_STATUS_CAPABILITY:
        return "blocked", "local non-dry-run authorization only permits local_status.status", False, False, False
    if decision.get("outcome") != "allow" or decision.get("granted_capability") != _LOCAL_STATUS_STATUS_CAPABILITY:
        return "blocked", "local non-dry-run authorization requires an explicit allow decision", False, False, False
    if bool(decision.get("external_side_effects")):
        return "blocked", "local non-dry-run authorization refuses external side effects", False, False, False
    return "effective_for_local_status_read", "local_status.status authorized for real local non-dry-run execution", True, True, True


def _local_mcp_safe_tool_scope_status(
    *,
    permission: dict[str, Any],
    validation: dict[str, Any],
    dry_run: dict[str, Any],
) -> tuple[str, str, bool, bool, bool]:
    decision = permission["decision"]
    if _unsafe_flags(validation, dry_run):
        return "blocked", "local MCP safe-tool authorization blocked by unsafe invariant", False, False, False
    if not permission.get("identity_verified"):
        return "blocked", "local MCP safe-tool authorization requires verified principal identity", False, False, False
    if decision.get("adapter_id") != _LOCAL_MCP_ADAPTER:
        return "blocked", "local MCP safe-tool authorization only permits mcp_local adapter", False, False, False
    if decision.get("requested_capability") != _LOCAL_MCP_CAPABILITY:
        return "blocked", "local MCP safe-tool authorization only permits mcp.local_echo_digest", False, False, False
    if decision.get("outcome") != "allow" or decision.get("granted_capability") != _LOCAL_MCP_CAPABILITY:
        return "blocked", "local MCP safe-tool authorization requires an explicit allow decision", False, False, False
    if bool(decision.get("external_side_effects")):
        return "blocked", "local MCP safe-tool authorization refuses external side effects", False, False, False
    return "effective_for_mcp_local_safe_tool", "mcp.local_echo_digest authorized for one governed local MCP-shaped tool", True, True, True


def _scope_status(
    *,
    operation_scope: str,
    validation: dict[str, Any],
    dry_run: dict[str, Any],
    permission: dict[str, Any],
) -> tuple[str, str, bool, bool, bool]:
    if operation_scope == _DRY_RUN_SAFE_SCOPE:
        return _dry_run_scope_status(validation=validation, dry_run=dry_run)
    if operation_scope == _LOCAL_STATUS_READ_SCOPE:
        return _local_status_read_scope_status(permission=permission, validation=validation, dry_run=dry_run)
    if operation_scope == _LOCAL_MCP_SAFE_TOOL_SCOPE:
        return _local_mcp_safe_tool_scope_status(permission=permission, validation=validation, dry_run=dry_run)
    return "blocked", "effective authorization scope is not allowed", False, False, False


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
) -> tuple[EffectiveAuthorization, dict[str, Any], dict[str, Any]]:
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
    permission_payload = collect_permission_decision(
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
    validation = gate_payload["validation"]
    dry_run = gate_payload["dry_run"]
    status, reason, scope_authorized, adapter_authorized, local_authorized = _scope_status(
        operation_scope=scope,
        validation=validation,
        dry_run=dry_run,
        permission=permission_payload,
    )
    decision = permission_payload["decision"]
    identity = permission_payload["identity"]
    effective_id = _effective_id(
        (
            _EFFECTIVE_AUTHORIZATION_VERSION,
            validation["validation_id"],
            dry_run["dry_run_id"],
            decision["decision_id"],
            scope,
            status,
            str(scope_authorized).lower(),
            str(adapter_authorized).lower(),
            str(local_authorized).lower(),
            decision["requested_capability"],
            decision.get("adapter_id") or "",
            identity["identity_binding_id"],
        )
    )
    result = EffectiveAuthorization(
        effective_authorization_id=effective_id,
        status=status,
        reason=reason,
        operation_scope=scope,
        scope_authorized=scope_authorized,
        adapter_capability_authorized=adapter_authorized,
        adapter_id=decision.get("adapter_id"),
        requested_capability=decision["requested_capability"],
        actor=decision["actor"],
        channel=decision["channel"],
        domain=decision["domain"],
        action=decision["action"],
        validation_id=validation["validation_id"],
        capture_id=validation["capture_id"],
        dry_run_id=dry_run["dry_run_id"],
        proposal_id=dry_run["proposal_id"],
        authorization_record_id=dry_run["authorization_record_id"],
        evaluation_id=dry_run["evaluation_id"],
        decision_id=validation["decision_id"],
        audit_log_id=dry_run["audit_log_id"],
        approval_intent=bool(validation["approval_intent"]),
        approval_captured=bool(validation["approval_captured"]),
        approval_validated=bool(validation["approval_validated"]),
        validation_status=validation["status"],
        dry_run_status=dry_run["status"],
        proposal_status=validation["proposal_status"],
        decision_outcome=validation["decision_outcome"],
        authorization_status=validation["authorization_status"],
        effective_authorization=scope_authorized,
        effective_authorization_version=_EFFECTIVE_AUTHORIZATION_VERSION,
        permission_decision_id=decision["decision_id"],
        identity_binding_id=identity["identity_binding_id"],
        identity_verified=bool(identity["identity_verified"]),
        local_non_dry_run_authorized=local_authorized,
        authorized_resource=(f"adapter:{decision.get('adapter_id')}" if local_authorized else None),
        authorized_target=(decision["requested_capability"] if local_authorized else None),
    )
    return result, gate_payload, permission_payload


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
    effective, gate_payload, permission_payload = build_effective_authorization(
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
        "operation": "effective-authorization",
        "overall": "ready",
        "effective_authorization_version": _EFFECTIVE_AUTHORIZATION_VERSION,
        "dry_run_safe_scope": _DRY_RUN_SAFE_SCOPE,
        "local_non_dry_run_scope": _LOCAL_STATUS_READ_SCOPE,
        "local_mcp_safe_tool_scope": _LOCAL_MCP_SAFE_TOOL_SCOPE,
        "effective_authorization": effective.effective_authorization,
        "scope_authorized": effective.scope_authorized,
        "adapter_capability_authorized": effective.adapter_capability_authorized,
        "local_non_dry_run_authorized": effective.local_non_dry_run_authorized,
        "authorization_persisted": False,
        "dispatch_enabled": False,
        "adapter_dispatched": False,
        "adapter_executed": False,
        "executes_tools": False,
        "external_side_effects": False,
        "effective": effective.to_dict(),
        "permission": permission_payload,
        "validation": gate_payload["validation"],
        "capture": gate_payload["capture"],
        "dry_run": gate_payload["dry_run"],
        "audit": gate_payload["audit"],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "adapter_capability_elevated": False,
            "effective_authorization_scope_limited": True,
            "local_non_dry_run_scope_limited": True,
            "approval_text_elevates_permissions": False,
            "identity_elevates_permissions": False,
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
        f"local_non_dry_run_authorized: {str(effective['local_non_dry_run_authorized']).lower()}",
        f"adapter_id: {effective.get('adapter_id') or 'none'}",
        f"requested_capability: {effective['requested_capability']}",
        f"identity_binding_id: {effective.get('identity_binding_id') or 'none'}",
        f"identity_verified: {str(effective.get('identity_verified', False)).lower()}",
        f"authorized_resource: {effective.get('authorized_resource') or 'none'}",
        f"authorized_target: {effective.get('authorized_target') or 'none'}",
        f"approval_validated: {str(effective['approval_validated']).lower()}",
        f"effective_authorization: {str(effective['effective_authorization']).lower()}",
        f"authorization_persisted: {str(effective['authorization_persisted']).lower()}",
        f"dispatch_enabled: {str(effective['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(effective['adapter_dispatched']).lower()}",
        f"adapter_executed: {str(effective['adapter_executed']).lower()}",
        f"executes_tools: {str(effective['executes_tools']).lower()}",
        f"reason: {effective['reason']}",
        "grants_permissions: false",
    ]
    return "\n".join(lines)
