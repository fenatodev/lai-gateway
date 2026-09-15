import hashlib
from typing import Any

_LOCAL_STATUS_ADAPTER_VERSION = "local-status-adapter/v1"
_LOCAL_STATUS_ID = "local_status"
_ALLOWED_CAPABILITIES = {"local_status.status", "local_status.echo"}


def can_handle_local_status(adapter_id: str | None, capability: str | None) -> bool:
    return adapter_id == _LOCAL_STATUS_ID and capability in _ALLOWED_CAPABILITIES


def _digest(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def execute_local_status_adapter(
    *,
    requested_capability: str,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    if requested_capability not in _ALLOWED_CAPABILITIES:
        return {
            "status": "blocked",
            "reason": "local status capability is not allowlisted",
            "adapter_id": _LOCAL_STATUS_ID,
            "requested_capability": requested_capability,
            "adapter_version": _LOCAL_STATUS_ADAPTER_VERSION,
            "executed": False,
        }
    safe_parameters = parameters or {}
    keys = sorted(str(key)[:48] for key in safe_parameters.keys())[:8]
    return {
        "status": "ok",
        "reason": "local status adapter executed inside allowlisted in-process handler",
        "adapter_id": _LOCAL_STATUS_ID,
        "requested_capability": requested_capability,
        "adapter_version": _LOCAL_STATUS_ADAPTER_VERSION,
        "executed": True,
        "result_type": "local_status",
        "parameter_count": len(safe_parameters),
        "parameter_keys": keys,
        "action_sha256": _digest(action),
        "parameter_values_exposed": False,
        "raw_action_exposed": False,
        "local_only": True,
        "network_access": False,
        "credential_access": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "shell_execution": False,
        "external_side_effects": False,
        "grants_permission": False,
    }
