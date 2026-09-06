from __future__ import annotations

import ipaddress
import shlex
import socket
from collections.abc import Iterable
from typing import Any

from . import __version__
from .config import DEFAULT_ACCESS_TOKEN_FILE, DEFAULT_PAIR_TOKEN_FILE, DEFAULT_PORT


def collect_lan_info(*, port: int = DEFAULT_PORT, discovered_hosts: Iterable[str] | None = None) -> dict[str, Any]:
    """Return private LAN candidates and exact safe startup commands.

    This is intentionally read-only: no token creation, no server startup, no bind check side effects.
    """
    _validate_port(port)
    candidates = [_candidate_payload(ip, port) for ip in _discover_candidate_ips(discovered_hosts)]
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "lan-info",
        "port": port,
        "starts_server": False,
        "modifies_files": False,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "security": {
            "loopback_is_default": True,
            "private_bind_is_opt_in": True,
            "wildcard_bind_allowed": False,
            "public_bind_allowed": False,
            "requires_gateway_access_token": True,
            "pair_token_supported": True,
            "harness_control_token_browser_exposure": False,
        },
        "setup_commands": [
            "lai-gateway token create",
            "lai-gateway token check",
            "lai-gateway pair create --ttl-seconds 600 --show",
        ],
        "warnings": [] if candidates else ["no private LAN candidate IPs were detected"],
    }


def render_lan_info(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway lan-info: {payload['candidate_count']} candidate(s)",
        f"version: {payload['version']}",
        f"port: {payload['port']}",
        "starts_server: false",
        "modifies_files: false",
        "",
        "setup:",
    ]
    lines.extend(f"  {command}" for command in payload["setup_commands"])
    lines.append("")
    if payload["candidates"]:
        lines.append("candidates:")
        for item in payload["candidates"]:
            lines.append(f"  - {item['ip']} -> {item['url']}")
            lines.append("    command:")
            lines.append(f"      {item['dev_command']}")
    else:
        lines.append("candidates: none")
    if payload["warnings"]:
        lines.append("")
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in payload["warnings"])
    lines.append("")
    lines.append("Private LAN serving still requires LAI_GATEWAY_PRIVATE_BIND=1 and a gateway access token.")
    return "\n".join(lines)


def _discover_candidate_ips(discovered_hosts: Iterable[str] | None = None) -> list[str]:
    raw_hosts = list(discovered_hosts) if discovered_hosts is not None else _system_address_strings()
    unique: list[str] = []
    seen: set[str] = set()
    for raw in raw_hosts:
        parsed = _safe_lan_ip(raw)
        if parsed is None:
            continue
        normalized = str(parsed)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _system_address_strings() -> list[str]:
    hosts: set[str] = set()
    names = {socket.gethostname(), socket.getfqdn()}
    for name in sorted(names):
        if not name:
            continue
        try:
            for info in socket.getaddrinfo(name, None, family=socket.AF_UNSPEC, type=socket.SOCK_DGRAM):
                hosts.add(str(info[4][0]))
        except OSError:
            continue
    for target in (("192.0.2.1", 9, socket.AF_INET), ("2001:db8::1", 9, socket.AF_INET6)):
        candidate = _outbound_source_address(*target)
        if candidate:
            hosts.add(candidate)
    return sorted(hosts)


def _outbound_source_address(host: str, port: int, family: int) -> str | None:
    sock = socket.socket(family, socket.SOCK_DGRAM)
    try:
        sock.connect((host, port))
        return str(sock.getsockname()[0])
    except OSError:
        return None
    finally:
        sock.close()


def _safe_lan_ip(raw: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        ip = ipaddress.ip_address(raw.split("%", 1)[0])
    except ValueError:
        return None
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved or ip.is_link_local:
        return None
    if ip.is_global:
        return None
    if not ip.is_private:
        return None
    return ip


def _candidate_payload(ip: str, port: int) -> dict[str, Any]:
    parsed = ipaddress.ip_address(ip)
    url_host = f"[{ip}]" if parsed.version == 6 else ip
    url = f"http://{url_host}:{port}/"
    command = _private_dev_command(ip, port)
    return {
        "ip": ip,
        "ip_version": parsed.version,
        "url": url,
        "dev_command": command,
        "pair_command": "lai-gateway pair create --ttl-seconds 600 --show",
        "notes": [
            "Run this only on a trusted private LAN.",
            "Paste the temporary pair token into the UI and keep it only in page memory.",
        ],
    }


def _private_dev_command(ip: str, port: int) -> str:
    env_parts = {
        "LAI_GATEWAY_PRIVATE_BIND": "1",
        "LAI_GATEWAY_BIND": ip,
        "LAI_GATEWAY_ACCESS_TOKEN_FILE": _shell_path(DEFAULT_ACCESS_TOKEN_FILE),
        "LAI_GATEWAY_PAIR_TOKEN_FILE": _shell_path(DEFAULT_PAIR_TOKEN_FILE),
    }
    prefix = " ".join(_shell_assignment(key, value) for key, value in env_parts.items())
    return f"{prefix} lai-gateway dev --no-open --bind {shlex.quote(ip)} --port {port}"


def _shell_assignment(key: str, value: str) -> str:
    if value.startswith("${HOME}/"):
        return f"{key}={value}"
    return f"{key}={shlex.quote(value)}"


def _shell_path(path: str) -> str:
    if path.startswith("~/"):
        return "${HOME}/" + path[2:]
    return path


def _validate_port(port: int) -> None:
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be between 1 and 65535")
