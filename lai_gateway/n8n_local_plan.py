import re
from pathlib import Path
from typing import Any

from . import __version__
from .authorization_recovery import collect_authorization_recovery
from .effective_authorization import collect_effective_authorization
from .local_n8n_adapter import default_workflow_sha256, inspect_local_n8n_plan_adapter

_SCHEMA_VERSION = "n8n-local-plan/v1"
_ADAPTER_ID = "n8n"
_CAPABILITY = "n8n.local_plan_digest"
_SCOPE = "n8n-local-plan"
_ACTION = "n8n.local_plan_digest"
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _workflow_sha256(value: str | None) -> tuple[str, bool]:
    if value is None or not str(value).strip():
        return default_workflow_sha256(), True
    digest = str(value).strip().lower()
    if not _HEX_SHA256.fullmatch(digest):
        return default_workflow_sha256(), False
    return digest, True


def _request_kwargs(workflow_sha256: str, *, channel: str = "gateway") -> dict[str, Any]:
    return {
        "adapter_id": _ADAPTER_ID,
        "requested_capability": _CAPABILITY,
        "actor": "user",
        "channel": channel,
        "domain": "automation",
        "action": _ACTION,
        "parameters": {"workflow_sha256": workflow_sha256},
        "approval_intent": True,
        "approved_by": "user",
        "operation_scope": _SCOPE,
    }


def _blocked_invalid_digest(n8n_action: str, authorization_grant_id: str | None, workflow_sha256: str) -> dict[str, Any]:
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "n8n-local-plan",
        "schema_version": _SCHEMA_VERSION,
        "overall": "blocked",
        "n8n_action": n8n_action,
        "status": "blocked",
        "reason": "workflow_sha256 must be a hex sha256 digest; raw workflow JSON is not accepted",
        "adapter_id": _ADAPTER_ID,
        "operation_scope": _SCOPE,
        "requested_capability": _CAPABILITY,
        "authorization_grant_id": authorization_grant_id,
        "workflow_sha256": workflow_sha256,
        "effective": None,
        "authorization_issue": None,
        "authorization_consume": None,
        "handler_result": None,
        "local_plan_inspected": False,
        "workflow_executed": False,
        "workflow_activated": False,
        "webhook_called": False,
        "calls_n8n_instance": False,
        "external_side_effects": False,
        "security": _security(consumed_or_issued=False),
    }


def _security(*, consumed_or_issued: bool) -> dict[str, bool]:
    return {
        "prints_tokens": False,
        "accepts_raw_workflow": False,
        "stores_raw_workflow": False,
        "exposes_raw_workflow": False,
        "requires_exact_capability": True,
        "requires_minimal_scope": True,
        "requires_verified_identity": True,
        "requires_single_use_authorization": True,
        "blocks_replay": True,
        "local_only": True,
        "calls_n8n_instance": False,
        "workflow_execution": False,
        "workflow_activation": False,
        "webhook_called": False,
        "network_access": False,
        "credential_access": False,
        "filesystem_read": False,
        "filesystem_write": consumed_or_issued,
        "authorization_state_write": consumed_or_issued,
        "shell_execution": False,
        "external_side_effects": False,
        "grants_permissions": False,
    }


def collect_n8n_local_plan(
    *,
    n8n_action: str = "plan",
    authorization_grant_id: str | None = None,
    authorization_dir: str | Path | None = None,
    scope_root: Path | None = None,
    workflow_sha256: str | None = None,
    ttl_seconds: int | None = 300,
    channel: str = "gateway",
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
    action = (n8n_action or "plan").strip().lower()
    digest, digest_valid = _workflow_sha256(workflow_sha256)
    if not digest_valid:
        return _blocked_invalid_digest(action, authorization_grant_id, digest)
    request = _request_kwargs(digest, channel=channel)
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
    effective_payload = collect_effective_authorization(**request, **identity_kwargs)
    issued = None
    consumed = None
    handler_result = None
    status = "planned"
    overall = "ready"
    reason = "n8n local plan digest prepared; no workflow created, activated, or executed"
    if action == "issue":
        issued = collect_authorization_recovery(
            recovery_action="issue",
            authorization_dir=authorization_dir,
            scope_root=scope_root,
            ttl_seconds=ttl_seconds,
            **request,
            **identity_kwargs,
        )
        status = str(issued["status"])
        overall = "ready" if status == "issued" else "blocked"
        reason = str(issued["reason"])
        authorization_grant_id = str(issued.get("authorization_grant_id") or authorization_grant_id or "") or None
    elif action == "inspect":
        if not authorization_grant_id:
            status = "blocked"
            overall = "blocked"
            reason = "authorization_grant_id is required before inspecting the n8n local plan"
        else:
            consumed = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=authorization_grant_id,
                authorization_dir=authorization_dir,
                scope_root=scope_root,
                **request,
                **identity_kwargs,
            )
            status = str(consumed["status"])
            reason = str(consumed["reason"])
            if consumed.get("dispatch_allowed"):
                handler_result = inspect_local_n8n_plan_adapter(
                    requested_capability=_CAPABILITY,
                    action=_ACTION,
                    parameters={"workflow_sha256": digest},
                )
                status = "inspected_local_n8n_plan" if handler_result.get("status") == "ok" else "blocked"
                overall = "ready" if handler_result.get("status") == "ok" else "blocked"
                reason = str(handler_result.get("reason") or reason)
            else:
                overall = "blocked"
    elif action != "plan":
        status = "blocked"
        overall = "blocked"
        reason = "unsupported n8n local plan action"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "n8n-local-plan",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "n8n_action": action,
        "status": status,
        "reason": reason,
        "adapter_id": _ADAPTER_ID,
        "operation_scope": _SCOPE,
        "requested_capability": _CAPABILITY,
        "authorization_grant_id": authorization_grant_id,
        "workflow_sha256": digest,
        "effective": effective_payload["effective"],
        "authorization_issue": issued,
        "authorization_consume": consumed,
        "handler_result": handler_result,
        "local_plan_inspected": bool(handler_result and handler_result.get("plan_inspected")),
        "workflow_executed": False,
        "workflow_activated": False,
        "webhook_called": False,
        "calls_n8n_instance": False,
        "external_side_effects": False,
        "security": _security(consumed_or_issued=bool(consumed or issued)),
    }


def render_n8n_local_plan(payload: dict[str, Any]) -> str:
    return "\n".join([
        f"lai-gateway n8n-local-plan: {payload['overall']}",
        f"version: {payload['version']}",
        f"schema_version: {payload['schema_version']}",
        f"n8n_action: {payload['n8n_action']}",
        f"status: {payload['status']}",
        f"adapter_id: {payload['adapter_id']}",
        f"operation_scope: {payload['operation_scope']}",
        f"requested_capability: {payload['requested_capability']}",
        f"authorization_grant_id: {payload.get('authorization_grant_id') or 'none'}",
        f"workflow_sha256: {payload['workflow_sha256']}",
        f"local_plan_inspected: {str(payload['local_plan_inspected']).lower()}",
        f"calls_n8n_instance: {str(payload['calls_n8n_instance']).lower()}",
        f"workflow_executed: {str(payload['workflow_executed']).lower()}",
        f"workflow_activated: {str(payload['workflow_activated']).lower()}",
        f"webhook_called: {str(payload['webhook_called']).lower()}",
        f"external_side_effects: {str(payload['external_side_effects']).lower()}",
        f"reason: {payload['reason']}",
        "grants_permissions: false",
    ])
