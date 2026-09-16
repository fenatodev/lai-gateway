import hashlib
import re
from typing import Any

_LOCAL_MCP_ADAPTER_VERSION = "local-mcp-adapter/v1"
_LOCAL_MCP_ID = "mcp_local"
_LOCAL_MCP_CAPABILITY = "mcp.local_echo_digest"
_ALLOWED_CAPABILITIES = {_LOCAL_MCP_CAPABILITY}
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_PAYLOAD_SHA256 = hashlib.sha256(b"lai-mcp-local-healthcheck").hexdigest()


def can_handle_local_mcp(adapter_id: str | None, capability: str | None) -> bool:
    return adapter_id == _LOCAL_MCP_ID and capability in _ALLOWED_CAPABILITIES


def default_payload_sha256() -> str:
    return _DEFAULT_PAYLOAD_SHA256


def _safe_payload_sha256(parameters: dict[str, str] | None) -> str | None:
    value = str((parameters or {}).get("payload_sha256") or _DEFAULT_PAYLOAD_SHA256).strip().lower()
    if not _HEX_SHA256.fullmatch(value):
        return None
    return value


def _action_sha256(action: str | None) -> str:
    return hashlib.sha256((action or "").encode("utf-8")).hexdigest()


def execute_local_mcp_adapter(
    *,
    requested_capability: str,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    if requested_capability not in _ALLOWED_CAPABILITIES:
        return {
            "status": "blocked",
            "reason": "local MCP capability is not allowlisted",
            "adapter_id": _LOCAL_MCP_ID,
            "requested_capability": requested_capability,
            "adapter_version": _LOCAL_MCP_ADAPTER_VERSION,
            "executed": False,
        }
    payload_sha256 = _safe_payload_sha256(parameters)
    if payload_sha256 is None:
        return {
            "status": "blocked",
            "reason": "payload_sha256 must be a hex sha256 digest; raw payload is not accepted",
            "adapter_id": _LOCAL_MCP_ID,
            "requested_capability": requested_capability,
            "adapter_version": _LOCAL_MCP_ADAPTER_VERSION,
            "executed": False,
            "raw_payload_accepted": False,
        }
    return {
        "status": "ok",
        "reason": "allowlisted local MCP-shaped tool executed inside the gateway process",
        "adapter_id": _LOCAL_MCP_ID,
        "requested_capability": requested_capability,
        "adapter_version": _LOCAL_MCP_ADAPTER_VERSION,
        "tool_name": "local_echo_digest",
        "executed": True,
        "result_type": "mcp_local_tool",
        "payload_sha256": payload_sha256,
        "action_sha256": _action_sha256(action),
        "raw_payload_accepted": False,
        "raw_payload_exposed": False,
        "parameter_values_exposed": False,
        "local_only": True,
        "network_access": False,
        "credential_access": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "shell_execution": False,
        "external_side_effects": False,
        "grants_permission": False,
        "calls_upstream_mcp": False,
        "broad_mcp_tool_execution": False,
    }
