import hashlib
import re
from typing import Any

_LOCAL_N8N_ADAPTER_VERSION = "local-n8n-adapter/v1"
_N8N_ADAPTER_ID = "n8n"
_N8N_PLAN_CAPABILITY = "n8n.local_plan_digest"
_ALLOWED_CAPABILITIES = {_N8N_PLAN_CAPABILITY}
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_WORKFLOW_SHA256 = hashlib.sha256(b"lai-n8n-local-plan-healthcheck").hexdigest()


def can_handle_local_n8n(adapter_id: str | None, capability: str | None) -> bool:
    return adapter_id == _N8N_ADAPTER_ID and capability in _ALLOWED_CAPABILITIES


def default_workflow_sha256() -> str:
    return _DEFAULT_WORKFLOW_SHA256


def _safe_workflow_sha256(parameters: dict[str, str] | None) -> str | None:
    value = str((parameters or {}).get("workflow_sha256") or _DEFAULT_WORKFLOW_SHA256).strip().lower()
    if not _HEX_SHA256.fullmatch(value):
        return None
    return value


def _action_sha256(action: str | None) -> str:
    return hashlib.sha256((action or "").encode("utf-8")).hexdigest()


def inspect_local_n8n_plan_adapter(
    *,
    requested_capability: str,
    action: str | None = None,
    parameters: dict[str, str] | None = None,
) -> dict[str, Any]:
    if requested_capability not in _ALLOWED_CAPABILITIES:
        return {
            "status": "blocked",
            "reason": "local n8n capability is not allowlisted",
            "adapter_id": _N8N_ADAPTER_ID,
            "requested_capability": requested_capability,
            "adapter_version": _LOCAL_N8N_ADAPTER_VERSION,
            "plan_inspected": False,
        }
    workflow_sha256 = _safe_workflow_sha256(parameters)
    if workflow_sha256 is None:
        return {
            "status": "blocked",
            "reason": "workflow_sha256 must be a hex sha256 digest; raw workflow JSON is not accepted",
            "adapter_id": _N8N_ADAPTER_ID,
            "requested_capability": requested_capability,
            "adapter_version": _LOCAL_N8N_ADAPTER_VERSION,
            "plan_inspected": False,
            "raw_workflow_accepted": False,
        }
    return {
        "status": "ok",
        "reason": "allowlisted local n8n plan digest inspected inside the gateway process",
        "adapter_id": _N8N_ADAPTER_ID,
        "requested_capability": requested_capability,
        "adapter_version": _LOCAL_N8N_ADAPTER_VERSION,
        "result_type": "n8n_local_plan",
        "plan_inspected": True,
        "workflow_sha256": workflow_sha256,
        "action_sha256": _action_sha256(action),
        "raw_workflow_accepted": False,
        "raw_workflow_exposed": False,
        "workflow_execution": False,
        "workflow_activation": False,
        "webhook_called": False,
        "calls_n8n_instance": False,
        "network_access": False,
        "credential_access": False,
        "filesystem_read": False,
        "filesystem_write": False,
        "shell_execution": False,
        "external_side_effects": False,
        "grants_permission": False,
    }
