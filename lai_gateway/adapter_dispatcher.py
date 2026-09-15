from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from . import __version__
from .effective_authorization import collect_effective_authorization

_ADAPTER_DISPATCHER_VERSION = "adapter-dispatcher/v1"


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
    effective_authorization: bool
    scope_authorized: bool
    adapter_capability_authorized: bool
    handler_registered: bool
    dispatcher_version: str
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

def _dispatch_id(material: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(material).encode("utf-8")).hexdigest()[:16]
    return f"adi-{digest}"


def _action_sha256(action: str | None) -> str:
    text = (action or "").encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _adapter_status(effective: dict[str, Any]) -> str:
    if not effective.get("adapter_id"):
        return "missing"
    if effective.get("requested_capability") in {"missing", ""}:
        return "missing"
    if effective.get("decision_outcome") == "deny":
        return "missing"
    return "registered"

def _dispatch_status(
    *,
    dispatch_requested: bool,
    effective: dict[str, Any],
    adapter_status: str,
) -> tuple[str, str, bool]:
    if adapter_status == "missing":
        return "blocked", "adapter contract is missing", False
    if effective.get("operation_scope") != "adapter-dry-run":
        return "blocked", "dispatcher interface only accepts dry-run-safe scope", False
    if effective.get("status") == "blocked":
        return "blocked", "dispatcher blocked by underlying authorization state", False
    if not effective.get("effective_authorization"):
        return "pending", "dispatcher waits for scoped effective authorization", False
    if effective.get("adapter_capability_authorized"):
        return "blocked", "dispatcher refuses broad adapter capability authorization", False
    if dispatch_requested:
        return "blocked", "dispatcher has no real adapter handlers registered", False
    return "planned_not_dispatched", "dispatcher interface ready without dispatch", False

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
) -> tuple[AdapterDispatcherInterface, dict[str, Any]]:
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
    )
    effective = effective_payload["effective"]
    adapter_status = _adapter_status(effective)
    status, reason, permitted = _dispatch_status(
        dispatch_requested=dispatch_requested,
        effective=effective,
        adapter_status=adapter_status,
    )
    dispatch_id = _dispatch_id(
        (
            _ADAPTER_DISPATCHER_VERSION,
            effective["effective_authorization_id"],
            str(dispatch_requested).lower(),
            status,
            effective["operation_scope"],
            effective.get("adapter_id") or "",
            effective["requested_capability"],
        )
    )
    result = AdapterDispatcherInterface(
        dispatch_id=dispatch_id,
        status=status,
        reason=reason,
        dispatch_requested=dispatch_requested,
        dispatch_permitted=permitted,
        adapter_id=effective.get("adapter_id"),
        adapter_status=adapter_status,
        requested_capability=effective["requested_capability"],
        actor=effective["actor"],
        channel=effective["channel"],
        domain=effective["domain"],
        action_sha256=_action_sha256(effective.get("action")),
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
        effective_authorization=bool(effective["effective_authorization"]),
        scope_authorized=bool(effective["scope_authorized"]),
        adapter_capability_authorized=bool(effective["adapter_capability_authorized"]),
        handler_registered=False,
        dispatcher_version=_ADAPTER_DISPATCHER_VERSION,
    )
    return result, effective_payload

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
) -> dict[str, Any]:
    dispatcher, effective_payload = build_adapter_dispatcher_interface(
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
    )
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "adapter-dispatcher",
        "overall": "ready",
        "dispatcher_version": _ADAPTER_DISPATCHER_VERSION,
        "interface_only": True,
        "dispatch_requested": bool(dispatch_requested),
        "dispatch_permitted": dispatcher.dispatch_permitted,
        "dispatch_enabled": False,
        "adapter_dispatched": False,
        "adapter_executed": False,
        "executes_tools": False,
        "external_side_effects": False,
        "result": "not_dispatched",
        "dispatcher": dispatcher.to_dict(),
        "effective": _strip_raw_action(effective_payload["effective"]),
        "validation": _strip_raw_action(effective_payload["validation"]),
        "capture": _strip_raw_action(effective_payload["capture"]),
        "dry_run": _strip_raw_action(effective_payload["dry_run"]),
        "audit": effective_payload["audit"],
        "security": {
            "prints_tokens": False,
            "registers_real_handlers": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "grants_permissions": False,
            "adapter_capability_elevated": False,
            "requires_effective_authorization": True,
            "requires_registered_handler": True,
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
        f"dispatch_requested: {str(dispatcher['dispatch_requested']).lower()}",
        f"dispatch_permitted: {str(dispatcher['dispatch_permitted']).lower()}",
        f"dispatch_enabled: {str(dispatcher['dispatch_enabled']).lower()}",
        f"adapter_dispatched: {str(dispatcher['adapter_dispatched']).lower()}",
        f"adapter_executed: {str(dispatcher['adapter_executed']).lower()}",
        f"handler_registered: {str(dispatcher['handler_registered']).lower()}",
        f"operation_scope: {dispatcher['operation_scope']}",
        f"adapter_id: {dispatcher.get('adapter_id') or 'none'}",
        f"requested_capability: {dispatcher['requested_capability']}",
        f"effective_authorization: {str(dispatcher['effective_authorization']).lower()}",
        f"adapter_capability_authorized: {str(dispatcher['adapter_capability_authorized']).lower()}",
        f"result: {payload['result']}",
        f"reason: {dispatcher['reason']}",
        "grants_permissions: false",
    ]
    return "\n".join(lines)

