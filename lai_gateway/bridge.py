from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from . import __version__
from .config import DEFAULT_PORT
from .errors import ConfigError
from .access import collect_mobile_access

_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class BridgePlan:
    listen_ip: str
    connect_ip: str
    port: int
    firewall_profile: str = "Private"


def collect_mobile_bridge(
    *,
    port: int = DEFAULT_PORT,
    listen_ip: str | None = None,
    connect_ip: str | None = None,
    target: str = "recommended",
    apply: bool = False,
    remove: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    if apply and remove:
        raise ConfigError("mobile-bridge cannot apply and remove in the same run")
    _validate_port(port)
    access = collect_mobile_access(bind="127.0.0.1", port=port)
    plan = _resolve_plan(access, port=port, listen_ip=listen_ip, connect_ip=connect_ip, target=target)
    commands = _bridge_commands(plan)
    payload: dict[str, Any] = {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "mobile-bridge",
        "starts_server": False,
        "modifies_files": False,
        "modifies_windows_network": bool(apply or remove),
        "requires_admin": True,
        "wsl": access.get("environment", {}).get("wsl", False),
        "target": target,
        "listen_ip": plan.listen_ip,
        "connect_ip": plan.connect_ip,
        "port": plan.port,
        "url": f"http://{plan.listen_ip}:{plan.port}/",
        "commands": commands,
        "results": [],
        "warnings": _warnings(access, plan),
        "security": {
            "tokens_involved": False,
            "harness_token_exposed": False,
            "pair_token_exposed": False,
            "wildcard_bind_allowed": False,
            "public_ip_allowed": False,
            "tailscale_cgnat_allowed": _is_tailscale_ip(plan.listen_ip),
        },
    }
    if apply or remove:
        payload["results"] = _execute_windows_bridge(commands["apply" if apply else "remove"], runner=runner)
    return payload


def render_mobile_bridge(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-bridge: {payload['url']}",
        f"version: {payload['version']}",
        f"wsl: {str(payload['wsl']).lower()}",
        f"listen_ip: {payload['listen_ip']}",
        f"connect_ip: {payload['connect_ip']}",
        f"port: {payload['port']}",
        f"requires_admin: {str(payload['requires_admin']).lower()}",
        f"modifies_windows_network: {str(payload['modifies_windows_network']).lower()}",
        "",
        "apply:",
    ]
    lines.extend(f"  {command}" for command in payload["commands"]["apply"])
    lines.append("remove:")
    lines.extend(f"  {command}" for command in payload["commands"]["remove"])
    if payload.get("warnings"):
        lines.append("")
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in payload["warnings"])
    if payload.get("results"):
        lines.append("")
        lines.append("results:")
        for result in payload["results"]:
            lines.append(f"  - {result['name']}: rc={result['returncode']}")
            if result.get("summary"):
                lines.append(f"    {result['summary']}")
    return "\n".join(lines)


def _resolve_plan(
    access: dict[str, Any],
    *,
    port: int,
    listen_ip: str | None,
    connect_ip: str | None,
    target: str,
) -> BridgePlan:
    links = access.get("links", [])
    if listen_ip is None:
        chosen = _choose_link(links, target)
        listen_ip = chosen["ip"]
        connect_ip = connect_ip or chosen.get("connect_address") or _connect_address_from_link(chosen, access)
    else:
        _validate_listen_ip(listen_ip)
        connect_ip = connect_ip or _default_connect_ip(access)
    if connect_ip is None:
        raise ConfigError("mobile-bridge could not determine the WSL connect address; pass --connect-ip")
    _validate_connect_ip(connect_ip)
    return BridgePlan(listen_ip=listen_ip, connect_ip=connect_ip, port=port)


def _choose_link(links: list[dict[str, Any]], target: str) -> dict[str, Any]:
    if target not in {"recommended", "tailscale", "windows-lan"}:
        raise ConfigError("mobile-bridge target must be recommended, tailscale, or windows-lan")
    if target == "recommended":
        chosen = next((item for item in links if item.get("recommended")), None)
    else:
        chosen = next((item for item in links if item.get("kind") == target), None)
    if chosen is None:
        raise ConfigError(f"mobile-bridge could not find a {target} mobile access candidate")
    _validate_listen_ip(str(chosen["ip"]))
    return chosen


def _connect_address_from_link(link: dict[str, Any], access: dict[str, Any]) -> str | None:
    command = link.get("portproxy_command")
    if isinstance(command, str):
        marker = "connectaddress="
        if marker in command:
            return command.split(marker, 1)[1].split()[0]
    return _default_connect_ip(access)


def _default_connect_ip(access: dict[str, Any]) -> str | None:
    for item in access.get("links", []):
        if item.get("kind") == "wsl-internal":
            return str(item.get("ip"))
    return None


def _bridge_commands(plan: BridgePlan) -> dict[str, list[str]]:
    display_name = f"lai-gateway {plan.port}"
    add_proxy = (
        f"netsh interface portproxy add v4tov4 listenaddress={plan.listen_ip} listenport={plan.port} "
        f"connectaddress={plan.connect_ip} connectport={plan.port}"
    )
    delete_proxy = f"netsh interface portproxy delete v4tov4 listenaddress={plan.listen_ip} listenport={plan.port}"
    add_firewall = (
        f"New-NetFirewallRule -DisplayName \"{display_name}\" -Direction Inbound -Action Allow "
        f"-Protocol TCP -LocalAddress {plan.listen_ip} -LocalPort {plan.port} -Profile {plan.firewall_profile}"
    )
    delete_firewall = f"Remove-NetFirewallRule -DisplayName \"{display_name}\" -ErrorAction SilentlyContinue"
    return {"apply": [add_proxy, add_firewall], "remove": [delete_proxy, delete_firewall]}


def _execute_windows_bridge(commands: list[str], *, runner: Runner | None = None) -> list[dict[str, Any]]:
    if runner is None and shutil.which("powershell.exe") is None:
        raise ConfigError("mobile-bridge apply/remove requires powershell.exe from WSL on Windows")
    run = runner or _run_powershell_command
    results: list[dict[str, Any]] = []
    for index, command in enumerate(commands):
        name = "portproxy" if index == 0 else "firewall"
        completed = run(["powershell.exe", "-NoProfile", "-Command", command])
        combined = f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()
        results.append({
            "name": name,
            "returncode": completed.returncode,
            "ok": completed.returncode == 0,
            "summary": _summarize_output(combined),
        })
    return results


def _run_powershell_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)


def _summarize_output(raw: str) -> str:
    if not raw:
        return "ok"
    cleaned = " ".join(raw.replace("\r", "").split())
    if len(cleaned) > 240:
        return cleaned[:237] + "..."
    return cleaned


def _warnings(access: dict[str, Any], plan: BridgePlan) -> list[str]:
    warnings = list(access.get("warnings", []))
    warnings.append("Run apply/remove from an elevated Windows context; non-admin shells may fail.")
    warnings.append("Bridge setup contains no tokens; it only forwards the selected Windows/Tailscale IP to WSL.")
    if _is_tailscale_ip(plan.listen_ip):
        warnings.append("Tailscale must be running on both devices and the phone must use the same tailnet.")
    return warnings


def _validate_listen_ip(raw: str) -> None:
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError as exc:
        raise ConfigError(f"invalid listen ip: {raw}") from exc
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved or ip.is_link_local or ip.is_global:
        raise ConfigError(f"unsafe listen ip for mobile bridge: {raw}")
    if ip.version != 4:
        raise ConfigError("mobile-bridge currently supports IPv4 only")
    if not (ip.is_private or _is_tailscale_ip(str(ip))):
        raise ConfigError(f"listen ip must be private LAN or Tailscale CGNAT: {raw}")


def _validate_connect_ip(raw: str) -> None:
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError as exc:
        raise ConfigError(f"invalid connect ip: {raw}") from exc
    if ip.version != 4 or ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved or ip.is_link_local or ip.is_global:
        raise ConfigError(f"unsafe WSL connect ip for mobile bridge: {raw}")
    if not ip.is_private:
        raise ConfigError(f"connect ip must be private WSL address: {raw}")


def _is_tailscale_ip(raw: str) -> bool:
    try:
        return ipaddress.ip_address(raw) in _TAILSCALE_CGNAT
    except ValueError:
        return False


def _validate_port(port: int) -> None:
    if not 1 <= int(port) <= 65535:
        raise ConfigError("mobile-bridge port must be between 1 and 65535")
