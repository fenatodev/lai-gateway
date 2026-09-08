from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .ops import collect_ops_status


def collect_health_report(
    *,
    config: GatewayConfig | None = None,
    mobile_candidate_ip: str | None = None,
    mobile_port: int | None = None,
    telegram_token_file: Path | None = None,
    telegram_chat_id: str | None = None,
    telegram_enable_send: bool | None = None,
) -> dict[str, Any]:
    """Collect a compact, secret-free daily health report without mutation."""
    ops = collect_ops_status(
        config=config,
        mobile_candidate_ip=mobile_candidate_ip,
        mobile_port=mobile_port,
        telegram_token_file=telegram_token_file,
        telegram_chat_id=telegram_chat_id,
        telegram_enable_send=telegram_enable_send,
    )
    doctor = ops.get("doctor") or {}
    mobile = ops.get("mobile") or {}
    telegram = ops.get("telegram") or {}
    model = ops.get("model") or {}
    model_runs = ops.get("model_runs") or {}
    mcp = ops.get("mcp_broker") or {}
    mobile_listener = mobile.get("listener") if isinstance(mobile.get("listener"), dict) else {}
    access = mobile.get("mobile_access") if isinstance(mobile.get("mobile_access"), dict) else {}

    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "health-report",
        "overall": ops.get("overall", "unknown"),
        "starts_server": False,
        "modifies_files": False,
        "network_calls": dict(ops.get("network_calls") or {}),
        "checks": {
            "doctor": doctor.get("overall", "unknown"),
            "harness_model": _harness_model_status(doctor),
            "mobile": mobile.get("overall", "unknown"),
            "telegram": telegram.get("overall", "unknown"),
            "gateway_model_probe": model.get("overall", "unknown"),
            "model_runs": model_runs.get("count", 0),
            "mcp_broker": mcp.get("overall", "unknown"),
        },
        "mcp": {
            "server_count": mcp.get("server_count", 0),
            "execution_enabled": bool(mcp.get("execution_enabled", False)),
        },
        "mobile": {
            "listener_active": bool(mobile_listener.get("active", False)),
            "target_present": bool(mobile_listener.get("target")),
            "recommended_url_present": bool(access.get("recommended_url")),
        },
        "telegram": {
            "send_enabled": bool(telegram.get("send_enabled", False)),
            "chat_configured": bool(telegram.get("chat_id_configured", False)),
            "token_status": (telegram.get("token_file") or {}).get("status", "unknown"),
        },
        "security": {
            "prints_tokens": False,
            "prints_pairing_secret": False,
            "prints_chat_reference": False,
            "prints_harness_token": False,
            "starts_server": False,
            "modifies_files": False,
            "mcp_tool_execution": bool(mcp.get("execution_enabled", False)),
        },
        "next_steps": list(ops.get("next_steps") or []),
    }


def render_health_report(payload: dict[str, Any]) -> str:
    checks = payload.get("checks") or {}
    mcp = payload.get("mcp") or {}
    mobile = payload.get("mobile") or {}
    telegram = payload.get("telegram") or {}
    network = payload.get("network_calls") or {}
    security = payload.get("security") or {}

    lines = [
        f"lai-gateway health-report: {payload.get('overall', 'unknown')}",
        f"version: {payload.get('version', __version__)}",
        "scope: read-only daily operations snapshot",
        f"doctor: {checks.get('doctor', 'unknown')}",
        f"harness_model: {checks.get('harness_model', 'unknown')}",
        f"mobile: {checks.get('mobile', 'unknown')} listener_active={str(mobile.get('listener_active', False)).lower()}",
        f"telegram: {checks.get('telegram', 'unknown')} send_enabled={str(telegram.get('send_enabled', False)).lower()}",
        f"model: {checks.get('gateway_model_probe', 'unknown')} runs={checks.get('model_runs', 0)}",
        f"mcp_broker: {checks.get('mcp_broker', 'unknown')} servers={mcp.get('server_count', 0)} execution_enabled={str(mcp.get('execution_enabled', False)).lower()}",
        f"network_calls: harness_local={str(network.get('harness_local', False)).lower()} model_local={str(network.get('model_local', False)).lower()} telegram=false",
        f"security: tokens={str(security.get('prints_tokens', False)).lower()} pairing_secret={str(security.get('prints_pairing_secret', False)).lower()} writes={str(security.get('modifies_files', False)).lower()} starts_server={str(security.get('starts_server', False)).lower()}",
    ]
    steps = payload.get("next_steps") or []
    if steps:
        lines.append("next_steps:")
        lines.extend(f"  {step}" for step in steps[:6])
    return "\n".join(lines)


def _harness_model_status(doctor: dict[str, Any]) -> str:
    for check in doctor.get("checks", []):
        if isinstance(check, dict) and check.get("name") == "harness_readiness":
            return "ready" if check.get("status") == "ok" else str(check.get("status") or "unknown")
    return "unknown"
