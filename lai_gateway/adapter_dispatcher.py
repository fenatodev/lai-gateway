import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import collect_adapter_registry
from .authorization_recovery import collect_authorization_recovery
from .effective_authorization import collect_effective_authorization
from .local_status_adapter import can_handle_local_status, execute_local_status_adapter
from .permission_decision import collect_permission_decision

_ADAPTER_DISPATCHER_VERSION = "adapter-dispatcher/v3"
_DRY_RUN_SCOPE = "adapter-dry-run"
_LOCAL_STATUS_READ_SCOPE = "local-status-read"
_LOCAL_STATUS_HANDLER_ID = "local_status.in_process.v1"


@dataclass(frozen=True)
class AdapterDispatcherInterface:
    dispatch_id: str
    status: str
    reason: str
    dispatch_requested: bool
    dispatch_permitted: bool
    adapter_id: str | None
    adapter_status: str
    requested_capability: str
    actor: str
    channel: str
    domain: str
    action_sha256: str
    operation_scope: str
    effective_authorization_id: str
    validation_id: str
    capture_id: str
    dry_run_id: str
    proposal_id: str
    authorization_record_id: str
    evaluation_id: str
    decision_id: str
    audit_log_id: str
    permission_decision_id: str
    permission_outcome: str
    effective_authorization: bool
    scope_authorized: bool
    adapter_capability_authorized: bool
    handler_registered: bool
    handler_id: str | None
    dispatcher_version: str
    dispatch_enabled: bool = False
    adapter_dispatched: bool = False
    adapter_executed: bool = False
    executes_tools: bool = False
    external_side_effects: bool = False
    modifies_files: bool = False
    starts_server: bool = False
    grants_permission: bool = False
    authorization_grant_id: str | None = None
    authorization_recovery_status: str | None = None
    authorization_consumed: bool = False
    recovered_after_restart: bool = False
    retry_automatic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _dispatch_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"adi-{digest}"


def _action_sha256(action: str | None) -> str:
    text = (action or "").encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _adapter_status(adapter_id: str | None) -> str:
    if not adapter_id:
        return "missing"
    registry = collect_adapter_registry(adapter_id=adapter_id)
    if registry.get("overall") != "ready" or not registry.get("adapters"):
        return "missing"
    return str(registry["adapters"][0].get("status", "registered"))


def _strip_raw_action(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key == "action":
                result["action_sha256"] = _action_sha256(str(item))
            else:
                result[key] = _strip_raw_action(item)
        return result
    if isinstance(value, list):
        return [_strip_raw_action(item) for item in value]
    return value

def _local_handler_available(decision: dict[str, Any]) -> bool:
    return (
        decision.get("outcome") == "allow"
        and decision.get("granted_capability") == decision.get("requested_capability")
        and can_handle_local_status(
            decision.get("adapter_id"),
            decision.get("requested_capability"),
        )
    )


def _legacy_status(
    *,
    dispatch_requested: bool,
    effective: dict[str, Any],
    adapter_status: str,
) -> tuple[str, str, bool, bool]:
    if adapter_status == "missing":
        return "blocked", "adapter contract is missing", False, False
    if effective.get("operation_scope") != _DRY_RUN_SCOPE:
        return "blocked", "dispatcher interface only accepts dry-run-safe scope", False, False
    if effective.get("status") == "blocked":
        return "blocked", "dispatcher blocked by underlying authorization state", False, False
    if not effective.get("effective_authorization"):
        return "pending", "dispatcher waits for scoped effective authorization", False, False
    if effective.get("adapter_capability_authorized"):
        return "blocked", "dispatcher refuses broad adapter capability authorization", False, False
    if dispatch_requested:
        return "blocked", "dispatcher has no real adapter handlers registered", False, False
    return "planned_not_dispatched", "dispatcher interface ready without dispatch", False, False


def _local_status(
    *,
    dispatch_requested: bool,
    decision: dict[str, Any],
    effective: dict[str, Any],
    authorization_grant_id: str | None,
    authorization_recovery: dict[str, Any] | None,
) -> tuple[str, str, bool, bool]:
    if not _local_handler_available(decision):
        return "blocked", "local handler is not allowlisted for this decision", False, False
    if not dispatch_requested:
        return "planned_local_handler", "local handler is registered but dispatch was not requested", False, True
    if effective.get("operation_scope") != _LOCAL_STATUS_READ_SCOPE:
        return "blocked", "local_status dispatch requires local-status-read effective authorization", False, True
    if not effective.get("effective_authorization") or not effective.get("local_non_dry_run_authorized"):
        return "blocked", "local_status dispatch blocked without local non-dry-run authorization", False, True
    if not effective.get("adapter_capability_authorized"):
        return "blocked", "local_status dispatch requires adapter capability authorization", False, True
    if not authorization_grant_id:
        return "blocked", "local_status dispatch requires a persisted single-use authorization grant", False, True
    if not authorization_recovery or authorization_recovery.get("status") != "consumed_for_single_use":
        return "blocked", "local_status dispatch blocked until persisted authorization is consumed", False, True
    if not authorization_recovery.get("dispatch_allowed"):
        return "blocked", "authorization recovery did not allow dispatch", False, True
    return "dispatched_local", "allowlisted local handler executed after single-use persisted authorization", True, True


def build_adapter_dispatcher_interface(
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
    dispatch_requested: bool = False,
    authorization_grant_id: str | None = None,
    authorization_dir: str | Path | None = None,
    scope_root: Path | None = None,
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
) -> tuple[AdapterDispatcherInterface, dict[str, Any], dict[str, Any] | None]:
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
    decision = permission_payload["decision"]
    effective_payload = collect_effective_authorization(
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
    effective = effective_payload["effective"]
    adapter_status = _adapter_status(decision.get("adapter_id"))
    handler_registered = _local_handler_available(decision)
    authorization_recovery_payload = None
    if (
        handler_registered
        and dispatch_requested
        and effective.get("operation_scope") == _LOCAL_STATUS_READ_SCOPE
        and authorization_grant_id
    ):
        authorization_recovery_payload = collect_authorization_recovery(
            recovery_action="consume",
            authorization_grant_id=authorization_grant_id,
            authorization_dir=authorization_dir,
            scope_root=scope_root,
            requested_capability=requested_capability,
            adapter_id=adapter_id,
            actor=actor,
            channel=channel,
            domain=domain,
            action=action,
            parameters=parameters,
            approval_intent=approval_intent,
            approved_by=approved_by,
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
    if handler_registered:
        status, reason, executed, registered = _local_status(
            dispatch_requested=dispatch_requested,
            decision=decision,
            effective=effective,
            authorization_grant_id=authorization_grant_id,
            authorization_recovery=authorization_recovery_payload,
        )
    else:
        status, reason, executed, registered = _legacy_status(
            dispatch_requested=dispatch_requested,
            effective=effective,
            adapter_status=adapter_status,
        )
    handler_result = None
    if executed:
        handler_result = execute_local_status_adapter(
            requested_capability=decision["requested_capability"],
            action=action,
            parameters=parameters,
        )
    dispatch_id = _dispatch_id(
        (
            _ADAPTER_DISPATCHER_VERSION,
            decision["decision_id"],
            effective["effective_authorization_id"],
            str(dispatch_requested).lower(),
            authorization_grant_id or "",
            status,
            decision.get("adapter_id") or "",
            decision["requested_capability"],
        )
    )
    dispatcher = AdapterDispatcherInterface(
        dispatch_id=dispatch_id,
        status=status,
        reason=reason,
        dispatch_requested=dispatch_requested,
        dispatch_permitted=executed,
        adapter_id=decision.get("adapter_id"),
        adapter_status=adapter_status,
        requested_capability=decision["requested_capability"],
        actor=decision["actor"],
        channel=decision["channel"],
        domain=decision["domain"],
        action_sha256=_action_sha256(action),
        operation_scope=effective["operation_scope"],
        effective_authorization_id=effective["effective_authorization_id"],
        validation_id=effective["validation_id"],
        capture_id=effective["capture_id"],
        dry_run_id=effective["dry_run_id"],
        proposal_id=effective["proposal_id"],
        authorization_record_id=effective["authorization_record_id"],
        evaluation_id=effective["evaluation_id"],
        decision_id=effective["decision_id"],
        audit_log_id=effective["audit_log_id"],
        permission_decision_id=decision["decision_id"],
        permission_outcome=decision["outcome"],
        effective_authorization=bool(effective["effective_authorization"]),
        scope_authorized=bool(effective["scope_authorized"]),
        adapter_capability_authorized=bool(effective.get("adapter_capability_authorized")),
        handler_registered=registered,
        handler_id=_LOCAL_STATUS_HANDLER_ID if registered else None,
        dispatcher_version=_ADAPTER_DISPATCHER_VERSION,
        dispatch_enabled=executed,
        adapter_dispatched=executed,
        adapter_executed=executed,
        authorization_grant_id=authorization_grant_id,
        authorization_recovery_status=(authorization_recovery_payload or {}).get("status"),
        authorization_consumed=bool((authorization_recovery_payload or {}).get("authorization_consumed")),
        recovered_after_restart=bool((authorization_recovery_payload or {}).get("recovered_after_restart")),
        retry_automatic=False,
    )
    governance = effective_payload | {"permission": permission_payload}
    if authorization_recovery_payload is not None:
        governance["authorization_recovery"] = authorization_recovery_payload
    return dispatcher, governance, handler_result


def collect_adapter_dispatcher_interface(
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
    dispatch_requested: bool = False,
    authorization_grant_id: str | None = None,
    authorization_dir: str | Path | None = None,
    scope_root: Path | None = None,
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
    dispatcher, governance_payload, handler_result = build_adapter_dispatcher_interface(
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
        dispatch_requested=dispatch_requested,
        authorization_grant_id=authorization_grant_id,
        authorization_dir=authorization_dir,
        scope_root=scope_root,
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
    executed = bool(dispatcher.adapter_executed)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "adapter-dispatcher",
        "overall": "ready",
        "dispatcher_version": _ADAPTER_DISPATCHER_VERSION,
        "interface_only": not dispatcher.handler_registered,
        "local_handler_enabled": dispatcher.handler_registered,
        "dispatch_requested": bool(dispatch_requested),
        "dispatch_permitted": dispatcher.dispatch_permitted,
        "dispatch_enabled": dispatcher.dispatch_enabled,
        "adapter_dispatched": dispatcher.adapter_dispatched,
        "adapter_executed": dispatcher.adapter_executed,
        "executes_tools": False,
        "external_side_effects": False,
        "result": "local_status" if executed else "not_dispatched",
        "dispatcher": dispatcher.to_dict(),
        "handler_result": handler_result,
        "permission": _strip_raw_action(governance_payload["permission"]),
        "effective": _strip_raw_action(governance_payload["effective"]),
        "validation": _strip_raw_action(governance_payload["validation"]),
        "capture": _strip_raw_action(governance_payload["capture"]),
        "dry_run": _strip_raw_action(governance_payload["dry_run"]),
        "authorization_recovery": _strip_raw_action(governance_payload.get("authorization_recovery")),
        "audit": governance_payload["audit"],
        "security": {
            "prints_tokens": False,
            "registers_real_handlers": dispatcher.handler_registered,
            "registered_handler_id": dispatcher.handler_id,
            "dispatches_adapter": dispatcher.adapter_dispatched,
            "executes_tools": False,
            "external_side_effects": False,
            "grants_permissions": False,
            "adapter_capability_elevated": False,
            "requires_effective_authorization": True,
            "requires_single_use_authorization": dispatcher.handler_registered,
            "authorization_consumed": dispatcher.authorization_consumed,
            "requires_registered_handler": bool(dispatch_requested),
            "local_only": dispatcher.handler_registered,
            "network_access": False,
            "credential_access": False,
            "filesystem_write": dispatcher.authorization_consumed,
            "authorization_state_write": dispatcher.authorization_consumed,
            "shell_execution": False,
        },
    }


def render_adapter_dispatcher_interface(payload: dict[str, Any]) -> str:
    dispatcher = payload["dispatcher"]
    lines = [
        f"lai-gateway adapter-dispatcher: {payload['overall']}",
        f"version: {payload['version']}",
        f"dispatcher_version: {payload['dispatcher_version']}",
        f"dispatch_id: {dispatcher['dispatch_id']}",
        f"status: {dispatcher['status']}",
        f"interface_only: {str(payload['interface_only']).lower()}",
        f"local_handler_enabled: {str(payload['local_handler_enabled']).lower()}",
        f"dispatch_requested: {str(dispatcher['dispatch_requested']).lower()}",
        f"dispatch_permitted: {str(dispatcher['dispatch_permitted']).lower()}",
        f"dispatch_enabled: {str(dispatcher['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(dispatcher['adapter_dispatched']).lower()}",
        f"adapter_executed: {str(dispatcher['adapter_executed']).lower()}",
        f"handler_registered: {str(dispatcher['handler_registered']).lower()}",
        f"operation_scope: {dispatcher['operation_scope']}",
        f"adapter_id: {dispatcher.get('adapter_id') or 'none'}",
        f"requested_capability: {dispatcher['requested_capability']}",
        f"permission_outcome: {dispatcher['permission_outcome']}",
        f"effective_authorization: {str(dispatcher['effective_authorization']).lower()}",
        f"adapter_capability_authorized: {str(dispatcher['adapter_capability_authorized']).lower()}",
        f"authorization_grant_id: {dispatcher.get('authorization_grant_id') or 'none'}",
        f"authorization_recovery_status: {dispatcher.get('authorization_recovery_status') or 'none'}",
        f"authorization_consumed: {str(dispatcher.get('authorization_consumed', False)).lower()}",
        f"retry_automatic: {str(dispatcher.get('retry_automatic', False)).lower()}",
        f"result: {payload['result']}",
        f"reason: {dispatcher['reason']}",
        "executes_tools: false",
        "external_side_effects: false",
        "grants_permissions: false",
    ]
    return "\n".join(lines)

