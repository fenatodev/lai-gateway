from __future__ import annotations

import ipaddress
import json
import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from .config import DEFAULT_PORT
from .lan import _discover_candidate_ips
from .qr import qr_svg

_TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")


def collect_mobile_access(
    *,
    port: int = DEFAULT_PORT,
    bind: str = "127.0.0.1",
    discovered_hosts: list[str] | None = None,
    windows_hosts: list[str] | None = None,
    tailscale_hosts: list[str] | None = None,
    force_wsl: bool | None = None,
) -> dict[str, Any]:
    wsl = is_wsl() if force_wsl is None else force_wsl
    linux_candidates = _discover_candidate_ips(discovered_hosts)
    connect_address = _wsl_connect_address(bind, linux_candidates) if wsl else None
    windows_candidates = _normalize_hosts(windows_hosts if windows_hosts is not None else (_windows_ipv4_hosts() if wsl else []), tailscale=False)
    tailscale_candidates = _normalize_hosts(tailscale_hosts if tailscale_hosts is not None else _tailscale_hosts(), tailscale=True)
    links: list[dict[str, Any]] = []
    for ip in tailscale_candidates:
        links.append(_link(ip, port, "tailscale", recommended=True, requires_portproxy=wsl, connect_address=connect_address))
    for ip in windows_candidates:
        kind = "windows-lan" if wsl else "lan"
        links.append(_link(ip, port, kind, recommended=not bool(links), requires_portproxy=wsl, connect_address=connect_address))
    for ip in linux_candidates:
        links.append(_link(ip, port, "wsl-internal" if wsl else "linux-lan", recommended=not bool(links), requires_portproxy=False, connect_address=None, phone_reachable=not wsl))
    links = _dedupe_links(links)
    recommended = next((item for item in links if item["recommended"]), links[0] if links else None)
    qr = qr_svg(recommended["url"]) if recommended else None
    warnings = []
    if wsl:
        warnings.append("WSL2 detected: phone usually cannot reach the WSL internal IP directly.")
        if _is_loopback_bind(bind):
            warnings.append("Current gateway bind is loopback; run mobile-serve with the WSL candidate before the QR URL works from a phone.")
        if any(item["requires_portproxy"] for item in links):
            warnings.append("Use the printed Windows portproxy command, or run mobile-proxy and point Tailscale Serve at its loopback URL.")
    if not links:
        warnings.append("no mobile access candidates detected")
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "mobile-access",
        "port": port,
        "bind": bind,
        "environment": {"wsl": wsl},
        "candidate_count": len(links),
        "recommended_url": recommended["url"] if recommended else None,
        "recommended_kind": recommended["kind"] if recommended else None,
        "qr_svg": qr,
        "links": links,
        "warnings": warnings,
        "security": {
            "qr_contains_token": False,
            "harness_control_token_browser_exposure": False,
            "starts_server": False,
            "modifies_files": False,
        },
    }


def render_mobile_access(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-access: {payload['candidate_count']} candidate(s)",
        f"version: {payload['version']}",
        f"wsl: {str(payload['environment']['wsl']).lower()}",
        f"bind: {payload['bind']}",
        f"port: {payload['port']}",
        f"recommended_url: {payload['recommended_url'] or 'none'}",
        "",
        "links:",
    ]
    if payload["links"]:
        for item in payload["links"]:
            marker = "recommended" if item["recommended"] else item["kind"]
            lines.append(f"  - {item['url']} ({marker})")
            if item.get("portproxy_command"):
                lines.append("    windows_portproxy:")
                lines.append(f"      {item['portproxy_command']}")
            if item.get("firewall_command"):
                lines.append("    windows_firewall:")
                lines.append(f"      {item['firewall_command']}")
            if item.get("mobile_bridge_apply_command"):
                lines.append("    lai_bridge_apply:")
                lines.append(f"      {item['mobile_bridge_apply_command']}")
            if item.get("mobile_proxy_command"):
                lines.append("    tailscale_serve_proxy:")
                lines.append(f"      {item['mobile_proxy_command']}")
                lines.append(f"      point Tailscale Serve to {item['tailscale_serve_target_url']}")
    else:
        lines.append("  none")
    if payload["warnings"]:
        lines.append("")
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in payload["warnings"])
    lines.append("")
    lines.append("QR is generated locally and contains only the URL, never tokens.")
    return "\n".join(lines)


def is_wsl() -> bool:
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "microsoft" in version or "wsl" in version


def _link(
    ip: str,
    port: int,
    kind: str,
    *,
    recommended: bool,
    requires_portproxy: bool,
    connect_address: str | None,
    phone_reachable: bool = True,
) -> dict[str, Any]:
    parsed = ipaddress.ip_address(ip)
    host = f"[{ip}]" if parsed.version == 6 else ip
    url = f"http://{host}:{port}/"
    payload: dict[str, Any] = {
        "ip": ip,
        "kind": kind,
        "url": url,
        "recommended": recommended,
        "phone_reachable": phone_reachable,
        "requires_portproxy": requires_portproxy,
    }
    if requires_portproxy and connect_address and parsed.version == 4:
        payload["portproxy_command"] = (
            f"netsh interface portproxy add v4tov4 listenaddress={ip} listenport={port} "
            f"connectaddress={connect_address} connectport={port}"
        )
        payload["firewall_command"] = (
            f"New-NetFirewallRule -DisplayName \"lai-gateway {port}\" -Direction Inbound "
            f"-Action Allow -Protocol TCP -LocalAddress {ip} -LocalPort {port} -Profile Private"
        )
        payload["mobile_bridge_apply_command"] = (
            f"lai-gateway mobile-bridge --listen-ip {ip} --connect-ip {connect_address} --port {port} --apply"
        )
        payload["mobile_bridge_remove_command"] = (
            f"lai-gateway mobile-bridge --listen-ip {ip} --connect-ip {connect_address} --port {port} --remove"
        )
        payload["mobile_proxy_command"] = (
            f"lai-gateway-mobile-proxy --target-host {connect_address} --target-port {port}"
        )
        payload["tailscale_serve_target_url"] = "http://127.0.0.1:18787"
    return payload


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    recommended_seen = False
    for item in links:
        if item["ip"] in seen:
            continue
        seen.add(item["ip"])
        if item["recommended"] and not recommended_seen:
            recommended_seen = True
        elif item["recommended"]:
            item = {**item, "recommended": False}
        out.append(item)
    return out


def _normalize_hosts(hosts: list[str], *, tailscale: bool) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in hosts:
        try:
            ip = ipaddress.ip_address(str(raw).strip().split("%", 1)[0])
        except ValueError:
            continue
        ok = ip in _TAILSCALE_NET if tailscale else _is_private_lan(ip)
        if not ok:
            continue
        normalized = str(ip)
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def _is_private_lan(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved or ip.is_link_local or ip.is_global:
        return False
    return ip.is_private and ip not in _TAILSCALE_NET


def _wsl_connect_address(bind: str, linux_candidates: list[str]) -> str | None:
    if not _is_loopback_bind(bind):
        return bind
    return linux_candidates[0] if linux_candidates else None


def _is_loopback_bind(bind: str) -> bool:
    try:
        return ipaddress.ip_address(bind).is_loopback
    except ValueError:
        return bind == "localhost"


def _windows_ipv4_hosts() -> list[str]:
    return _windows_lan_hosts_from_rows(_powershell_ip_rows())


def _windows_lan_hosts_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in rows:
        alias = str(row.get("InterfaceAlias", "")).lower()
        if any(term in alias for term in ("tailscale", "wsl", "hyper-v", "vethernet", "docker")):
            continue
        out.append(str(row.get("IPAddress", "")))
    return out


def _tailscale_hosts() -> list[str]:
    hosts: list[str] = []
    for cmd in (["tailscale", "ip", "-4"], ["tailscale.exe", "ip", "-4"]):
        try:
            result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        hosts.extend(line.strip() for line in result.stdout.splitlines())
    for row in _powershell_ip_rows():
        if "tailscale" in str(row.get("InterfaceAlias", "")).lower():
            hosts.append(str(row.get("IPAddress", "")))
    return hosts


def _powershell_ip_rows() -> list[dict[str, Any]]:
    script = (
        "Get-NetIPAddress -AddressFamily IPv4 | "
        "Where-Object { $_.IPAddress -notlike '127.*' } | "
        "Select-Object IPAddress,InterfaceAlias,PrefixLength | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []
