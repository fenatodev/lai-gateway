from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import __version__
from .model import collect_model_plan, collect_model_runtime, collect_model_status

_MODEL_RUNTIME_PROFILE_VERSION = "model-runtime-profile/v1"


def _digest(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _safe_status(value: Any) -> str:
    text = str(value or "unknown").strip().lower().replace(" ", "-")
    return text or "unknown"


def _configured(model_config: dict[str, Any]) -> bool:
    return bool(model_config.get("configured") and model_config.get("base_url") and model_config.get("model"))


def _config_error_is_blocking(runtime: dict[str, Any]) -> bool:
    message = str(runtime.get("config_error") or "").lower()
    if not message:
        return False
    if "file not found" in message:
        return False
    if "requires a model name" in message or "requires an api_key_file" in message:
        return False
    return True


def _runtime_profile_overall(runtime: dict[str, Any], status: dict[str, Any]) -> str:
    model_config = status.get("model_config") or {}
    if runtime.get("overall") == "blocked" or status.get("overall") == "blocked":
        return "blocked"
    if _config_error_is_blocking(runtime):
        return "blocked"
    if not _configured(model_config):
        return "needs_config"
    if runtime.get("ready_for_chat") or status.get("overall") == "ready":
        return "ready"
    return "needs_probe"


def _next_steps(runtime: dict[str, Any], plan: dict[str, Any] | None) -> list[str]:
    steps = list(runtime.get("next_steps") or [])
    if plan:
        for item in plan.get("warnings") or []:
            if item not in steps:
                steps.append(str(item))
        for item in plan.get("plan") or []:
            title = str(item.get("title") or "").strip()
            detail = str(item.get("detail") or "").strip()
            line = f"{title}: {detail}" if title and detail else title or detail
            if line and line not in steps:
                steps.append(line)
    return steps[:8]


def collect_model_runtime_profile(
    *,
    config_path: str | Path | None = None,
    include_plan: bool = True,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a UX-oriented local model runtime profile without starting or probing runtime."""
    scoped_env = dict(env or {})
    if config_path is not None:
        scoped_env["LAI_GATEWAY_MODEL_CONFIG_FILE"] = str(Path(config_path).expanduser())
    runtime = collect_model_runtime(runtime_action="show", config_path=config_path, probe_openai=False, env=scoped_env)
    status = runtime.get("status") or collect_model_status(env=scoped_env, probe_openai=False)
    model_config = status.get("model_config") or {}
    plan = collect_model_plan(env=scoped_env) if include_plan else None
    overall = _runtime_profile_overall(runtime, status)
    profile_id = "mrp-" + _digest((
        _MODEL_RUNTIME_PROFILE_VERSION,
        overall,
        str(model_config.get("provider") or ""),
        str(model_config.get("base_url") or ""),
        str(model_config.get("model") or ""),
    ))
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "model-runtime-profile",
        "schema_version": _MODEL_RUNTIME_PROFILE_VERSION,
        "overall": overall,
        "reason": _reason(overall, runtime, status),
        "profile": {
            "profile_id": profile_id,
            "status": overall,
            "provider": model_config.get("provider") or "openai-compatible",
            "base_url_configured": bool(model_config.get("base_url")),
            "model_configured": bool(model_config.get("model")),
            "model": model_config.get("model"),
            "api_key_configured": bool(model_config.get("api_key_configured")),
            "api_key_file_configured": bool(model_config.get("api_key_file")),
            "api_key_value_printed": False,
            "config_file_configured": bool(runtime.get("configured")),
            "ready_for_chat": bool(runtime.get("ready_for_chat")),
            "runtime_overall": _safe_status(runtime.get("overall")),
            "status_overall": _safe_status(status.get("overall")),
            "fallback_mode": "explicit-local-fallback" if overall != "ready" else "none",
            "cloud_fallback": False,
            "diagnostic_probe_required": overall == "needs_probe",
            "diagnostic_probe_performed": False,
            "starts_runtime": False,
            "downloads_models": False,
        },
        "diagnostics": {
            "runtime": {
                "overall": runtime.get("overall"),
                "configured": bool(runtime.get("configured")),
                "ready_for_chat": bool(runtime.get("ready_for_chat")),
                "config_error_present": bool(runtime.get("config_error")),
            },
            "status": {
                "overall": status.get("overall"),
                "runtime_tools_available": [
                    key for key, value in (status.get("commands") or {}).items() if bool(value.get("available"))
                ],
                "windows_runtime_tools_available": [
                    key for key, value in (status.get("windows_commands") or {}).items() if bool(value.get("available"))
                ],
                "local_openai_probe_performed": False,
            },
            "plan": {
                "included": bool(plan),
                "overall": plan.get("overall") if plan else None,
                "backend": plan.get("backend") if plan else None,
            },
        },
        "next_steps": _next_steps(runtime, plan),
        "data_touched": {
            "model_runtime_config_read": bool(runtime.get("configured")),
            "hardware_snapshot_read": True,
            "runtime_command_presence_checked": True,
            "config_path_value_returned": False,
            "api_key_value_read": False,
            "api_key_value_printed": False,
            "filesystem_write": False,
            "network_access": False,
            "local_openai_probe": False,
            "downloads_models": False,
            "starts_runtime": False,
        },
        "security": {
            "read_only": True,
            "prints_tokens": False,
            "stores_api_key_value": False,
            "api_key_value_printed": False,
            "starts_server": False,
            "starts_runtime": False,
            "modifies_files": False,
            "filesystem_write": False,
            "downloads_models": False,
            "executes_tools": False,
            "calls_harness": False,
            "dispatches_adapter": False,
            "issues_grants": False,
            "consumes_grants": False,
            "effective_authorization": False,
            "cloud_fallback": False,
            "network_access": False,
            "local_openai_probe": False,
            "external_side_effects": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "browser_authenticated": False,
            "n8n_real_workflow": False,
            "mcp_broad": False,
            "scans_home": False,
            "recursive_scan": False,
            "implicit_ingestion": False,
        },
    }


def _reason(overall: str, runtime: dict[str, Any], status: dict[str, Any]) -> str:
    if overall == "ready":
        return "local model runtime profile is ready without starting or probing runtime"
    if overall == "needs_config":
        return "local model runtime profile needs explicit local runtime configuration"
    if overall == "needs_probe":
        return "local runtime is configured but readiness still needs an explicit local diagnostic probe"
    return str(runtime.get("config_error") or status.get("recommendation") or "model runtime profile is blocked")[:240]


def render_model_runtime_profile(payload: dict[str, Any]) -> str:
    profile = payload.get("profile") or {}
    lines = [
        f"lai-gateway model-runtime-profile: {payload.get('overall', 'unknown')}",
        f"schema: {payload.get('schema_version', _MODEL_RUNTIME_PROFILE_VERSION)}",
        f"profile_id: {profile.get('profile_id') or 'none'}",
        f"provider: {profile.get('provider') or 'openai-compatible'}",
        f"model_configured: {str(bool(profile.get('model_configured'))).lower()}",
        f"ready_for_chat: {str(bool(profile.get('ready_for_chat'))).lower()}",
        f"fallback_mode: {profile.get('fallback_mode') or 'unknown'}",
        "read_only: true",
        "starts_runtime: false",
        "downloads_models: false",
        "cloud_fallback: false",
        "network_access: false",
        "local_openai_probe: false",
        "filesystem_write: false",
        "executes_tools: false",
        "calls_harness: false",
        "issues_grants: false",
        "consumes_grants: false",
        "dispatches_adapter: false",
        f"reason: {payload.get('reason', '')}",
    ]
    steps = payload.get("next_steps") or []
    if steps:
        lines.append("next_steps:")
        lines.extend(f"  {step}" for step in steps[:6])
    return "\n".join(lines)
