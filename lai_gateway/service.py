from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import DEFAULT_PORT, GatewayConfig
from .errors import ConfigError
from .lan import _safe_lan_ip

DEFAULT_SERVICE_NAME = "lai-gateway-mobile.service"


def default_user_unit_path(service_name: str = DEFAULT_SERVICE_NAME) -> Path:
    _validate_service_name(service_name)
    return Path("~/.config/systemd/user").expanduser() / service_name


def collect_service_plan(
    *,
    config: GatewayConfig,
    candidate_ip: str,
    port: int = DEFAULT_PORT,
    service_name: str = DEFAULT_SERVICE_NAME,
    unit_path: Path | None = None,
    python_bin: str | None = None,
    repo_dir: Path | None = None,
    telegram_notify: bool = False,
    telegram_token_file: Path | None = None,
    telegram_chat_id: str | None = None,
) -> dict[str, Any]:
    """Return a token-free systemd user service plan for mobile serving."""
    _validate_service_name(service_name)
    target_ip = _validate_candidate_ip(candidate_ip)
    _validate_port(port)
    unit_target = (unit_path or default_user_unit_path(service_name)).expanduser()
    project_dir = (repo_dir or Path.cwd()).resolve()
    executable = python_bin or sys.executable
    systemd_user = _systemd_user_status()
    unit_text = _render_systemd_unit(
        config=config,
        candidate_ip=target_ip,
        port=port,
        service_name=service_name,
        python_bin=executable,
        repo_dir=project_dir,
        telegram_notify=telegram_notify,
        telegram_token_file=telegram_token_file,
        telegram_chat_id=telegram_chat_id,
    )
    installed = unit_target.exists()
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "service-plan",
        "overall": "ready",
        "service_name": service_name,
        "unit_path": str(unit_target),
        "installed": installed,
        "starts_server": False,
        "modifies_files": False,
        "modifies_systemd": False,
        "systemctl_available": systemd_user["systemctl_available"],
        "systemd_user_available": systemd_user["available"],
        "systemd_user_detail": systemd_user["detail"],
        "candidate_ip": target_ip,
        "port": port,
        "url": f"http://{target_ip}:{port}/",
        "telegram_notify": telegram_notify,
        "unit_text": unit_text,
        "commands": _service_commands(service_name),
        "security": {
            "prints_tokens": False,
            "stores_token_values": False,
            "stores_token_paths_only": True,
            "requires_explicit_install": True,
            "does_not_enable_or_start_service": True,
            "private_bind_required": True,
        },
    }


def install_service_unit(*, force: bool = False, **plan_kwargs: Any) -> dict[str, Any]:
    plan = collect_service_plan(**plan_kwargs)
    path = Path(plan["unit_path"]).expanduser()
    if path.exists() and not force:
        raise ConfigError(f"service unit already exists: {path}; pass --force to overwrite")
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    path.write_text(plan["unit_text"], encoding="utf-8")
    os.chmod(path, 0o644)
    return {
        **plan,
        "operation": "service-install",
        "installed": True,
        "modifies_files": True,
        "modifies_systemd": False,
        "force": force,
    }


def remove_service_unit(*, service_name: str = DEFAULT_SERVICE_NAME, unit_path: Path | None = None) -> dict[str, Any]:
    _validate_service_name(service_name)
    path = (unit_path or default_user_unit_path(service_name)).expanduser()
    removed = False
    try:
        path.unlink()
        removed = True
    except FileNotFoundError:
        removed = False
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "service-remove",
        "overall": "ready",
        "service_name": service_name,
        "unit_path": str(path),
        "removed": removed,
        "starts_server": False,
        "modifies_files": removed,
        "modifies_systemd": False,
        "commands": _service_commands(service_name),
        "security": {
            "prints_tokens": False,
            "requires_manual_daemon_reload": True,
        },
    }


def render_service_plan(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway service-plan: {payload['overall']}",
        f"version: {payload['version']}",
        f"service_name: {payload['service_name']}",
        f"unit_path: {payload['unit_path']}",
        f"installed: {str(payload['installed']).lower()}",
        "starts_server: false",
        "modifies_files: false",
        "modifies_systemd: false",
        f"url: {payload['url']}",
        f"telegram_notify: {str(payload['telegram_notify']).lower()}",
        f"systemctl_available: {str(payload['systemctl_available']).lower()}",
        f"systemd_user_available: {str(payload['systemd_user_available']).lower()}",
        f"systemd_user_detail: {payload['systemd_user_detail']}",
        "commands:",
    ]
    for name, command in payload["commands"].items():
        lines.append(f"  {name}: {command}")
    lines.append("exec_start:")
    lines.append(f"  {_exec_start_from_unit(payload['unit_text'])}")
    lines.append("Run service-install to write the unit file; enabling/starting remains a manual systemctl step.")
    return "\n".join(lines)


def render_service_install(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway service-install: {payload['overall']}",
        f"version: {payload['version']}",
        f"written: {payload['unit_path']}",
        f"service_name: {payload['service_name']}",
        "starts_server: false",
        "modifies_files: true",
        "modifies_systemd: false",
        f"systemd_user_available: {str(payload['systemd_user_available']).lower()}",
        f"systemd_user_detail: {payload['systemd_user_detail']}",
        "next_steps:",
        f"  {payload['commands']['daemon_reload']}",
        f"  {payload['commands']['enable_now']}",
        f"  {payload['commands']['status']}",
        f"  {payload['commands']['logs']}",
    ]
    return "\n".join(lines)


def render_service_remove(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"lai-gateway service-remove: {payload['overall']}",
            f"version: {payload['version']}",
            f"removed: {str(payload['removed']).lower()}",
            f"unit_path: {payload['unit_path']}",
            "next_steps:",
            f"  {payload['commands']['daemon_reload']}",
        ]
    )


def _render_systemd_unit(
    *,
    config: GatewayConfig,
    candidate_ip: str,
    port: int,
    service_name: str,
    python_bin: str,
    repo_dir: Path,
    telegram_notify: bool,
    telegram_token_file: Path | None,
    telegram_chat_id: str | None,
) -> str:
    env = {
        "PYTHONPATH": str(repo_dir),
        "LAI_GATEWAY_PRIVATE_BIND": "1",
        "LAI_GATEWAY_HARNESS_URL": config.harness_url,
        "LAI_GATEWAY_TOKEN_FILE": str(config.token_file),
        "LAI_GATEWAY_ACCESS_TOKEN_FILE": str(config.access_token_file or Path("~/.config/lai-gateway/access-token").expanduser()),
        "LAI_GATEWAY_PAIR_TOKEN_FILE": str(config.pair_token_file or Path("~/.config/lai-gateway/pair-token.json").expanduser()),
    }
    if telegram_notify:
        env["LAI_GATEWAY_TELEGRAM_ENABLE_SEND"] = "1"
    exec_args = [
        python_bin,
        "-m",
        "lai_gateway",
        "mobile-serve",
        "--candidate-ip",
        candidate_ip,
        "--port",
        str(port),
    ]
    if telegram_notify:
        exec_args.append("--telegram-notify")
    if telegram_token_file is not None:
        exec_args.extend(["--telegram-token-file", str(telegram_token_file.expanduser())])
    if telegram_chat_id:
        exec_args.extend(["--telegram-chat-id", telegram_chat_id])
    lines = [
        "[Unit]",
        "Description=LAI Gateway mobile access",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
        f"WorkingDirectory={_unit_value(str(repo_dir))}",
    ]
    lines.extend(f"Environment={_unit_value(f'{key}={value}')}" for key, value in env.items())
    lines.extend(
        [
            "ExecStart=" + " ".join(_unit_arg(arg) for arg in exec_args),
            "Restart=on-failure",
            "RestartSec=5",
            "NoNewPrivileges=true",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )
    return "\n".join(lines)



def _systemd_user_status() -> dict[str, Any]:
    if shutil.which("systemctl") is None:
        return {"systemctl_available": False, "available": False, "detail": "systemctl not found"}
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "show-environment"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"systemctl_available": True, "available": False, "detail": _summarize_systemd_detail(str(exc))}
    if completed.returncode == 0:
        return {"systemctl_available": True, "available": True, "detail": "systemd user bus is reachable"}
    raw = f"{completed.stdout}\n{completed.stderr}".strip()
    return {"systemctl_available": True, "available": False, "detail": _summarize_systemd_detail(raw)}


def _summarize_systemd_detail(raw: str) -> str:
    cleaned = " ".join(raw.replace("\r", "").split()) or "systemd user bus is not reachable"
    if len(cleaned) > 160:
        return cleaned[:157] + "..."
    return cleaned

def _service_commands(service_name: str) -> dict[str, str]:
    return {
        "daemon_reload": "systemctl --user daemon-reload",
        "enable_now": f"systemctl --user enable --now {service_name}",
        "status": f"systemctl --user status {service_name}",
        "logs": f"journalctl --user -u {service_name} -n 80 --no-pager",
        "stop_disable": f"systemctl --user disable --now {service_name}",
    }


def _exec_start_from_unit(unit_text: str) -> str:
    for line in unit_text.splitlines():
        if line.startswith("ExecStart="):
            return line.split("=", 1)[1]
    return "none"


def _validate_candidate_ip(raw: str) -> str:
    ip = _safe_lan_ip(raw)
    if ip is None:
        raise ConfigError(f"service candidate-ip must be a concrete private LAN address: {raw}")
    return str(ip)


def _validate_port(port: int) -> None:
    if not 1 <= int(port) <= 65535:
        raise ConfigError("service port must be between 1 and 65535")


def _validate_service_name(name: str) -> None:
    if not name.endswith(".service"):
        raise ConfigError("service name must end with .service")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@_.-")
    if not name or any(ch not in allowed for ch in name) or "/" in name:
        raise ConfigError("service name contains unsafe characters")


def _unit_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _unit_arg(value: str) -> str:
    return _unit_value(value) if any(ch.isspace() or ch in '"\\' for ch in value) else value
