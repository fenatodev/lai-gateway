from __future__ import annotations

from typing import Any

from . import __version__
from .adapter_dispatcher import collect_adapter_dispatcher_interface
from .authorization_record import collect_authorization_record
from .authorization_validation import collect_authorization_validation_gate
from .effective_authorization import collect_effective_authorization
from .permission_decision import collect_permission_decision

_PERMISSION_UX_VERSION = "permission-ux/v1"


def _state_for_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"allow", "ready", "not_required", "effective_for_dry_run_safe_operation", "effective_for_local_status_read", "effective_for_local_mcp_safe_tool", "effective_for_n8n_local_plan", "planned_local_handler"}:
        return "ready"
    if normalized in {"deny", "blocked", "expired", "missing", "rejected"}:
        return "danger"
    return "warn"


def _stage(
    *,
    order: int,
    stage_id: str,
    label: str,
    status: str,
    summary: str,
    authority: str,
    source: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "order": order,
        "stage_id": stage_id,
        "label": label,
        "status": status,
        "state": _state_for_status(status),
        "summary": summary,
        "authority": authority,
        "source": source,
        "grants_permission": False,
        "executes_tools": False,
        "external_side_effects": False,
        **extra,
    }


def _bool_word(value: bool) -> str:
    return "true" if value else "false"


def collect_permission_ux(
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
    authorization_grant_id: str | None = None,
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
    identity_kwargs = {
        "user_id": user_id,
        "client_id": client_id,
        "agent_id": agent_id,
        "service_id": service_id,
        "identity_source": identity_source,
        "expected_identity_binding_id": expected_identity_binding_id,
        "claimed_user_id": claimed_user_id,
        "claimed_client_id": claimed_client_id,
        "claimed_agent_id": claimed_agent_id,
        "claimed_service_id": claimed_service_id,
    }
    common = {
        "adapter_id": adapter_id,
        "requested_capability": requested_capability,
        "actor": actor,
        "channel": channel,
        "domain": domain,
        "action": action,
    }
    param_common = {**common, "parameters": parameters}
    decision_payload = collect_permission_decision(**common, **identity_kwargs)
    record_payload = collect_authorization_record(**common, **identity_kwargs)
    validation_payload = collect_authorization_validation_gate(
        **param_common,
        approval_intent=approval_intent,
        approved_by=approved_by,
    )
    effective_payload = collect_effective_authorization(
        **param_common,
        approval_intent=approval_intent,
        approved_by=approved_by,
        operation_scope=operation_scope,
        **identity_kwargs,
    )
    dispatcher_payload = collect_adapter_dispatcher_interface(
        **param_common,
        approval_intent=approval_intent,
        approved_by=approved_by,
        operation_scope=operation_scope,
        dispatch_requested=False,
        authorization_grant_id=authorization_grant_id,
        **identity_kwargs,
    )

    decision = decision_payload["decision"]
    record = record_payload["record"]
    validation = validation_payload["validation"]
    capture = validation_payload["capture"]
    effective = effective_payload["effective"]
    dispatcher = dispatcher_payload["dispatcher"]
    identity = decision_payload["identity"]
    grant_status = "provided_unverified" if authorization_grant_id else "missing"
    grant_summary = (
        "authorization_grant_id foi informado, mas este painel não lê, emite, consome ou revoga grants"
        if authorization_grant_id
        else "nenhum grant de uso único foi informado; execução real continuaria bloqueada"
    )
    stages = [
        _stage(
            order=1,
            stage_id="intent",
            label="Intenção",
            status="declared" if requested_capability or action else "missing",
            summary="capability e ação normalizadas; texto do pedido não concede permissão",
            authority="descritiva",
            source="request",
            requested_capability=requested_capability or "missing",
            adapter_id=adapter_id or "missing",
        ),
        _stage(
            order=2,
            stage_id="identity",
            label="Identidade",
            status="verified" if identity.get("identity_verified") else "blocked",
            summary="binding usuário/cliente/agente/serviço verificado localmente" if identity.get("identity_verified") else "identidade não confiável bloqueia a cadeia",
            authority="pré-condição",
            source="principal-identity/v1",
            identity_binding_id=identity.get("identity_binding_id"),
        ),
        _stage(
            order=3,
            stage_id="decision",
            label="Decisão",
            status=decision.get("outcome", "unknown"),
            summary=decision.get("reason", "sem razão"),
            authority="classificação policy-only",
            source="permission-decision/v1",
            decision_id=decision.get("decision_id"),
            requires_human_approval=bool(decision.get("requires_human_approval")),
        ),
        _stage(
            order=4,
            stage_id="record",
            label="Registro",
            status=record.get("status", "unknown"),
            summary=record.get("reason", "registro não efetivo"),
            authority="registro não efetivo",
            source="authorization-record/v1",
            authorization_record_id=record.get("record_id"),
            record_persisted=bool(record.get("record_persisted")),
        ),
        _stage(
            order=5,
            stage_id="approval_capture",
            label="Captura/aprovação",
            status=validation.get("status", capture.get("status", "unknown")),
            summary=validation.get("reason", capture.get("reason", "aprovação não capturada")),
            authority="sinal de aprovação, não executor",
            source="authorization-validation-gate/v1",
            approval_intent=bool(capture.get("approval_intent")),
            approval_captured=bool(capture.get("approval_captured")),
            approval_validated=bool(validation.get("approval_validated")),
            validation_id=validation.get("validation_id"),
        ),
        _stage(
            order=6,
            stage_id="effective_authorization",
            label="Autorização efetiva",
            status=effective.get("status", "unknown"),
            summary=effective.get("reason", "sem autorização efetiva"),
            authority="escopo estreito",
            source="effective-authorization/v2",
            effective_authorization_id=effective.get("effective_authorization_id"),
            effective_authorization=bool(effective.get("effective_authorization")),
            operation_scope=effective.get("operation_scope"),
            authorized_target=effective.get("authorized_target"),
        ),
        _stage(
            order=7,
            stage_id="single_use_grant",
            label="Grant single-use",
            status=grant_status,
            summary=grant_summary,
            authority="necessário para certos dispatches, não verificado aqui",
            source="authorization-recovery/v1",
            authorization_grant_id=authorization_grant_id,
            authorization_consumed=False,
        ),
        _stage(
            order=8,
            stage_id="execution",
            label="Execução",
            status="not_executed" if not dispatcher.get("adapter_executed") else "executed",
            summary=dispatcher.get("reason", "dispatcher não solicitado"),
            authority="nenhum efeito por este endpoint",
            source="adapter-dispatcher/v3",
            dispatch_requested=False,
            dispatch_permitted=bool(dispatcher.get("dispatch_permitted")),
            adapter_dispatched=bool(dispatcher.get("adapter_dispatched")),
            adapter_executed=bool(dispatcher.get("adapter_executed")),
            handler_registered=bool(dispatcher.get("handler_registered")),
        ),
    ]
    effective_authorized = bool(effective.get("effective_authorization"))
    executed = bool(dispatcher.get("adapter_executed"))
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "permission-ux",
        "schema_version": _PERMISSION_UX_VERSION,
        "overall": "ready",
        "summary": (
            f"permission UX: decision={decision.get('outcome', 'unknown')} "
            f"effective={_bool_word(effective_authorized)} grant={grant_status} executed={_bool_word(executed)}"
        ),
        "request": {
            "adapter_id": adapter_id,
            "requested_capability": requested_capability,
            "actor": actor,
            "channel": channel,
            "domain": domain,
            "operation_scope": operation_scope,
            "parameter_count": len(parameters or {}),
        },
        "stages": stages,
        "stage_count": len(stages),
        "decision": {
            "outcome": decision.get("outcome"),
            "reason": decision.get("reason"),
            "decision_id": decision.get("decision_id"),
        },
        "effective": {
            "status": effective.get("status"),
            "effective_authorization": effective_authorized,
            "operation_scope": effective.get("operation_scope"),
            "authorized_resource": effective.get("authorized_resource"),
            "authorized_target": effective.get("authorized_target"),
        },
        "grant": {
            "status": grant_status,
            "authorization_grant_id": authorization_grant_id,
            "checked": False,
            "issued": False,
            "consumed": False,
            "revoked": False,
        },
        "execution": {
            "dispatch_requested": False,
            "dispatch_permitted": bool(dispatcher.get("dispatch_permitted")),
            "adapter_dispatched": bool(dispatcher.get("adapter_dispatched")),
            "adapter_executed": executed,
            "handler_registered": bool(dispatcher.get("handler_registered")),
        },
        "next_steps": [
            "Use este painel para revisar a cadeia antes de emitir grant ou despachar qualquer adapter.",
            "Para execução real, use somente fluxo específico que emite e consome grant single-use no endpoint executor.",
        ],
        "source_payloads": {
            "permission_decision_operation": decision_payload.get("operation"),
            "authorization_record_operation": record_payload.get("operation"),
            "authorization_validation_operation": validation_payload.get("operation"),
            "effective_authorization_operation": effective_payload.get("operation"),
            "adapter_dispatcher_operation": dispatcher_payload.get("operation"),
        },
        "security": {
            "read_only": True,
            "prints_tokens": False,
            "issues_grants": False,
            "consumes_grants": False,
            "revokes_grants": False,
            "checks_grant_store": False,
            "persists_authorization": False,
            "dispatches_adapter": False,
            "executes_tools": False,
            "external_side_effects": False,
            "grants_permissions": False,
            "modifies_files": False,
            "starts_server": False,
            "approval_text_elevates_permissions": False,
            "content_elevates_permissions": False,
        },
    }


def render_permission_ux(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway permission-ux: {payload['overall']}",
        f"version: {payload['version']}",
        f"schema_version: {payload['schema_version']}",
        f"summary: {payload['summary']}",
        "flow:",
    ]
    for stage in payload["stages"]:
        lines.append(
            f"  {stage['order']}. {stage['label']}: {stage['status']} | {stage['authority']} | {stage['summary']}"
        )
    lines.extend([
        f"effective_authorization: {_bool_word(payload['effective']['effective_authorization'])}",
        f"grant_checked: {_bool_word(payload['grant']['checked'])}",
        f"grant_issued: {_bool_word(payload['grant']['issued'])}",
        f"grant_consumed: {_bool_word(payload['grant']['consumed'])}",
        f"adapter_executed: {_bool_word(payload['execution']['adapter_executed'])}",
        "read_only: true",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        "executes_tools: false",
        "external_side_effects: false",
        "grants_permissions: false",
    ])
    return "\n".join(lines)
