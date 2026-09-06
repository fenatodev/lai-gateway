from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import __version__
from .config import DEFAULT_PORT
from .errors import ConfigError
from .lan import collect_lan_info
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
