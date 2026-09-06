from __future__ import annotations

import json
import os
import secrets
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import DEFAULT_ACCESS_TOKEN_FILE, DEFAULT_PAIR_TOKEN_FILE
from .errors import ConfigError

_DEFAULT_TOKEN_BYTES = 32
_DEFAULT_PAIR_TTL_SECONDS = 600
_MIN_PAIR_TTL_SECONDS = 60
_MAX_PAIR_TTL_SECONDS = 3600


def default_access_token_path() -> Path:
    return Path(DEFAULT_ACCESS_TOKEN_FILE).expanduser()


def default_pair_token_path() -> Path:
    return Path(DEFAULT_PAIR_TOKEN_FILE).expanduser()


def create_gateway_access_token(path: Path | None = None, *, force: bool = False, include_token: bool = False) -> dict[str, Any]:
    target = (path or default_access_token_path()).expanduser()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() and not force:
        raise ConfigError(f"gateway access token file already exists: {target}")
    token = secrets.token_urlsafe(_DEFAULT_TOKEN_BYTES)
    _write_secret_file(target, token + "\n", force=force)
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


def create_gateway_pairing_token(
    path: Path | None = None,
    *,
    ttl_seconds: int = _DEFAULT_PAIR_TTL_SECONDS,
    force: bool = False,
    include_token: bool = False,
    ui_url: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    target = (path or default_pair_token_path()).expanduser()
    ttl = _validate_pair_ttl(ttl_seconds)
    current = _utc(now)
    expires = current + timedelta(seconds=ttl)
    token = secrets.token_urlsafe(_DEFAULT_TOKEN_BYTES)
    document = {
        "schema_version": 1,
        "kind": "lai-gateway-pair-token",
        "token": token,
        "created_at": _format_time(current),
        "expires_at": _format_time(expires),
    }
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists() and not force:
        raise ConfigError(f"gateway pairing token file already exists: {target}")
    _write_secret_file(target, json.dumps(document, sort_keys=True) + "\n", force=force)
    payload: dict[str, Any] = {
        "path": str(target),
        "created": True,
        "mode": token_file_mode(target),
        "ttl_seconds": ttl,
        "expires_at": document["expires_at"],
        "token_length": len(token),
        "printed_token": include_token,
    }
    if ui_url is not None:
        payload["ui_url"] = ui_url
    if include_token:
        payload["token"] = token
    return payload


def check_gateway_pairing_token_file(path: Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    target = (path or default_pair_token_path()).expanduser()
    document = _read_pair_document(target)
    token = _pair_token_from_document(document)
    expires = _parse_time(str(document["expires_at"]))
    seconds_remaining = int((expires - _utc(now)).total_seconds())
    expired = seconds_remaining <= 0
    mode = token_file_mode(target)
    _require_private_file_mode(target, label="gateway pairing token file")
    if expired:
        raise ConfigError(f"gateway pairing token expired at {document['expires_at']}: {target}")
    return {
        "path": str(target),
        "ok": True,
        "mode": mode,
        "expires_at": document["expires_at"],
        "seconds_remaining": seconds_remaining,
        "token_length": len(token),
    }


def read_valid_gateway_pairing_token(path: Path, *, now: datetime | None = None) -> str:
    check_gateway_pairing_token_file(path, now=now)
    document = _read_pair_document(path.expanduser())
    return _pair_token_from_document(document)


def revoke_gateway_pairing_token(path: Path | None = None) -> dict[str, Any]:
    target = (path or default_pair_token_path()).expanduser()
    try:
        target.unlink()
    except FileNotFoundError:
        return {"path": str(target), "revoked": False}
    return {"path": str(target), "revoked": True}


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
    _require_private_file_mode(target, label="gateway access token file")
    return {"path": str(target), "ok": True, "mode": mode, "token_length": len(token)}


def _write_secret_file(target: Path, content: str, *, force: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT
    if force:
        flags |= os.O_TRUNC
    else:
        flags |= os.O_EXCL
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    os.chmod(target, 0o600)


def _read_pair_document(target: Path) -> dict[str, Any]:
    _require_private_file_mode(target, label="gateway pairing token file")
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"gateway pairing token file not found: {target}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read gateway pairing token file: {target}: {exc}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"gateway pairing token file is not valid JSON: {target}") from exc
    if not isinstance(document, dict):
        raise ConfigError("gateway pairing token file must contain a JSON object")
    if document.get("schema_version") != 1 or document.get("kind") != "lai-gateway-pair-token":
        raise ConfigError("gateway pairing token file has an unsupported schema")
    return document


def _pair_token_from_document(document: dict[str, Any]) -> str:
    token = document.get("token")
    if not isinstance(token, str) or not token:
        raise ConfigError("gateway pairing token file does not contain a token")
    if any(ch.isspace() for ch in token):
        raise ConfigError("gateway pairing token must be a single bearer token without whitespace")
    if len(token) < 32:
        raise ConfigError("gateway pairing token must be at least 32 characters")
    if not isinstance(document.get("expires_at"), str):
        raise ConfigError("gateway pairing token file does not contain expires_at")
    return token


def _require_private_file_mode(target: Path, *, label: str) -> None:
    try:
        current_mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError as exc:
        raise ConfigError(f"{label} not found: {target}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot inspect {label}: {target}: {exc}") from exc
    if os.name == "posix" and current_mode & 0o077:
        raise ConfigError(f"{label} permissions must be 0600, got {current_mode:04o}: {target}")


def _validate_pair_ttl(ttl_seconds: int) -> int:
    if not _MIN_PAIR_TTL_SECONDS <= ttl_seconds <= _MAX_PAIR_TTL_SECONDS:
        raise ConfigError(
            f"gateway pairing token ttl must be between {_MIN_PAIR_TTL_SECONDS} and {_MAX_PAIR_TTL_SECONDS} seconds"
        )
    return ttl_seconds


def _utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as exc:
        raise ConfigError("gateway pairing token expires_at is not a valid timestamp") from exc
