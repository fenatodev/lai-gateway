from __future__ import annotations

import json
import os
import re
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
DEFAULT_TELEGRAM_CHAT_FILE = "~/.config/lai-gateway/telegram-chat-id"
_MAX_MESSAGE_CHARS = 4096
_MAX_DISCOVER_LIMIT = 20
_TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")
_TELEGRAM_CHAT_ID_RE = re.compile(r"^-?\d{1,20}$")


def default_telegram_token_path() -> Path:
    return Path(DEFAULT_TELEGRAM_TOKEN_FILE).expanduser()


def default_telegram_chat_path() -> Path:
    return Path(DEFAULT_TELEGRAM_CHAT_FILE).expanduser()


def inspect_telegram_token_file(*, token_file: Path | None = None) -> dict[str, Any]:
    """Return redacted diagnostics for the Telegram bot token file."""
    path = (token_file or default_telegram_token_path()).expanduser()
    return _token_diagnostics(path)


def render_telegram_token_check(payload: dict[str, Any]) -> str:
    lines = [
        f"lai-gateway telegram token-check: {payload['status']}",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"exists: {str(payload['exists']).lower()}",
        f"mode: {payload.get('mode') or 'none'}",
        f"raw_bytes: {payload['raw_bytes']}",
        f"line_count: {payload['line_count']}",
        f"whitespace_count: {payload['whitespace_count']}",
        f"compact_length: {payload['compact_length']}",
        f"token_shape_ok: {str(payload['token_shape_ok']).lower()}",
        f"compact_token_shape_ok: {str(payload['compact_token_shape_ok']).lower()}",
        f"can_repair_whitespace: {str(payload['can_repair_whitespace']).lower()}",
        f"detail: {payload['detail']}",
        "token_printed: false",
    ]
    if payload["can_repair_whitespace"]:
        lines.append("repair: lai-gateway telegram token-repair-whitespace")
    else:
        lines.append("setup: lai-gateway telegram token-set")
    return "\n".join(lines)


def repair_telegram_token_whitespace(*, token_file: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Remove accidental whitespace only when the compact value is a valid bot token shape."""
    path = (token_file or default_telegram_token_path()).expanduser()
    before = _token_diagnostics(path)
    if not before["can_repair_whitespace"]:
        raise ConfigError(f"telegram token whitespace repair is not safe: {before['detail']}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    compact = "".join(raw.split())
    if not dry_run:
        _write_secret_file(path, compact + "\n", force=True)
    after = _token_diagnostics(path) if not dry_run else before
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-token-repair-whitespace",
        "ok": True,
        "dry_run": dry_run,
        "path": str(path),
        "rewritten": not dry_run,
        "before": _public_token_diagnostics(before),
        "after": _public_token_diagnostics(after),
        "token_printed": False,
    }


def render_telegram_token_repair(payload: dict[str, Any]) -> str:
    return "\n".join([
        "lai-gateway telegram token-repair-whitespace: ok",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"dry_run: {str(payload['dry_run']).lower()}",
        f"rewritten: {str(payload['rewritten']).lower()}",
        f"status_after: {payload['after']['status']}",
        "token_printed: false",
    ])


def write_telegram_token_file(*, token: str, token_file: Path | None = None, force: bool = False) -> dict[str, Any]:
    path = (token_file or default_telegram_token_path()).expanduser()
    cleaned = token.strip()
    _validate_telegram_token(cleaned)
    if path.exists() and not force:
        raise ConfigError(f"telegram token file already exists: {path}; pass --force to overwrite")
    _write_secret_file(path, cleaned + "\n", force=True)
    info = _token_diagnostics(path)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-token-set",
        "ok": True,
        "path": str(path),
        "mode": info.get("mode"),
        "token_length": info["compact_length"],
        "token_printed": False,
    }


def render_telegram_token_set(payload: dict[str, Any]) -> str:
    return "\n".join([
        "lai-gateway telegram token-set: ok",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"mode: {payload.get('mode')}",
        f"token_length: {payload['token_length']}",
        "token_printed: false",
    ])


def inspect_telegram_chat_file(*, chat_file: Path | None = None) -> dict[str, Any]:
    path = (chat_file or default_telegram_chat_path()).expanduser()
    exists = path.exists()
    mode = token_file_mode(path) if exists else None
    detail = "telegram chat id file not found"
    chat_id = ""
    if exists:
        try:
            chat_id = _read_chat_id(path)
            detail = "telegram chat id file is ready"
        except ConfigError as exc:
            detail = str(exc)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-chat-check",
        "path": str(path),
        "exists": exists,
        "ok": bool(exists and chat_id),
        "status": "ready" if exists and chat_id else ("missing" if not exists else "invalid"),
        "detail": detail,
        "mode": mode,
        "chat_id_length": len(chat_id),
        "chat_id_printed": False,
    }


def render_telegram_chat_check(payload: dict[str, Any]) -> str:
    return "\n".join([
        f"lai-gateway telegram chat-check: {payload['status']}",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"exists: {str(payload['exists']).lower()}",
        f"mode: {payload.get('mode') or 'none'}",
        f"chat_id_length: {payload['chat_id_length']}",
        f"detail: {payload['detail']}",
        "chat_id_printed: false",
    ])


def write_telegram_chat_file(*, chat_id: str, chat_file: Path | None = None, force: bool = False) -> dict[str, Any]:
    path = (chat_file or default_telegram_chat_path()).expanduser()
    cleaned = chat_id.strip()
    _validate_telegram_chat_id(cleaned)
    if path.exists() and not force:
        raise ConfigError(f"telegram chat id file already exists: {path}; pass --force to overwrite")
    _write_secret_file(path, cleaned + "\n", force=True)
    info = inspect_telegram_chat_file(chat_file=path)
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-chat-set",
        "ok": True,
        "path": str(path),
        "mode": info.get("mode"),
        "chat_id_length": info["chat_id_length"],
        "chat_id_printed": False,
    }


def render_telegram_chat_set(payload: dict[str, Any]) -> str:
    return "\n".join([
        "lai-gateway telegram chat-set: ok",
        f"version: {payload['version']}",
        f"path: {payload['path']}",
        f"mode: {payload.get('mode')}",
        f"chat_id_length: {payload['chat_id_length']}",
        "chat_id_printed: false",
    ])


def get_telegram_bot_info(
    *,
    token_file: Path | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    path = (token_file or default_telegram_token_path()).expanduser()
    token_info = _inspect_token(path)
    if not token_info["ok"]:
        raise ConfigError(f"telegram token file is not ready: {token_info['detail']}")
    token = _read_token(path)
    request = Request(f"https://api.telegram.org/bot{token}/getMe", method="GET")
    raw = _open_json(request, opener=opener, timeout=10, label="telegram getMe")
    if not raw.get("ok"):
        raise GatewayError("telegram getMe was rejected by Telegram")
    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    username = str(result.get("username") or "").strip()
    bot_id = result.get("id")
    if not username or bot_id is None or not result.get("is_bot"):
        raise GatewayError("telegram getMe returned an incomplete bot identity")
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-bot-info",
        "ok": True,
        "network_call": True,
        "bot_id": bot_id,
        "username": username,
        "is_bot": True,
        "security": {
            "token_printed": False,
            "message_text_read": False,
            "webhook_exposed": False,
            "harness_write_authority": False,
        },
    }


def render_telegram_bot_info(payload: dict[str, Any]) -> str:
    username = payload["username"]
    return "\n".join([
        "lai-gateway telegram bot-info: ready",
        f"version: {payload['version']}",
        f"username: @{username}",
        f"bot_id: {payload['bot_id']}",
        "network_call: true",
        "token_printed: false",
        f"next: send /start to @{username}, then run LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE=1 lai-gateway telegram discover-chat",
    ])


def collect_telegram_preflight(
    *,
    token_file: Path | None = None,
    chat_id: str | None = None,
    chat_file: Path | None = None,
    enable_send: bool | None = None,
) -> dict[str, Any]:
    path = (token_file or default_telegram_token_path()).expanduser()
    send_enabled = _env_send_enabled() if enable_send is None else enable_send
    receive_enabled = _env_receive_enabled()
    token = _inspect_token(path)
    chat_detail = "telegram chat id is required"
    chat_source = "none"
    try:
        configured_chat, chat_source = _resolve_chat_id(chat_id=chat_id, chat_file=chat_file)
        chat_ok = bool(configured_chat)
        if chat_ok:
            chat_detail = "telegram chat id is ready"
    except ConfigError as exc:
        configured_chat = ""
        chat_ok = False
        chat_detail = str(exc)
        chat_source = "invalid"
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
        "chat_id_source": chat_source,
        "chat_id_detail": chat_detail,
        "security": {
            "token_printed": False,
            "chat_id_printed": False,
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
            f"chat_id_source: {payload.get('chat_id_source', 'none')}",
            f"chat_id_detail: {payload.get('chat_id_detail', '')}",
            "network_call: false",
            "webhook_exposed: false",
        ]
    )


def send_telegram_message(
    *,
    text: str,
    token_file: Path | None = None,
    chat_id: str | None = None,
    chat_file: Path | None = None,
    enable_send: bool | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    preflight = collect_telegram_preflight(token_file=token_file, chat_id=chat_id, chat_file=chat_file, enable_send=enable_send)
    if not preflight["send_enabled"]:
        raise ConfigError("telegram send requires LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1")
    if not preflight["token_file"]["ok"]:
        raise ConfigError(f"telegram token file is not ready: {preflight['token_file']['detail']}")
    if not preflight["chat_id_configured"]:
        raise ConfigError(preflight.get("chat_id_detail") or "telegram chat id is required")
    target_chat, _ = _resolve_chat_id(chat_id=chat_id, chat_file=chat_file)
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
    if payload["chats"]:
        lines.append("setup commands:")
        for chat in payload["chats"]:
            lines.append(f"  lai-gateway telegram chat-set --chat-id '{chat['id']}' --force")
            lines.append(f"  export LAI_GATEWAY_TELEGRAM_CHAT_ID='{chat['id']}'")
            lines.append("  export LAI_GATEWAY_TELEGRAM_ENABLE_SEND=1")
    else:
        lines.append("Send a message to your bot, then run discover-chat again.")
    return "\n".join(lines)


def build_mobile_access_telegram_text(
    *,
    port: int,
    bind: str = "127.0.0.1",
    candidate_ip: str | None = None,
) -> str:
    effective_bind = candidate_ip or bind
    mobile = collect_mobile_access(
        port=port,
        bind=effective_bind,
        discovered_hosts=[candidate_ip] if candidate_ip else None,
    )
    recommended = mobile.get("recommended_url") or "not detected"
    kind = mobile.get("recommended_kind") or "unknown"
    lines = [
        "lai-gateway mobile access",
        f"version: {__version__}",
        f"recommended: {recommended}",
        f"kind: {kind}",
        *( [f"bridge_target: {candidate_ip}"] if candidate_ip else [] ),
        "QR is available in the gateway UI and contains only the URL.",
    ]
    link = next((item for item in mobile.get("links", []) if item.get("recommended")), None)
    if link and link.get("mobile_bridge_apply_command"):
        lines.append("bridge:")
        lines.append(link["mobile_bridge_apply_command"])
    if mobile.get("warnings"):
        lines.append("warnings:")
        for warning in mobile["warnings"][:3]:
            lines.append(f"- {warning}")
    return "\n".join(lines)[:_MAX_MESSAGE_CHARS]


def notify_mobile_access(
    *,
    port: int,
    bind: str = "127.0.0.1",
    candidate_ip: str | None = None,
    token_file: Path | None = None,
    chat_id: str | None = None,
    enable_send: bool | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    text = build_mobile_access_telegram_text(port=port, bind=bind, candidate_ip=candidate_ip)
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
        raise GatewayError(_render_telegram_http_error(label=label, error=exc)) from exc
    except URLError as exc:
        raise GatewayError(f"{label} failed: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayError(f"{label} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise GatewayError(f"{label} returned non-object JSON")
    return payload


def _render_telegram_http_error(*, label: str, error: HTTPError) -> str:
    description = ""
    try:
        body = error.read(4096).decode("utf-8", errors="replace")
        payload = json.loads(body)
        if isinstance(payload, dict) and isinstance(payload.get("description"), str):
            description = _sanitize_telegram_error_description(payload["description"])
    except (OSError, ValueError, TypeError):
        description = ""

    message = f"{label} failed with HTTP {error.code}"
    if description:
        message += f": {description}"
    hint = _telegram_error_hint(label=label, status=error.code, description=description)
    if hint:
        message += f"; hint: {hint}"
    return message


def _sanitize_telegram_error_description(value: str) -> str:
    text = " ".join(value.split())
    text = re.sub(r"\d{5,}:[A-Za-z0-9_-]{20,}", "[redacted-token]", text)
    return text[:240]


def _telegram_error_hint(*, label: str, status: int, description: str) -> str:
    normalized = description.lower()
    if "chat not found" in normalized or "bot can't initiate conversation" in normalized:
        return (
            "send a message to the bot first, then run "
            "LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE=1 lai-gateway telegram discover-chat "
            "and export the discovered chat id"
        )
    if "bot was blocked by the user" in normalized:
        return "unblock the bot, send it a message, then run telegram discover-chat again"
    if status == 401 or "unauthorized" in normalized:
        return "the bot token was rejected by Telegram; replace it with lai-gateway telegram token-set --force"
    if status == 429 or "too many requests" in normalized:
        return "Telegram rate-limited this request; retry after the server-provided delay"
    if label == "telegram send" and status == 400:
        return "verify the discovered chat id before retrying the notification"
    return ""


def _token_diagnostics(path: Path) -> dict[str, Any]:
    exists = path.exists()
    raw = b""
    text = ""
    mode = None
    detail = "telegram token file not found"
    if exists:
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="replace")
            mode = token_file_mode(path)
        except OSError as exc:
            detail = f"cannot read telegram token file: {path}: {exc}"
    stripped = text.strip()
    compact = "".join(text.split())
    token_shape_ok = bool(_TELEGRAM_TOKEN_RE.fullmatch(stripped))
    compact_token_shape_ok = bool(_TELEGRAM_TOKEN_RE.fullmatch(compact))
    whitespace_count = sum(1 for ch in text if ch.isspace())
    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    permission_ok = True
    if exists and mode is not None and os.name == "posix":
        permission_ok = (int(mode, 8) & 0o077) == 0
    if exists:
        if not raw:
            detail = "telegram token file is empty"
        elif not permission_ok:
            detail = "telegram token file permissions must be 0600"
        elif token_shape_ok:
            detail = "telegram token file is ready"
        elif compact_token_shape_ok and whitespace_count:
            detail = "telegram token contains accidental whitespace and can be repaired safely"
        elif whitespace_count:
            detail = "telegram token contains whitespace and compact value is not a valid bot token shape"
        elif len(stripped) < 16:
            detail = "telegram token is too short"
        else:
            detail = "telegram token does not match the expected bot token shape"
    status = "ready" if exists and permission_ok and token_shape_ok else ("missing" if not exists else "invalid")
    return {
        "product": "lai-gateway",
        "version": __version__,
        "operation": "telegram-token-check",
        "path": str(path),
        "exists": exists,
        "ok": status == "ready",
        "status": status,
        "detail": detail,
        "mode": mode,
        "raw_bytes": len(raw),
        "line_count": line_count,
        "whitespace_count": whitespace_count,
        "compact_length": len(compact),
        "token_shape_ok": token_shape_ok,
        "compact_token_shape_ok": compact_token_shape_ok,
        "can_repair_whitespace": bool(exists and permission_ok and compact_token_shape_ok and not token_shape_ok),
        "token_printed": False,
    }


def _public_token_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: payload[k] for k in (
        "path", "exists", "ok", "status", "detail", "mode", "raw_bytes", "line_count",
        "whitespace_count", "compact_length", "token_shape_ok", "compact_token_shape_ok",
        "can_repair_whitespace", "token_printed"
    ) if k in payload}


def _validate_telegram_chat_id(chat_id: str) -> None:
    if not chat_id:
        raise ConfigError("telegram chat id is empty")
    if not _TELEGRAM_CHAT_ID_RE.fullmatch(chat_id):
        raise ConfigError("telegram chat id must be a non-zero integer")
    value = int(chat_id)
    if value == 0 or value < -(2**63) or value > 2**63 - 1:
        raise ConfigError("telegram chat id must fit a signed 64-bit non-zero integer")


def _read_chat_id(path: Path) -> str:
    try:
        chat_id = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ConfigError(f"telegram chat id file not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read telegram chat id file: {path}: {exc}") from exc
    _require_0600(path)
    _validate_telegram_chat_id(chat_id)
    return chat_id


def _resolve_chat_id(*, chat_id: str | None = None, chat_file: Path | None = None) -> tuple[str, str]:
    if chat_id is not None:
        value = str(chat_id).strip()
        _validate_telegram_chat_id(value)
        return value, "argument"
    env_value = os.environ.get("LAI_GATEWAY_TELEGRAM_CHAT_ID", "").strip()
    if env_value:
        _validate_telegram_chat_id(env_value)
        return env_value, "environment"
    path = (chat_file or default_telegram_chat_path()).expanduser()
    if path.exists():
        return _read_chat_id(path), "file"
    return "", "none"


def _validate_telegram_token(token: str) -> None:
    if not token:
        raise ConfigError("telegram token is empty")
    if any(ch.isspace() for ch in token):
        raise ConfigError("telegram token must be a single token without whitespace")
    if not _TELEGRAM_TOKEN_RE.fullmatch(token):
        raise ConfigError("telegram token must look like digits:letters_digits_dash_or_underscore")


def _write_secret_file(path: Path, value: str, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        os.chmod(path.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if not force:
        flags |= os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
    finally:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


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
    _validate_telegram_token(token)
    return token


def _require_0600(path: Path) -> None:
    if os.name == "posix" and int(token_file_mode(path), 8) & 0o077:
        raise ConfigError(f"telegram token file permissions must be 0600: {path}")


def _env_send_enabled() -> bool:
    return os.environ.get("LAI_GATEWAY_TELEGRAM_ENABLE_SEND", "0").strip().lower() in {"1", "true", "yes", "on"}


def _env_receive_enabled() -> bool:
    return os.environ.get("LAI_GATEWAY_TELEGRAM_ENABLE_RECEIVE", "0").strip().lower() in {"1", "true", "yes", "on"}
