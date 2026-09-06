from __future__ import annotations

import ipaddress
import json
import select
import socket
import socketserver
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from . import __version__
from .errors import ConfigError


@dataclass(frozen=True)
class MobileProxyConfig:
    listen_host: str
    listen_port: int
    target_host: str
    target_port: int
    connect_timeout: float = 5.0

    @property
    def listen_url(self) -> str:
        return f"http://{self.listen_host}:{self.listen_port}/"

    @property
    def target_url(self) -> str:
        return f"http://{self.target_host}:{self.target_port}/"


def collect_mobile_proxy_status(
    *,
    listen_host: str = "127.0.0.1",
    listen_port: int = 18787,
    target_host: str,
    target_port: int = 8787,
    connect_timeout: float = 5.0,
) -> dict[str, Any]:
    config = validate_mobile_proxy_config(
        listen_host=listen_host,
        listen_port=listen_port,
        target_host=target_host,
        target_port=target_port,
        connect_timeout=connect_timeout,
    )
    target = _tcp_check(config.target_host, config.target_port, timeout=config.connect_timeout)
    listen_available = _bind_check(config.listen_host, config.listen_port)
    listen_http = _http_health_check(config.listen_host, config.listen_port, timeout=config.connect_timeout)
    if target["ok"] and listen_http["ok"] and not listen_available["ok"]:
        overall = "ready"
    elif target["ok"] and listen_available["ok"]:
        overall = "ready_to_start"
    else:
        overall = "blocked"
    return {
        "operation": "mobile-proxy",
        "version": __version__,
        "overall": overall,
        "starts_server": False,
        "modifies_files": False,
        "prints_tokens": False,
        "listen": {"host": config.listen_host, "port": config.listen_port, "url": config.listen_url},
        "target": {"host": config.target_host, "port": config.target_port, "url": config.target_url},
        "checks": {"target_tcp": target, "listen_available": listen_available, "listen_http": listen_http},
        "security": {
            "loopback_listen_only": _is_loopback(config.listen_host),
            "private_target_only": _is_private_or_loopback(config.target_host),
            "payload_logging": False,
            "prints_tokens": False,
            "reads_tokens": False,
            "stores_tokens": False,
        },
        "next_steps": _proxy_next_steps(config, overall=overall),
    }


def render_mobile_proxy_status(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway mobile-proxy: {payload['overall']}",
        f"version: {payload['version']}",
        f"starts_server: {str(payload['starts_server']).lower()}",
        f"modifies_files: {str(payload['modifies_files']).lower()}",
        f"listen: {payload['listen']['url']}",
        f"target: {payload['target']['url']}",
        f"target_tcp: {'ok' if payload['checks']['target_tcp']['ok'] else 'fail'}",
        f"listen_available: {'ok' if payload['checks']['listen_available']['ok'] else 'fail'}",
        f"listen_http: {'ok' if payload['checks']['listen_http']['ok'] else 'fail'}",
    ]
    if payload.get("next_steps"):
        lines.append("next_steps:")
        for step in payload["next_steps"]:
            lines.append(f"  {step}")
    return "\n".join(lines)


def run_mobile_proxy(config: MobileProxyConfig) -> None:
    handler = _build_proxy_handler(config)
    with _ThreadingTCPServer((config.listen_host, config.listen_port), handler) as server:
        print("lai-gateway mobile-proxy: ready", flush=True)
        print(f"version: {__version__}", flush=True)
        print(f"listen: {config.listen_url}", flush=True)
        print(f"target: {config.target_url}", flush=True)
        print("payload_logging: false", flush=True)
        server.serve_forever()


def validate_mobile_proxy_config(
    *,
    listen_host: str,
    listen_port: int,
    target_host: str,
    target_port: int,
    connect_timeout: float = 5.0,
) -> MobileProxyConfig:
    listen = _parse_ip(listen_host, label="listen host")
    target = _parse_ip(target_host, label="target host")
    if not listen.is_loopback:
        raise ConfigError("mobile-proxy listen host must be loopback, usually 127.0.0.1")
    if not (target.is_private or target.is_loopback):
        raise ConfigError("mobile-proxy target host must be private or loopback")
    _validate_port(listen_port, "listen port")
    _validate_port(target_port, "target port")
    if connect_timeout <= 0 or connect_timeout > 30:
        raise ConfigError("mobile-proxy timeout must be between 0 and 30 seconds")
    return MobileProxyConfig(str(listen), listen_port, str(target), target_port, connect_timeout)


def _build_proxy_handler(config: MobileProxyConfig) -> type[socketserver.BaseRequestHandler]:
    class ProxyHandler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            upstream = socket.create_connection((config.target_host, config.target_port), timeout=config.connect_timeout)
            try:
                self.request.setblocking(False)
                upstream.setblocking(False)
                sockets = [self.request, upstream]
                while sockets:
                    readable, _, exceptional = select.select(sockets, [], sockets, 30)
                    if exceptional:
                        break
                    if not readable:
                        continue
                    for source in readable:
                        try:
                            chunk = source.recv(65536)
                        except OSError:
                            return
                        if not chunk:
                            return
                        destination = upstream if source is self.request else self.request
                        destination.sendall(chunk)
            finally:
                upstream.close()
    return ProxyHandler


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _tcp_check(host: str, port: int, *, timeout: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "error": None}
    except OSError as exc:
        return {"ok": False, "error": exc.__class__.__name__}


def _bind_check(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return {"ok": True, "error": None}
    except OSError as exc:
        return {"ok": False, "error": exc.__class__.__name__}


def _http_health_check(host: str, port: int, *, timeout: float) -> dict[str, Any]:
    url = f"http://{host}:{port}/healthz"
    try:
        with urlopen(url, timeout=timeout) as response:
            response.read(4096)
            return {"ok": 200 <= response.status < 500, "status": response.status, "error": None}
    except (OSError, URLError) as exc:
        return {"ok": False, "status": None, "error": exc.__class__.__name__}


def _parse_ip(raw: str, *, label: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        return ipaddress.ip_address(raw)
    except ValueError as exc:
        raise ConfigError(f"mobile-proxy {label} must be an IP address") from exc


def _validate_port(port: int, label: str) -> None:
    if port < 1 or port > 65535:
        raise ConfigError(f"mobile-proxy {label} must be between 1 and 65535")


def _is_loopback(host: str) -> bool:
    return ipaddress.ip_address(host).is_loopback


def _is_private_or_loopback(host: str) -> bool:
    ip = ipaddress.ip_address(host)
    return ip.is_private or ip.is_loopback


def _proxy_next_steps(config: MobileProxyConfig, *, overall: str) -> list[str]:
    if overall == "ready":
        return [f"Proxy is already serving {config.listen_url}; keep Tailscale Serve pointed to http://{config.listen_host}:{config.listen_port}."]
    if overall == "ready_to_start":
        return [
            f"Start proxy: lai-gateway mobile-proxy --target-host {config.target_host} --target-port {config.target_port}",
            f"Point Tailscale Serve to: http://{config.listen_host}:{config.listen_port}",
        ]
    return ["Fix target reachability or free the listen port, then rerun mobile-proxy --check."]


def dump_mobile_proxy_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
