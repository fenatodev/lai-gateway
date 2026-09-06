from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import ConfigError

DEFAULT_HARNESS_URL = "http://127.0.0.1:8765"
DEFAULT_TOKEN_FILE = "~/.config/lai/control-api-key"
DEFAULT_ACCESS_TOKEN_FILE = "~/.config/lai-gateway/access-token"
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_TIMEOUT_SECONDS = 10.0
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class GatewayConfig:
    harness_url: str
    token_file: Path
    bind: str = DEFAULT_BIND
    port: int = DEFAULT_PORT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    private_bind_enabled: bool = False
    access_token_file: Path | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "GatewayConfig":
        values = env if env is not None else os.environ
        private_bind_enabled = _parse_bool(values.get("LAI_GATEWAY_PRIVATE_BIND", "0"), "LAI_GATEWAY_PRIVATE_BIND")
        harness_url = values.get("LAI_GATEWAY_HARNESS_URL", DEFAULT_HARNESS_URL)
        token_file = Path(values.get("LAI_GATEWAY_TOKEN_FILE", DEFAULT_TOKEN_FILE)).expanduser()
        bind = values.get("LAI_GATEWAY_BIND", DEFAULT_BIND)
        port = _parse_port(values.get("LAI_GATEWAY_PORT", str(DEFAULT_PORT)), "LAI_GATEWAY_PORT")
        timeout = _parse_timeout(values.get("LAI_GATEWAY_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        access_token_file = _access_token_file(values, private_bind_enabled)
        return cls(
            harness_url=normalize_loopback_http_url(harness_url),
            token_file=token_file,
            bind=validate_gateway_bind(bind, private_bind_enabled=private_bind_enabled),
            port=port,
            timeout_seconds=timeout,
            private_bind_enabled=private_bind_enabled,
            access_token_file=access_token_file,
        )

    @property
    def access_mode(self) -> str:
        return "private-token" if self.private_bind_enabled else "loopback"

    def public_dict(self) -> dict[str, object]:
        return {
            "harness_url": self.harness_url,
            "token_file": str(self.token_file),
            "bind": self.bind,
            "port": self.port,
            "timeout_seconds": self.timeout_seconds,
            "access_mode": self.access_mode,
            "private_bind_enabled": self.private_bind_enabled,
            "access_token_file": str(self.access_token_file) if self.access_token_file is not None else None,
        }


def read_control_token(token_file: Path) -> str:
    return _read_single_token(token_file, label="control token")


def read_gateway_access_token(token_file: Path) -> str:
    token = _read_single_token(token_file, label="gateway access token")
    if len(token) < 16:
        raise ConfigError("gateway access token must be at least 16 characters")
    return token


def _read_single_token(token_file: Path, *, label: str) -> str:
    try:
        token = token_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ConfigError(f"{label} file not found: {token_file}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read {label} file: {token_file}: {exc}") from exc
    if not token:
        raise ConfigError(f"{label} file is empty: {token_file}")
    if any(ch.isspace() for ch in token):
        raise ConfigError(f"{label} must be a single bearer token without whitespace")
    return token


def normalize_loopback_http_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme != "http":
        raise ConfigError("harness URL must use http:// loopback; TLS belongs outside this local hop")
    if parsed.username or parsed.password:
        raise ConfigError("harness URL must not include credentials")
    if parsed.hostname not in _LOOPBACK_HOSTS:
        raise ConfigError("harness URL must point to loopback only")
    if parsed.query or parsed.fragment:
        raise ConfigError("harness URL must not include query or fragment")
    if not parsed.port:
        raise ConfigError("harness URL must include an explicit port")
    _parse_port(str(parsed.port), "harness URL port")
    path = parsed.path.rstrip("/")
    if path:
        raise ConfigError("harness URL must be an origin, not a path")
    host = parsed.hostname or "127.0.0.1"
    if host == "::1":
        return f"http://[::1]:{parsed.port}"
    return f"http://{host}:{parsed.port}"


def validate_loopback_bind(bind: str) -> str:
    return validate_gateway_bind(bind, private_bind_enabled=False)


def validate_gateway_bind(bind: str, *, private_bind_enabled: bool) -> str:
    if bind in _LOOPBACK_HOSTS:
        return bind
    if not private_bind_enabled:
        raise ConfigError("gateway bind must stay loopback-only unless LAI_GATEWAY_PRIVATE_BIND=1")
    try:
        address = ipaddress.ip_address(bind)
    except ValueError as exc:
        raise ConfigError("private gateway bind must be a concrete private IP address") from exc
    if address.is_unspecified or address.is_multicast or address.is_reserved or address.is_global:
        raise ConfigError("private gateway bind must not be wildcard, multicast, reserved, or public")
    if not address.is_private:
        raise ConfigError("private gateway bind must be a private LAN address")
    return bind


def _access_token_file(values: dict[str, str], private_bind_enabled: bool) -> Path | None:
    raw = values.get("LAI_GATEWAY_ACCESS_TOKEN_FILE")
    if raw:
        return Path(raw).expanduser()
    if private_bind_enabled:
        return Path(DEFAULT_ACCESS_TOKEN_FILE).expanduser()
    return None


def _parse_bool(value: str, label: str) -> bool:
    lowered = value.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ConfigError(f"{label} must be a boolean flag")


def _parse_port(value: str, label: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ConfigError(f"{label} must be an integer port") from exc
    if not 1 <= port <= 65535:
        raise ConfigError(f"{label} must be between 1 and 65535")
    return port


def _parse_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise ConfigError("LAI_GATEWAY_TIMEOUT_SECONDS must be numeric") from exc
    if timeout <= 0 or timeout > 60:
        raise ConfigError("LAI_GATEWAY_TIMEOUT_SECONDS must be > 0 and <= 60")
    return timeout
