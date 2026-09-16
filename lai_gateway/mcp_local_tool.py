import re
from pathlib import Path
from typing import Any

from . import __version__
from .authorization_recovery import collect_authorization_recovery
from .effective_authorization import collect_effective_authorization
from .local_mcp_adapter import default_payload_sha256, execute_local_mcp_adapter

_SCHEMA_VERSION = "mcp-local-tool/v1"
_ADAPTER_ID = "mcp_local"
_CAPABILITY = "mcp.local_echo_digest"
_SCOPE = "mcp-local-safe-tool"
_ACTION = "mcp.local_echo_digest"
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _payload_sha256(value: str | None) -> tuple[str, bool]:
    if value is None or not str(value).strip():
        return default_payload_sha256(), True
    digest = str(value).strip().lower()
    if not _HEX_SHA256.fullmatch(digest):
        return default_payload_sha256(), False
    return digest, True


def _request_kwargs(payload_sha256: str, *, channel: str = "gateway") -> dict[str, Any]:
    return {
        "adapter_id": _ADAPTER_ID,
        "requested_capability": _CAPABILITY,
        "actor": "user",
        "channel": channel,
        "domain": "tools",
        "action": _ACTION,
        "parameters": {"payload_sha256": payload_sha256},
        "approval_intent": True,
        "approved_by": "user",
        "operation_scope": _SCOPE,
    }


def collect_mcp_local_tool(
    *,
    mcp_action: str = "plan",
    authorization_grant_id: str | None = None,
    authorization_dir: str | Path | None = None,
    scope_root: Path | None = None,
    payload_sha256: str | None = None,
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
    action = (mcp_action or "plan").strip().lower()
    digest, digest_valid = _payload_sha256(payload_sha256)
    if not digest_valid:
        return {
            "product": "lai-gateway",
            "version": __version__,
            "operation": "mcp-local-tool",
            "schema_version": _SCHEMA_VERSION,
            "overall": "blocked",
            "mcp_action": action,
            "status": "blocked",
            "reason": "payload_sha256 must be a hex sha256 digest; raw payload is not accepted",
            "adapter_id": _ADAPTER_ID,
            "operation_scope": _SCOPE,
            "requested_capability": _CAPABILITY,
            "authorization_grant_id": authorization_grant_id,
            "payload_sha256": digest,
            "effective": None,
            "authorization_issue": None,
            "authorization_consume": None,
            "handler_result": None,
            "local_tool_executed": False,
            "executes_upstream_mcp_tools": False,
            "broad_mcp_tool_execution": False,
            "external_side_effects": False,
            "security": {
                "prints_tokens": False,
                "accepts_raw_payload": False,
                "stores_raw_payload": False,
                "exposes_raw_payload": False,
                "requires_exact_capability": True,
                "requires_minimal_scope": True,
                "requires_verified_identity": True,
                "requires_single_use_authorization": True,
                "blocks_replay": True,
                "local_only": True,
                "calls_upstream_mcp": False,
                "executes_upstream_mcp_tools": False,
                "broad_mcp_tool_execution": False,
                "network_access": False,
                "credential_access": False,
                "filesystem_write": False,
                "authorization_state_write": False,
                "shell_execution": False,
                "external_side_effects": False,
                "grants_permissions": False,
            },
        }
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
    reason = "local MCP safe tool planned; no grant consumed and no tool executed"
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
    elif action == "run":
        if not authorization_grant_id:
            status = "blocked"
            overall = "blocked"
            reason = "authorization_grant_id is required before running the local MCP tool"
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
                handler_result = execute_local_mcp_adapter(
                    requested_capability=_CAPABILITY,
                    action=_ACTION,
                    parameters={"payload_sha256": digest},
                )
                status = "executed_local_mcp_tool" if handler_result.get("status") == "ok" else "blocked"
                overall = "ready" if handler_result.get("status") == "ok" else "blocked"
                reason = str(handler_result.get("reason") or reason)
            else:
                overall = "blocked"
    elif action != "plan":
        status = "blocked"
        overall = "blocked"
        reason = "unsupported MCP local tool action"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "mcp-local-tool",
        "schema_version": _SCHEMA_VERSION,
        "overall": overall,
        "mcp_action": action,
        "status": status,
        "reason": reason,
        "adapter_id": _ADAPTER_ID,
        "operation_scope": _SCOPE,
        "requested_capability": _CAPABILITY,
        "authorization_grant_id": authorization_grant_id,
        "payload_sha256": digest,
        "effective": effective_payload["effective"],
        "authorization_issue": issued,
        "authorization_consume": consumed,
        "handler_result": handler_result,
        "local_tool_executed": bool(handler_result and handler_result.get("executed")),
        "executes_upstream_mcp_tools": False,
        "broad_mcp_tool_execution": False,
        "external_side_effects": False,
        "security": {
            "prints_tokens": False,
            "accepts_raw_payload": False,
            "stores_raw_payload": False,
            "exposes_raw_payload": False,
            "requires_exact_capability": True,
            "requires_minimal_scope": True,
            "requires_verified_identity": True,
            "requires_single_use_authorization": True,
            "blocks_replay": True,
            "local_only": True,
            "calls_upstream_mcp": False,
            "executes_upstream_mcp_tools": False,
            "broad_mcp_tool_execution": False,
            "network_access": False,
            "credential_access": False,
            "filesystem_write": bool(consumed or issued),
            "authorization_state_write": bool(consumed or issued),
            "shell_execution": False,
            "external_side_effects": False,
            "grants_permissions": False,
        },
    }


def render_mcp_local_tool(payload: dict[str, Any]) -> str:
    return "\n".join([
        f"lai-gateway mcp-local-tool: {payload['overall']}",
        f"version: {payload['version']}",
        f"schema_version: {payload['schema_version']}",
        f"mcp_action: {payload['mcp_action']}",
        f"status: {payload['status']}",
        f"adapter_id: {payload['adapter_id']}",
        f"operation_scope: {payload['operation_scope']}",
        f"requested_capability: {payload['requested_capability']}",
        f"authorization_grant_id: {payload.get('authorization_grant_id') or 'none'}",
        f"payload_sha256: {payload['payload_sha256']}",
        f"local_tool_executed: {str(payload['local_tool_executed']).lower()}",
        f"calls_upstream_mcp: {str(payload['security']['calls_upstream_mcp']).lower()}",
        f"broad_mcp_tool_execution: {str(payload['broad_mcp_tool_execution']).lower()}",
        f"external_side_effects: {str(payload['external_side_effects']).lower()}",
        f"reason: {payload['reason']}",
        "grants_permissions: false",
    ])
