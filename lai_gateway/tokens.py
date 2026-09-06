from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from typing import Any

from .config import DEFAULT_ACCESS_TOKEN_FILE
from .errors import ConfigError

_DEFAULT_TOKEN_BYTES = 32


def default_access_token_path() -> Path:
    return Path(DEFAULT_ACCESS_TOKEN_FILE).expanduser()


def create_gateway_access_token(path: Path | None = None, *, force: bool = False, include_token: bool = False) -> dict[str, Any]:
    target = (path or default_access_token_path()).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() and not force:
        raise ConfigError(f"gateway access token file already exists: {target}")
    token = secrets.token_urlsafe(_DEFAULT_TOKEN_BYTES)
    flags = os.O_WRONLY | os.O_CREAT
    if not force:
        flags |= os.O_EXCL
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(token + "\n")
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    os.chmod(target, 0o600)
    payload: dict[str, Any] = {
        "path": str(target),
        "created": True,
        "mode": token_file_mode(target),
        "token_length": len(token),
        "printed_token": include_token,
    }
    if include_token:
        payload["token"] = token
    return payload


def token_file_mode(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    return f"{mode:04o}"


def check_gateway_access_token_file(path: Path | None = None) -> dict[str, Any]:
    target = (path or default_access_token_path()).expanduser()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"gateway access token file not found: {target}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read gateway access token file: {target}: {exc}") from exc
    token = raw.strip()
    if not token:
        raise ConfigError(f"gateway access token file is empty: {target}")
    if any(ch.isspace() for ch in token):
        raise ConfigError("gateway access token must be a single bearer token without whitespace")
    if len(token) < 32:
        raise ConfigError("gateway access token must be at least 32 characters")
    mode = token_file_mode(target)
    if os.name == "posix" and stat.S_IMODE(target.stat().st_mode) & 0o077:
        raise ConfigError(f"gateway access token file permissions must be 0600, got {mode}: {target}")
    return {"path": str(target), "ok": True, "mode": mode, "token_length": len(token)}
