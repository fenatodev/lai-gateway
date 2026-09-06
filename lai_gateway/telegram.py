from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from .access import collect_mobile_access
from .config import GatewayConfig
from .doctor import collect_doctor
from urllib.request import Request, urlopen

from . import __version__
from .errors import ConfigError, GatewayError
from .tokens import token_file_mode

DEFAULT_TELEGRAM_TOKEN_FILE = "~/.config/lai-gateway/telegram-bot-token"
_MAX_MESSAGE_CHARS = 4096
_MAX_DISCOVER_LIMIT = 20


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
    receive_enabled = _env_receive_enabled()
    token = _inspect_token(path)
    chat_ok = bool(str(configured_chat).strip())
    overall = "ready" if token["ok"] and chat_ok and send_enabled else "needs_config"
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-preflight",
        "overall": overall,
        "send_enabled": send_enabled,
        "receive_enabled": receive_enabled,
        "network_call": False,
        "token_file": token,
        "chat_id_configured": chat_ok,
        "chat_id_source": "argument" if chat_id else "environment",
        "security": {
            "token_printed": False,
            "requires_enable_flag": True,
            "requires_receive_flag_for_updates": True,
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
            f"receive_enabled: {str(payload.get('receive_enabled', False)).lower()}",
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
    payload = _open_json(request, opener=opener, timeout=10, label="telegram send")
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



def discover_telegram_chats(
    *,
    token_file: Path | None = None,
    enable_receive: bool | None = None,
    limit: int = 10,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Fetch recent Telegram updates once and return redacted chat candidates."""
    receive_enabled = _env_receive_enabled() if enable_receive is None else enable_receive
    if not receive_enabled:
        raise ConfigError("telegram discover-chat requires LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE=1")
    if limit < 1 or limit > _MAX_DISCOVER_LIMIT:
        raise ConfigError(f"telegram discover-chat limit must be between 1 and {_MAX_DISCOVER_LIMIT}")
    path = (token_file or default_telegram_token_path()).expanduser()
    token_info = _inspect_token(path)
    if not token_info["ok"]:
        raise ConfigError(f"telegram token file is not ready: {token_info['detail']}")
    token = _read_token(path)
    params = urlencode({"limit": str(limit), "timeout": "0", "allowed_updates": '["message","channel_post"]'})
    request = Request(f"https://api.telegram.org/bot{token}/getUpdates?{params}", method="GET")
    raw = _open_json(request, opener=opener, timeout=10, label="telegram getUpdates")
    if not raw.get("ok"):
        raise GatewayError("telegram getUpdates was rejected by Telegram")
    updates = raw.get("result") if isinstance(raw.get("result"), list) else []
    chats = _extract_redacted_chats(updates)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-discover-chat",
        "ok": True,
        "network_call": True,
        "receive_enabled": True,
        "candidate_count": len(chats),
        "chats": chats,
        "security": {
            "token_printed": False,
            "message_text_redacted": True,
            "requires_receive_flag": True,
            "webhook_exposed": False,
            "harness_write_authority": False,
        },
    }


def render_telegram_discover(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway telegram discover-chat: {payload['candidate_count']} candidate(s)",
        f"version: {payload['version']}",
        "network_call: true",
        "message_text_redacted: true",
        "chats:",
    ]
    for chat in payload["chats"]:
        label = chat.get("label") or chat.get("type") or "chat"
        lines.append(f"  - chat_id: {chat['id']} ({label})")
    if not payload["chats"]:
        lines.append("  none")
    lines.append("Use LAI_GATEWAY_TELEGRAM_CHAT_ID=<chat_id> after confirming the target chat.")
    return "\n".join(lines)


def build_mobile_access_telegram_text(*, port: int, bind: str = "127.0.0.1") -> str:
    mobile = collect_mobile_access(port=port, bind=bind)
    recommended = mobile.get("recommended_url") or "not detected"
    kind = mobile.get("recommended_kind") or "unknown"
    lines = [
        "lai-gateway mobile access",
        f"version: {__version__}",
        f"recommended: {recommended}",
        f"kind: {kind}",
        "QR is available in the gateway UI and contains only the URL.",
    ]
    link = next((item for item in mobile.get("links", []) if item.get("recommended")), None)
    if link and link.get("lai_bridge_apply"):
        lines.append("bridge:")
        lines.append(link["lai_bridge_apply"])
    if mobile.get("warnings"):
        lines.append("warnings:")
        for warning in mobile["warnings"][:3]:
            lines.append(f"- {warning}")
    return "\n".join(lines)[:_MAX_MESSAGE_CHARS]


def notify_mobile_access(
    *,
    port: int,
    bind: str = "127.0.0.1",
    token_file: Path | None = None,
    chat_id: str | None = None,
    enable_send: bool | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    text = build_mobile_access_telegram_text(port=port, bind=bind)
    payload = send_telegram_message(
        text=text,
        token_file=token_file,
        chat_id=chat_id,
        enable_send=enable_send,
        opener=opener,
    )
    payload = dict(payload)
    payload["operation"] = "telegram-notify-mobile"
    payload["mobile_url_included"] = True
    payload["pair_token_included"] = False
    payload["harness_token_included"] = False
    return payload



def build_gateway_status_telegram_text(config: GatewayConfig) -> str:
    doctor = collect_doctor(config)
    checks = doctor.get("checks", [])
    lines = [
        "lai-gateway status",
        f"version: {__version__}",
        f"overall: {doctor.get('overall')}",
        f"harness: {config.harness_url}",
        f"access: {config.access_mode}",
    ]
    for check in checks[:8]:
        name = check.get("name", "check")
        status = check.get("status", "unknown")
        detail = str(check.get("detail", ""))
        if "token" in name.lower():
            detail = "redacted"
        lines.append(f"- {name}: {status} {detail}".strip())
    return "\n".join(lines)[:_MAX_MESSAGE_CHARS]


def notify_gateway_status(
    *,
    config: GatewayConfig,
    token_file: Path | None = None,
    chat_id: str | None = None,
    enable_send: bool | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    text = build_gateway_status_telegram_text(config)
    payload = send_telegram_message(
        text=text,
        token_file=token_file,
        chat_id=chat_id,
        enable_send=enable_send,
        opener=opener,
    )
    payload = dict(payload)
    payload["operation"] = "telegram-notify-status"
    payload["status_included"] = True
    payload["token_included"] = False
    payload["harness_write_authority"] = False
    return payload


def _extract_redacted_chats(updates: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for update in updates:
        if not isinstance(update, dict):
            continue
        message = update.get("message") if isinstance(update.get("message"), dict) else update.get("channel_post")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat")
        if not isinstance(chat, dict) or "id" not in chat:
            continue
        chat_id = str(chat["id"])
        if chat_id in seen:
            continue
        seen.add(chat_id)
        label = chat.get("title") or chat.get("username") or chat.get("type") or "chat"
        out.append({
            "id": chat["id"],
            "type": chat.get("type"),
            "label": str(label),
            "message_text_redacted": True,
        })
    return out


def _open_json(request: Request, *, opener: Callable[..., Any], timeout: int, label: str) -> dict[str, Any]:
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise GatewayError(f"{label} failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise GatewayError(f"{label} failed: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayError(f"{label} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise GatewayError(f"{label} returned non-object JSON")
    return payload


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


def _env_receive_enabled() -> bool:
    return os.environ.get("LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE", "0").strip().lower() in {"1", "true", "yes", "on"}
