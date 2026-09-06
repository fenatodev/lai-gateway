from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import ConfigError

DEFAULT_HARNESS_URL = "http://127.0.0.1:8765"
DEFAULT_TOKEN_FILE = "~/.config/lai/control-api-key"
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_TIMEOUT_SECONDS = 10.0
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class GatewayConfig:
    harness_url: str
    token_file: Path
    bind: str = DEFAULT_BIND
    port: int = DEFAULT_PORT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "GatewayConfig":
        values = env if env is not None else os.environ
        harness_url = values.get("LAI_GATEWAY_HARNESS_URL", DEFAULT_HARNESS_URL)
        token_file = Path(values.get("LAI_GATEWAY_TOKEN_FILE", DEFAULT_TOKEN_FILE)).expanduser()
        bind = values.get("LAI_GATEWAY_BIND", DEFAULT_BIND)
        port = _parse_port(values.get("LAI_GATEWAY_PORT", str(DEFAULT_PORT)), "LAI_GATEWAY_PORT")
        timeout = _parse_timeout(values.get("LAI_GATEWAY_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        config = cls(
            harness_url=normalize_loopback_http_url(harness_url),
            token_file=token_file,
            bind=validate_loopback_bind(bind),
            port=port,
            timeout_seconds=timeout,
        )
        return config

    def public_dict(self) -> dict[str, object]:
        return {
            "harness_url": self.harness_url,
            "token_file": str(self.token_file),
            "bind": self.bind,
            "port": self.port,
            "timeout_seconds": self.timeout_seconds,
        }


def read_control_token(token_file: Path) -> str:
    try:
        token = token_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ConfigError(f"control token file not found: {token_file}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read control token file: {token_file}: {exc}") from exc
    if not token:
        raise ConfigError(f"control token file is empty: {token_file}")
    if any(ch.isspace() for ch in token):
        raise ConfigError("control token must be a single bearer token without whitespace")
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
    if bind not in _LOOPBACK_HOSTS:
        raise ConfigError("gateway bind must stay loopback-only in this MVP")
    return bind


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
