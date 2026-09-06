from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .doctor import collect_doctor
from .errors import GatewayError
from .mobile import collect_mobile_status
from .model import collect_model_runs, collect_model_status
from .telegram import collect_telegram_preflight


def collect_ops_status(
    *,
    config: GatewayConfig | None = None,
    mobile_candidate_ip: str | None = None,
    mobile_port: int | None = None,
    telegram_token_file: Path | None = None,
    telegram_chat_id: str | None = None,
    telegram_enable_send: bool | None = None,
) -> dict[str, Any]:
    """Collect one read-only operational snapshot for the local gateway."""
    config_error: str | None = None
    try:
        resolved_config = config or GatewayConfig.from_env()
    except GatewayError as exc:
        resolved_config = None
        config_error = str(exc)

    doctor = collect_doctor(resolved_config)
    port = mobile_port or (resolved_config.port if resolved_config else 8787)
    bind = resolved_config.bind if resolved_config else "127.0.0.1"
    mobile = collect_mobile_status(
        port=port,
        bind=bind,
        candidate_ip=mobile_candidate_ip,
        access_token_path=resolved_config.access_token_file if resolved_config else None,
        pair_token_path=resolved_config.pair_token_file if resolved_config else None,
    )
    telegram = collect_telegram_preflight(
        token_file=telegram_token_file,
        chat_id=telegram_chat_id,
        enable_send=telegram_enable_send,
    )
    model = collect_model_status()
    model_runs = collect_model_runs(limit=5)
    overall = _ops_overall(doctor=doctor, mobile=mobile, telegram=telegram)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "ops-status",
        "overall": overall,
        "config_error": config_error,
        "starts_server": False,
        "modifies_files": False,
        "network_calls": {
            "harness_local": doctor.get("overall") != "blocked" or _has_check(doctor, "harness_status"),
            "telegram": False,
            "windows_network_mutation": False,
        },
        "doctor": doctor,
        "mobile": mobile,
        "telegram": telegram,
        "model": model,
        "model_runs": model_runs,
        "next_steps": _ops_next_steps(doctor=doctor, mobile=mobile, telegram=telegram, model_runs=model_runs),
        "security": {
            "prints_tokens": False,
            "starts_server": False,
            "modifies_files": False,
            "telegram_network_call": False,
            "harness_control_token_browser_exposure": False,
        },
    }


def render_ops_status(payload: dict[str, Any]) -> str:
    doctor = payload["doctor"]
    mobile = payload["mobile"]
    telegram = payload["telegram"]
    model = payload.get("model", {})
    model_runs = payload.get("model_runs", {})
    lines = [
        f"lai-gateway ops-status: {payload['overall']}",
        f"version: {payload['version']}",
        "starts_server: false",
        "modifies_files: false",
        f"doctor: {doctor['overall']}",
        f"harness_model: {_harness_model_status(doctor)}",
        f"mobile: {mobile['overall']}",
        f"telegram: {telegram['overall']}",
        f"gateway_model_probe: {model.get('overall', 'unknown')}",
        f"model_runs: {model_runs.get('count', 0)}",
    ]
    config = doctor.get("config")
    if isinstance(config, dict):
        lines.append(f"gateway_url: http://{config['bind']}:{config['port']}/")
        lines.append(f"harness_url: {config['harness_url']}")
        lines.append(f"access_mode: {config['access_mode']}")
    listener = mobile.get("listener", {})
    if listener.get("target"):
        lines.append(f"mobile_target: {listener['target']}")
        lines.append(f"mobile_listener: {'active' if listener.get('active') else 'none'}")
    scan_url = mobile.get("mobile_access", {}).get("recommended_url")
    if scan_url:
        lines.append(f"scan_url: {scan_url}")
    token_file = telegram.get("token_file", {})
    lines.append(f"telegram_token: {token_file.get('status', 'unknown')}")
    lines.append(f"telegram_chat: {'ready' if telegram.get('chat_id_configured') else 'missing'}")
    lines.append(f"telegram_send_enabled: {str(telegram.get('send_enabled', False)).lower()}")
    if payload["next_steps"]:
        lines.append("next_steps:")
        lines.extend(f"  {step}" for step in payload["next_steps"])
    return "\n".join(lines)


def _harness_model_status(doctor: dict[str, Any]) -> str:
    for check in doctor.get("checks", []):
        if check.get("name") == "harness_readiness":
            return "ready" if check.get("status") == "ok" else str(check.get("status") or "unknown")
    return "unknown"


def _ops_overall(*, doctor: dict[str, Any], mobile: dict[str, Any], telegram: dict[str, Any]) -> str:
    if doctor.get("overall") == "blocked" or mobile.get("overall") == "blocked":
        return "blocked"
    if doctor.get("overall") == "warn" or mobile.get("overall") != "ready" or telegram.get("overall") != "ready":
        return "warn"
    return "ready"


def _ops_next_steps(*, doctor: dict[str, Any], mobile: dict[str, Any], telegram: dict[str, Any], model_runs: dict[str, Any] | None = None) -> list[str]:
    steps: list[str] = []
    for check in doctor.get("checks", []):
        if check.get("status") == "fail":
            steps.append(f"Fix doctor check `{check.get('name')}`: {check.get('detail')}")
    steps.extend(str(step) for step in mobile.get("next_steps", []))
    if (model_runs or {}).get("count", 0) == 0:
        steps.append("Run local model evaluation metrics: lai-gateway-model --eval --record")
    if telegram.get("overall") != "ready":
        if not telegram.get("token_file", {}).get("ok"):
            steps.append("Configure Telegram token: lai-gateway telegram token-set --force")
        if not telegram.get("chat_id_configured"):
            steps.append("Discover and persist Telegram chat: LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE=1 lai-gateway telegram discover-chat")
        if telegram.get("token_file", {}).get("ok") and telegram.get("chat_id_configured") and not telegram.get("send_enabled"):
            steps.append("Enable Telegram send for this shell: export LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1")
    return _dedupe(steps)


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _has_check(payload: dict[str, Any], name: str) -> bool:
    return any(check.get("name") == name for check in payload.get("checks", []))
