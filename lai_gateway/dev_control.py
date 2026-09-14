from typing import Any

from . import __version__
from .harness_client import READ_ONLY_RUN_MODES, WORK_RUN_MODES


def collect_dev_control_policy() -> dict[str, Any]:
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "dev-control-policy",
        "overall": "ready",
        "starts_server": False,
        "modifies_files": False,
        "executes_work": False,
        "policy_only": True,
        "surfaces": {
            "conversation": {
                "purpose": "general chat",
                "creates_harness_run": False,
                "allowed_modes": [],
                "writes_source_checkout": False,
            },
            "plan": {
                "route": "/v1/harness/runs",
                "purpose": "read-only assisted planning",
                "allowed_modes": sorted(READ_ONLY_RUN_MODES),
                "writes_source_checkout": False,
            },
            "workbench_work": {
                "route": "/v1/local-chat/runs",
                "purpose": "sandboxed work run negotiated with Harness",
                "allowed_modes": sorted(WORK_RUN_MODES),
                "requires_workspace_id": True,
                "requires_model_id": True,
                "requires_loopback_local_chat": True,
                "writes_source_checkout": False,
                "promotion_required_for_source_change": True,
            },
            "promotion": {
                "route": "/v1/local-chat/runs/{control_run_id}/promotion",
                "requires_review": True,
                "requires_workspace_id": True,
                "requires_control_run_id": True,
                "requires_patch_sha256": True,
                "human_approval_required": True,
            },
        },
        "forbidden": [
            "write_mode_via_generic_harness_runs",
            "source_checkout_write_without_review",
            "promotion_without_patch_sha256",
            "skill_or_channel_permission_elevation",
        ],
        "security": {
            "prints_tokens": False,
            "grants_permissions": False,
            "channels_elevate_permissions": False,
            "skills_elevate_permissions": False,
            "adapters_elevate_permissions": False,
        },
    }


def render_dev_control_policy(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway dev-control-policy: {payload['overall']}",
        f"version: {payload['version']}",
        "policy_only: true",
        "grants_permissions: false",
    ]
    surfaces = payload.get("surfaces", {})
    for name, surface in surfaces.items():
        modes = ", ".join(surface.get("allowed_modes", [])) or "none"
        route = surface.get("route", "none")
        lines.append(f"- {name}: route={route} modes={modes} writes_source_checkout={surface.get('writes_source_checkout', False)}")
    if payload.get("forbidden"):
        lines.append("forbidden:")
        lines.extend(f"  - {item}" for item in payload["forbidden"])
    return "\n".join(lines)
