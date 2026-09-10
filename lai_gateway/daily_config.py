from __future__ import annotations

import ipaddress
import json
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .errors import ConfigError

DEFAULT_DAILY_CONFIG_FILE = "~/.config/lai-gateway/daily.json"
_SCHEMA_VERSION = 1
_SANDBOX_IMAGE_RE = re.compile(r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*(?::[A-Za-z0-9_.-]+)?@sha256:[0-9a-f]{64}$")
_BARE_EXECUTABLE_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")


@dataclass(frozen=True)
class DailyConfig:
    candidate_ip: str
    phone_url: str | None = None
    port: int = 8787
    proxy_port: int = 18787
    harness_repo: str | None = None
    sandbox_image: str | None = None
    sandbox_python: str | None = None
    path: Path | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "candidate_ip": self.candidate_ip,
            "phone_url": self.phone_url,
            "port": self.port,
            "proxy_port": self.proxy_port,
            "harness_repo": self.harness_repo,
            "sandbox_image": self.sandbox_image,
            "sandbox_python": self.sandbox_python,
            "path": str(self.path) if self.path else None,
        }


def default_daily_config_path() -> Path:
    return Path(os.path.expanduser(DEFAULT_DAILY_CONFIG_FILE))


def resolve_daily_config_path(path: str | Path | None = None) -> Path:
    return Path(os.path.expanduser(str(path))) if path else default_daily_config_path()


def resolve_effective_daily_config_path(path: str | Path | None = None) -> Path:
    return resolve_daily_config_path(path or os.environ.get("LAI_GATEWAY_DAILY_CONFIG"))


def validate_daily_config(
    *,
    candidate_ip: str,
    phone_url: str | None = None,
    port: int | str = 8787,
    proxy_port: int | str = 18787,
    harness_repo: str | None = None,
    sandbox_image: str | None = None,
    sandbox_python: str | None = None,
    path: Path | None = None,
) -> DailyConfig:
    try:
        parsed_ip = ipaddress.ip_address(candidate_ip)
    except ValueError as exc:
        raise ConfigError("daily candidate_ip must be a valid IP address") from exc
    if not parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_multicast or parsed_ip.is_unspecified:
        raise ConfigError("daily candidate_ip must be a concrete private non-loopback address")
    resolved_port = _validate_port(port, "daily port")
    resolved_proxy_port = _validate_port(proxy_port, "daily proxy_port")
    normalized_url = _validate_phone_url(phone_url, expected_port=resolved_port) if phone_url else None
    normalized_repo = _normalize_harness_repo(harness_repo)
    normalized_sandbox_image = _normalize_sandbox_image(sandbox_image)
    normalized_sandbox_python = _normalize_sandbox_python(sandbox_python)
    return DailyConfig(
        candidate_ip=str(parsed_ip),
        phone_url=normalized_url,
        port=resolved_port,
        proxy_port=resolved_proxy_port,
        harness_repo=normalized_repo,
        sandbox_image=normalized_sandbox_image,
        sandbox_python=normalized_sandbox_python,
        path=path,
    )


def write_daily_config(
    config: DailyConfig,
    *,
    path: str | Path | None = None,
    force: bool = True,
) -> Path:
    target = resolve_daily_config_path(path or config.path)
    if target.exists() and not force:
        raise ConfigError(f"daily config file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    document = config.public_dict()
    document.pop("path", None)
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.chmod(tmp, 0o600)
    tmp.replace(target)
    os.chmod(target, 0o600)
    return target


def read_daily_config(*, path: str | Path | None = None) -> DailyConfig:
    target = resolve_effective_daily_config_path(path)
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"daily config file not found: {target}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read daily config file: {target}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"daily config file is not valid JSON: {target}") from exc
    if not isinstance(data, dict):
        raise ConfigError("daily config file must contain a JSON object")
    if data.get("schema_version") != _SCHEMA_VERSION:
        raise ConfigError("daily config file has an unsupported schema_version")
    config = validate_daily_config(
        candidate_ip=str(data.get("candidate_ip") or ""),
        phone_url=data.get("phone_url"),
        port=data.get("port", 8787),
        proxy_port=data.get("proxy_port", 18787),
        harness_repo=data.get("harness_repo"),
        sandbox_image=data.get("sandbox_image"),
        sandbox_python=data.get("sandbox_python"),
        path=target,
    )
    _check_daily_file_mode(target)
    return config


def collect_daily_config(*, path: str | Path | None = None) -> dict[str, Any]:
    target = resolve_effective_daily_config_path(path)
    try:
        config = read_daily_config(path=target)
    except ConfigError as exc:
        return {
            "product": "lai-gateway",
            "version": __version__,
            "operation": "daily-config",
            "overall": "needs_config",
            "path": str(target),
            "config": None,
            "error": str(exc),
            "security": _security_payload(),
        }
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "daily-config",
        "overall": "ready",
        "path": str(target),
        "config": config.public_dict(),
        "security": _security_payload(),
    }


def render_daily_config(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway daily-config: {payload['overall']}",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        "prints_tokens: false",
    ]
    config = payload.get("config") or {}
    if config:
        lines.append(f"candidate_ip: {config['candidate_ip']}")
        lines.append(f"port: {config['port']}")
        lines.append(f"proxy_port: {config['proxy_port']}")
        if config.get("phone_url"):
            lines.append(f"phone_url: {config['phone_url']}")
        if config.get("harness_repo"):
            lines.append(f"harness_repo: {config['harness_repo']}")
        if config.get("sandbox_image"):
            lines.append("sandbox_image: configured")
        if config.get("sandbox_python"):
            lines.append(f"sandbox_python: {config['sandbox_python']}")
        lines.append("daily_command:")
        lines.append("  lai-gateway-daily --show-pair")
    elif payload.get("error"):
        lines.append(f"error: {payload['error']}")
        lines.append("configure:")
        lines.append("  lai-gateway daily-config set --candidate-ip <wsl-ip> --phone-url http://<tailscale-magicdns>:8787/")
    return "\n".join(lines)


def shell_exports(config: DailyConfig) -> str:
    values: dict[str, str] = {
        "LAI_GATEWAY_MOBILE_IP": config.candidate_ip,
        "LAI_GATEWAY_MOBILE_PORT": str(config.port),
        "LAI_GATEWAY_MOBILE_PROXY_PORT": str(config.proxy_port),
    }
    if config.phone_url:
        values["LAI_GATEWAY_PHONE_URL"] = config.phone_url
    if config.harness_repo:
        values["LAI_HARNESS_REPO_DIR"] = config.harness_repo
    if config.sandbox_image:
        values["LAI_REMOTE_SANDBOX_IMAGE"] = config.sandbox_image
    if config.sandbox_python:
        values["LAI_REMOTE_SANDBOX_PYTHON"] = config.sandbox_python
    return "\n".join(f"export {key}={shlex.quote(value)}" for key, value in values.items()) + "\n"


def _validate_port(value: int | str, label: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} must be an integer port") from exc
    if port < 1 or port > 65535:
        raise ConfigError(f"{label} must be between 1 and 65535")
    return port


def _validate_phone_url(phone_url: str, *, expected_port: int) -> str:
    parsed = urlparse(phone_url)
    if parsed.scheme != "http":
        raise ConfigError("daily phone_url must use http:// inside the private tailnet")
    if parsed.username or parsed.password:
        raise ConfigError("daily phone_url must not include credentials")
    if not parsed.hostname:
        raise ConfigError("daily phone_url must include a hostname")
    if parsed.port != expected_port:
        raise ConfigError("daily phone_url must include the configured mobile port")
    if parsed.query or parsed.fragment:
        raise ConfigError("daily phone_url must not include query or fragment")
    path = parsed.path or "/"
    if path != "/":
        raise ConfigError("daily phone_url must point to the gateway root path")
    return f"http://{parsed.netloc}/"


def _normalize_harness_repo(harness_repo: str | None) -> str | None:
    if not harness_repo:
        return None
    expanded = os.path.expanduser(harness_repo)
    if "\n" in expanded or "\x00" in expanded:
        raise ConfigError("daily harness_repo must be a single path")
    return expanded


def _normalize_sandbox_image(sandbox_image: str | None) -> str | None:
    if not sandbox_image:
        return None
    image = sandbox_image.strip()
    if not _SANDBOX_IMAGE_RE.fullmatch(image):
        raise ConfigError("daily sandbox_image must be digest-pinned as <repository>[:tag]@sha256:<64 lowercase hex>")
    return image


def _normalize_sandbox_python(sandbox_python: str | None) -> str | None:
    if not sandbox_python:
        return None
    executable = sandbox_python.strip()
    if not _BARE_EXECUTABLE_RE.fullmatch(executable):
        raise ConfigError("daily sandbox_python must be a bare executable name")
    return executable


def _check_daily_file_mode(path: Path) -> None:
    try:
        mode = path.stat().st_mode & 0o777
    except OSError as exc:
        raise ConfigError(f"cannot inspect daily config file: {path}: {exc}") from exc
    if mode != 0o600:
        raise ConfigError(f"daily config file permissions must be 0600, got {mode:04o}: {path}")


def _security_payload() -> dict[str, bool]:
    return {
        "contains_tokens": False,
        "prints_tokens": False,
        "starts_server": False,
        "modifies_files": False,
    }
