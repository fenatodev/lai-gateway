from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import __version__
from .errors import ConfigError, GatewayError
from .tokens import token_file_mode

DEFAULT_TELEGRAM_TOKEN_FILE = "~/.config/lai-gateway/telegram-bot-token"
_MAX_MESSAGE_CHARS = 4096


def default_telegram_token_path() -> Path:
    return Path(DEFAULT_TELEGRAM_TOKEN_FILE).expanduser()


def collect_telegram_preflight(
    *,
    token_file: Path | None = None,
    chat_id: str | None = None,
    enable_send: bool | None = None,
) -> dict[str, Any]:
    path = (token_file or default_telegram_token_path()).expanduser()
    configured_chat = chat_id if chat_id is not None else os.environ.get("LAI_GATEWAY_TELEGRAM_CHAT_ID", "")
    send_enabled = _env_send_enabled() if enable_send is None else enable_send
    token = _inspect_token(path)
    chat_ok = bool(str(configured_chat).strip())
    overall = "ready" if token["ok"] and chat_ok and send_enabled else "needs_config"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-preflight",
        "overall": overall,
        "send_enabled": send_enabled,
        "network_call": False,
        "token_file": token,
        "chat_id_configured": chat_ok,
        "chat_id_source": "argument" if chat_id else "environment",
        "security": {
            "token_printed": False,
            "requires_enable_flag": True,
            "outbound_only": True,
            "webhook_exposed": False,
            "harness_write_authority": False,
        },
    }


def render_telegram_preflight(payload: dict[str, Any]) -> str:
    token = payload["token_file"]
    return "\n".join(
        [
            f"lai-gateway telegram: {payload['overall']}",
            f"version: {payload['version']}",
            f"send_enabled: {str(payload['send_enabled']).lower()}",
            f"token_file: {token['status']} ({token['path']})",
            f"chat_id_configured: {str(payload['chat_id_configured']).lower()}",
            "network_call: false",
            "webhook_exposed: false",
        ]
    )


def send_telegram_message(
    *,
    text: str,
    token_file: Path | None = None,
    chat_id: str | None = None,
    enable_send: bool | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    preflight = collect_telegram_preflight(token_file=token_file, chat_id=chat_id, enable_send=enable_send)
    if not preflight["send_enabled"]:
        raise ConfigError("telegram send requires LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1")
    if not preflight["token_file"]["ok"]:
        raise ConfigError(f"telegram token file is not ready: {preflight['token_file']['detail']}")
    target_chat = str(chat_id if chat_id is not None else os.environ.get("LAI_GATEWAY_TELEGRAM_CHAT_ID", "")).strip()
    if not target_chat:
        raise ConfigError("telegram chat id is required")
    if not text or len(text) > _MAX_MESSAGE_CHARS:
        raise ConfigError("telegram message text must be between 1 and 4096 characters")
    token = _read_token((token_file or default_telegram_token_path()).expanduser())
    data = urlencode({"chat_id": target_chat, "text": text}).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        method="POST",
    )
    try:
        with opener(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise GatewayError(f"telegram send failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise GatewayError(f"telegram send failed: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayError("telegram send returned invalid JSON") from exc
    if not payload.get("ok"):
        raise GatewayError("telegram send was rejected by Telegram")
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-send-message",
        "ok": True,
        "message_id": result.get("message_id"),
        "chat_id_configured": True,
        "token_printed": False,
        "webhook_exposed": False,
    }


def _inspect_token(path: Path) -> dict[str, Any]:
    exists = path.exists()
    try:
        token = _read_token(path)
        mode = token_file_mode(path)
        _require_0600(path)
    except ConfigError as exc:
        return {"path": str(path), "exists": exists, "ok": False, "status": "invalid" if exists else "missing", "detail": str(exc)}
    return {"path": str(path), "exists": True, "ok": True, "status": "ready", "mode": mode, "token_length": len(token)}


def _read_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ConfigError(f"telegram token file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read telegram token file: {path}: {exc}") from exc
    if not token or any(ch.isspace() for ch in token):
        raise ConfigError("telegram token must be a single token without whitespace")
    if len(token) < 16:
        raise ConfigError("telegram token is too short")
    return token


def _require_0600(path: Path) -> None:
    if os.name == "posix" and int(token_file_mode(path), 8) & 0o077:
        raise ConfigError(f"telegram token file permissions must be 0600: {path}")


def _env_send_enabled() -> bool:
    return os.environ.get("LAI_GATEWAY_TELEGRAM_ENABLE_SEND", "0").strip().lower() in {"1", "true", "yes", "on"}
