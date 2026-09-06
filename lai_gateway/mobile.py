from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
import socket

from . import __version__
from .access import collect_mobile_access
from .config import DEFAULT_HARNESS_URL, DEFAULT_PORT, DEFAULT_TOKEN_FILE, GatewayConfig
from .errors import ConfigError
from .lan import _safe_lan_ip, collect_lan_info
from .tokens import (
    check_gateway_access_token_file,
    check_gateway_pairing_token_file,
    create_gateway_access_token,
    create_gateway_pairing_token,
    default_access_token_path,
    default_pair_token_path,
)


def collect_mobile_start(
    *,
    port: int = DEFAULT_PORT,
    ttl_seconds: int = 600,
    prepare: bool = False,
    show_pair: bool = False,
    access_token_path: Path | None = None,
    pair_token_path: Path | None = None,
    discovered_hosts: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build a mobile access plan and optionally prepare token files.

    The default mode is read-only. Mutations happen only when prepare=True.
    Pair token values are included only when show_pair=True.
    """
    access_path = (access_token_path or default_access_token_path()).expanduser()
    pair_path = (pair_token_path or default_pair_token_path()).expanduser()
    lan = collect_lan_info(port=port, discovered_hosts=discovered_hosts)
    actions: list[dict[str, Any]] = []

    access = _inspect_access_token(access_path)
    pair = _inspect_pair_token(pair_path)

    if prepare:
        if not access["ok"]:
            if access["exists"]:
                raise ConfigError(f"cannot prepare mobile start with invalid gateway access token: {access['detail']}")
            created = create_gateway_access_token(access_path)
            actions.append({"name": "access_token_created", "path": created["path"], "mode": created["mode"]})
            access = _inspect_access_token(access_path)
        pair_created = create_gateway_pairing_token(
            pair_path,
            ttl_seconds=ttl_seconds,
            force=True,
            include_token=show_pair,
            ui_url=_preferred_url(lan),
        )
        action = {
            "name": "pair_token_created",
            "path": pair_created["path"],
            "mode": pair_created["mode"],
            "ttl_seconds": pair_created["ttl_seconds"],
            "expires_at": pair_created["expires_at"],
            "printed_token": pair_created["printed_token"],
        }
        if show_pair:
            action["pair_token"] = pair_created["token"]
        actions.append(action)
        pair = _inspect_pair_token(pair_path)

    preferred = lan["candidates"][0] if lan["candidates"] else None
    status = _overall_status(lan, access, pair, prepare=prepare)
    payload: dict[str, Any] = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "mobile-start",
        "overall": status,
        "port": port,
        "ttl_seconds": ttl_seconds,
        "prepare": prepare,
        "starts_server": False,
        "modifies_files": prepare,
        "candidate_count": lan["candidate_count"],
        "preferred_url": preferred["url"] if preferred else None,
        "preferred_command": preferred["dev_command"] if preferred else None,
        "candidates": lan["candidates"],
        "access_token": access,
        "pair_token": pair,
        "actions": actions,
        "next_steps": _next_steps(preferred, access, pair),
        "security": {
            "private_bind_is_opt_in": True,
            "starts_server": False,
            "harness_control_token_browser_exposure": False,
            "browser_storage_required": False,
            "pair_token_printed_only_when_requested": True,
        },
    }
    return payload


def prepare_mobile_serve_config(
    *,
    candidate_ip: str | None = None,
    port: int = DEFAULT_PORT,
    ttl_seconds: int = 600,
    show_pair: bool = False,
    access_token_path: Path | None = None,
    pair_token_path: Path | None = None,
    discovered_hosts: Iterable[str] | None = None,
    env: dict[str, str] | None = None,
) -> tuple[dict[str, Any], GatewayConfig]:
    """Prepare mobile access and return a private-bind config for serving.

    This function writes token files by design. It does not start the server.
    """
    access_path = (access_token_path or default_access_token_path()).expanduser()
    pair_path = (pair_token_path or default_pair_token_path()).expanduser()
    hosts = [candidate_ip] if candidate_ip else discovered_hosts
    candidate_probe = collect_mobile_start(
        port=port,
        ttl_seconds=ttl_seconds,
        prepare=False,
        show_pair=False,
        access_token_path=access_path,
        pair_token_path=pair_path,
        discovered_hosts=hosts,
    )
    chosen = _single_mobile_candidate(candidate_probe)
    _ensure_no_existing_listener(chosen["ip"], port)
    payload = collect_mobile_start(
        port=port,
        ttl_seconds=ttl_seconds,
        prepare=True,
        show_pair=show_pair,
        access_token_path=access_path,
        pair_token_path=pair_path,
        discovered_hosts=[chosen["ip"]],
    )
    values = {
        "LAI_GATEWAY_HARNESS_URL": DEFAULT_HARNESS_URL,
        "LAI_GATEWAY_TOKEN_FILE": DEFAULT_TOKEN_FILE,
        "LAI_GATEWAY_PRIVATE_BIND": "1",
        "LAI_GATEWAY_BIND": chosen["ip"],
        "LAI_GATEWAY_PORT": str(port),
        "LAI_GATEWAY_ACCESS_TOKEN_FILE": str(access_path),
        "LAI_GATEWAY_PAIR_TOKEN_FILE": str(pair_path),
    }
    if env:
        for key in ("LAI_GATEWAY_HARNESS_URL", "LAI_GATEWAY_TOKEN_FILE", "LAI_GATEWAY_TIMEOUT_SECONDS"):
            if key in env:
                values[key] = env[key]
    config = GatewayConfig.from_env(values)
    mobile_access = collect_mobile_access(port=port, bind=config.bind, discovered_hosts=[chosen["ip"]])
    payload = dict(payload)
    payload["operation"] = "mobile-serve"
    payload["starts_server"] = True
    payload["modifies_files"] = True
    payload["selected_candidate"] = chosen
    payload["serve"] = {
        "bind": config.bind,
        "port": config.port,
        "url": chosen["url"],
        "access_mode": config.access_mode,
    }
    payload["mobile_access"] = mobile_access
    payload["scan_url"] = mobile_access.get("recommended_url") or chosen["url"]
    payload["security"] = dict(payload["security"], requires_private_bind=True, wildcard_bind_allowed=False, public_bind_allowed=False)
    return payload, config


def _ensure_no_existing_listener(ip: str, port: int) -> None:
    if _tcp_connects(ip, port):
        raise ConfigError(
            f"mobile serve target already has a listener: {ip}:{port}; stop the existing mobile-serve process or choose --port"
        )


def collect_mobile_status(
    *,
    port: int = DEFAULT_PORT,
    bind: str = "127.0.0.1",
    candidate_ip: str | None = None,
    access_token_path: Path | None = None,
    pair_token_path: Path | None = None,
    discovered_hosts: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Inspect mobile access readiness without mutating files or starting servers."""
    access_path = (access_token_path or default_access_token_path()).expanduser()
    pair_path = (pair_token_path or default_pair_token_path()).expanduser()
    hosts = [candidate_ip] if candidate_ip else discovered_hosts
    lan = collect_lan_info(port=port, discovered_hosts=hosts)
    selected = _select_status_target(bind=bind, candidate_ip=candidate_ip, lan=lan, port=port)
    target_ip = selected["ip"] if selected else None
    listener_active = _tcp_connects(target_ip, port) if target_ip else False
    access = _inspect_access_token(access_path)
    pair = _inspect_pair_token(pair_path)
    mobile_access = collect_mobile_access(
        port=port,
        bind=target_ip or bind,
        discovered_hosts=[target_ip] if target_ip else None,
    )
    overall = _mobile_status_overall(target_ip=target_ip, listener_active=listener_active, access=access, pair=pair)
    payload: dict[str, Any] = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "mobile-status",
        "overall": overall,
        "port": port,
        "bind": bind,
        "starts_server": False,
        "modifies_files": False,
        "selected_candidate": selected,
        "listener": {
            "target": f"{target_ip}:{port}" if target_ip else None,
            "ip": target_ip,
            "port": port,
            "active": listener_active,
        },
        "access_token": access,
        "pair_token": pair,
        "mobile_access": mobile_access,
        "next_steps": _mobile_status_next_steps(
            target_ip=target_ip,
            port=port,
            listener_active=listener_active,
            access=access,
            pair=pair,
            mobile_access=mobile_access,
        ),
        "security": {
            "starts_server": False,
            "modifies_files": False,
            "prints_tokens": False,
            "network_probe_local_only": True,
            "harness_control_token_browser_exposure": False,
        },
    }
    return payload


def render_mobile_status(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-status: {payload['overall']}",
        f"version: {payload['version']}",
        f"target: {payload['listener']['target'] or 'none'}",
        f"listener: {'active' if payload['listener']['active'] else 'none'}",
        "starts_server: false",
        "modifies_files: false",
        f"access_token: {payload['access_token']['status']} ({payload['access_token']['path']})",
        f"pair_token: {payload['pair_token']['status']} ({payload['pair_token']['path']})",
    ]
    if payload["pair_token"].get("expires_at"):
        lines.append(f"pair_expires_at: {payload['pair_token']['expires_at']}")
        lines.append(f"pair_seconds_remaining: {payload['pair_token']['seconds_remaining']}")
    mobile_access = payload.get("mobile_access", {})
    if mobile_access.get("recommended_url"):
        lines.append(f"scan_url: {mobile_access['recommended_url']}")
        recommended = next((item for item in mobile_access.get("links", []) if item.get("recommended")), None)
        if recommended and recommended.get("mobile_bridge_apply_command"):
            lines.append("lai_bridge_apply:")
            lines.append(f"  {recommended['mobile_bridge_apply_command']}")
    if mobile_access.get("warnings"):
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in mobile_access["warnings"])
    if payload["next_steps"]:
        lines.append("next_steps:")
        lines.extend(f"  {step}" for step in payload["next_steps"])
    return "\n".join(lines)


def _tcp_connects(ip: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(0.10)
    try:
        return sock.connect_ex((ip, int(port))) == 0
    except OSError:
        return False
    finally:
        sock.close()


def render_mobile_serve_ready(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-serve: {payload['overall']}",
        f"version: {payload['version']}",
        f"access: {payload['serve']['access_mode']}",
        f"ui: {payload['serve']['url']}",
        f"scan_url: {payload.get('scan_url') or payload['serve']['url']}",
        "starts_server: true",
        "modifies_files: true",
    ]
    mobile_access = payload.get("mobile_access", {})
    if payload.get("scan_url"):
        lines.append("phone:")
        lines.append(f"  scan_url: {payload['scan_url']}")
        recommended = next((item for item in mobile_access.get("links", []) if item.get("recommended")), None)
        if recommended and recommended.get("portproxy_command"):
            lines.append("  windows_portproxy:")
            lines.append(f"    {recommended['portproxy_command']}")
        if recommended and recommended.get("firewall_command"):
            lines.append("  windows_firewall:")
            lines.append(f"    {recommended['firewall_command']}")
        if recommended and recommended.get("mobile_bridge_apply_command"):
            lines.append("  lai_bridge_apply:")
            lines.append(f"    {recommended['mobile_bridge_apply_command']}")
    if mobile_access.get("warnings"):
        lines.append("mobile_warnings:")
        for warning in mobile_access["warnings"]:
            lines.append(f"  - {warning}")
    if payload["actions"]:
        lines.append("actions:")
        for action in payload["actions"]:
            lines.append(f"  - {action['name']}")
            if action.get("expires_at"):
                lines.append(f"    expires_at: {action['expires_at']}")
            if action.get("pair_token"):
                lines.append(f"    pair_token: {action['pair_token']}")
    lines.append("Paste the temporary pair token into the UI and keep it only in page memory.")
    return "\n".join(lines)


def _single_mobile_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates", [])
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ConfigError("mobile serve requires a private LAN candidate; pass --candidate-ip when autodetection fails")
    raise ConfigError("mobile serve found multiple private LAN candidates; pass --candidate-ip to choose one")


def render_mobile_start(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-start: {payload['overall']}",
        f"version: {payload['version']}",
        f"port: {payload['port']}",
        f"prepare: {str(payload['prepare']).lower()}",
        "starts_server: false",
        f"modifies_files: {str(payload['modifies_files']).lower()}",
        "",
        f"access_token: {payload['access_token']['status']} ({payload['access_token']['path']})",
        f"pair_token: {payload['pair_token']['status']} ({payload['pair_token']['path']})",
    ]
    if payload["pair_token"].get("expires_at"):
        lines.append(f"pair_expires_at: {payload['pair_token']['expires_at']}")
        lines.append(f"pair_seconds_remaining: {payload['pair_token']['seconds_remaining']}")
    if payload["preferred_url"]:
        lines.extend(["", f"mobile_url: {payload['preferred_url']}", "command:", f"  {payload['preferred_command']}"])
    else:
        lines.extend(["", "mobile_url: none"])
    if payload["actions"]:
        lines.append("")
        lines.append("actions:")
        for action in payload["actions"]:
            lines.append(f"  - {action['name']}")
            if action.get("expires_at"):
                lines.append(f"    expires_at: {action['expires_at']}")
            if action.get("pair_token"):
                lines.append(f"    pair_token: {action['pair_token']}")
    lines.append("")
    lines.append("next_steps:")
    lines.extend(f"  {step}" for step in payload["next_steps"])
    return "\n".join(lines)


def _inspect_access_token(path: Path) -> dict[str, Any]:
    target = path.expanduser()
    exists = target.exists()
    try:
        checked = check_gateway_access_token_file(target)
    except ConfigError as exc:
        return {"path": str(target), "ok": False, "exists": exists, "status": "invalid" if exists else "missing", "detail": str(exc)}
    return {"path": checked["path"], "ok": True, "exists": True, "status": "ready", "mode": checked["mode"], "token_length": checked["token_length"]}


def _inspect_pair_token(path: Path) -> dict[str, Any]:
    target = path.expanduser()
    exists = target.exists()
    try:
        checked = check_gateway_pairing_token_file(target)
    except ConfigError as exc:
        status = "invalid" if exists else "missing"
        if exists and "expired" in str(exc).lower():
            status = "expired"
        return {"path": str(target), "ok": False, "exists": exists, "status": status, "detail": str(exc)}
    return {
        "path": checked["path"],
        "ok": True,
        "exists": True,
        "status": "ready",
        "mode": checked["mode"],
        "expires_at": checked["expires_at"],
        "seconds_remaining": checked["seconds_remaining"],
        "token_length": checked["token_length"],
    }


def _select_status_target(*, bind: str, candidate_ip: str | None, lan: dict[str, Any], port: int) -> dict[str, Any] | None:
    if candidate_ip:
        return {"ip": candidate_ip, "url": f"http://{candidate_ip}:{port}/", "source": "candidate-ip"}
    if bind and bind not in {"127.0.0.1", "localhost", "::1"}:
        return {"ip": bind, "url": f"http://{bind}:{port}/", "source": "bind"}
    candidates = lan.get("candidates", [])
    if candidates:
        selected = dict(candidates[0])
        selected["source"] = "lan"
        return selected
    return None


def _mobile_status_overall(
    *,
    target_ip: str | None,
    listener_active: bool,
    access: dict[str, Any],
    pair: dict[str, Any],
) -> str:
    if target_ip is None:
        return "blocked"
    if not access["ok"]:
        return "needs_prepare"
    if not pair["ok"]:
        return "needs_pair"
    if not listener_active:
        return "needs_server"
    return "ready"


def _mobile_status_next_steps(
    *,
    target_ip: str | None,
    port: int,
    listener_active: bool,
    access: dict[str, Any],
    pair: dict[str, Any],
    mobile_access: dict[str, Any],
) -> list[str]:
    if target_ip is None:
        return ["No private LAN IP candidate detected; pass --candidate-ip when you know the WSL/private address."]
    steps: list[str] = []
    if not access["ok"] or not pair["ok"]:
        steps.append(f"Prepare mobile tokens: lai-gateway mobile-start --candidate-ip {target_ip} --port {port} --prepare --show-pair")
    if not listener_active:
        steps.append(f"Start private gateway: lai-gateway mobile-serve --candidate-ip {target_ip} --port {port}")
    recommended = next((item for item in mobile_access.get("links", []) if item.get("recommended")), None)
    if recommended and recommended.get("mobile_bridge_apply_command"):
        steps.append(f"Apply phone bridge if needed: {recommended['mobile_bridge_apply_command']}")
    if listener_active and access["ok"] and pair["ok"] and mobile_access.get("recommended_url"):
        steps.append(f"Open on phone: {mobile_access['recommended_url']}")
    return steps


def _preferred_url(lan_payload: dict[str, Any]) -> str | None:
    candidates = lan_payload.get("candidates", [])
    return candidates[0]["url"] if candidates else None


def _overall_status(lan: dict[str, Any], access: dict[str, Any], pair: dict[str, Any], *, prepare: bool) -> str:
    if lan["candidate_count"] <= 0:
        return "blocked"
    if not access["ok"]:
        return "blocked" if prepare and access["exists"] else "needs_prepare"
    if not pair["ok"]:
        return "needs_prepare"
    return "ready"


def _next_steps(preferred: dict[str, Any] | None, access: dict[str, Any], pair: dict[str, Any]) -> list[str]:
    steps: list[str] = []
    if not access["ok"]:
        steps.append("Run: lai-gateway token create")
    if not pair["ok"]:
        steps.append("Run: lai-gateway pair create --ttl-seconds 600 --show")
    if preferred is not None:
        steps.append(f"Start private gateway: {preferred['dev_command']}")
        steps.append(f"Open on phone: {preferred['url']}")
        steps.append("Paste the temporary pair token into the UI and keep it only in page memory.")
    else:
        steps.append("No private LAN IP candidate detected; stay on loopback until network discovery is available.")
    return steps
