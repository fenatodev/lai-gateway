from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import re
import secrets
import threading
from typing import Any


DIRECT_CONVERSATION_SCHEMA_VERSION = "direct-conversation-session/v1"
DIRECT_CONVERSATION_MAX_SESSIONS = 32
DIRECT_CONVERSATION_MAX_EXCHANGES = 8
DIRECT_CONVERSATION_MAX_CHARS = 24_000

_ID_RE = re.compile(r"^dc-[0-9a-f]{16}$")


class DirectConversationError(RuntimeError):
    pass


class DirectConversationNotFound(DirectConversationError):
    pass


class DirectConversationBusy(DirectConversationError):
    pass


@dataclass
class _Conversation:
    messages: list[dict[str, str]] = field(default_factory=list)
    busy: bool = False


def is_direct_conversation_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


class DirectConversationStore:
    def __init__(
        self,
        *,
        max_sessions: int = DIRECT_CONVERSATION_MAX_SESSIONS,
        max_exchanges: int = DIRECT_CONVERSATION_MAX_EXCHANGES,
        max_chars: int = DIRECT_CONVERSATION_MAX_CHARS,
    ) -> None:
        if max_sessions < 1 or max_exchanges < 1 or max_chars < 1:
            raise ValueError("direct conversation bounds must be positive")

        self.max_sessions = max_sessions
        self.max_exchanges = max_exchanges
        self.max_chars = max_chars
        self._items: OrderedDict[str, _Conversation] = OrderedDict()
        self._lock = threading.RLock()

    def create(self) -> dict[str, Any]:
        with self._lock:
            while len(self._items) >= self.max_sessions:
                removable = next(
                    (
                        cid
                        for cid, conversation in self._items.items()
                        if not conversation.busy
                    ),
                    None,
                )
                if removable is None:
                    raise DirectConversationBusy(
                        "all direct conversation slots are busy"
                    )
                del self._items[removable]

            conversation_id = ""
            while not conversation_id or conversation_id in self._items:
                conversation_id = f"dc-{secrets.token_hex(8)}"

            self._items[conversation_id] = _Conversation()
            return self._snapshot(conversation_id)

    def snapshot(self, conversation_id: str) -> dict[str, Any]:
        with self._lock:
            self._get(conversation_id)
            self._items.move_to_end(conversation_id)
            return self._snapshot(conversation_id)

    def reset(self, conversation_id: str) -> dict[str, Any]:
        with self._lock:
            conversation = self._get(conversation_id)
            if conversation.busy:
                raise DirectConversationBusy("direct conversation is busy")
            conversation.messages.clear()
            return self._snapshot(conversation_id)

    def begin_turn(self, conversation_id: str) -> tuple[dict[str, str], ...]:
        with self._lock:
            conversation = self._get(conversation_id)
            if conversation.busy:
                raise DirectConversationBusy("direct conversation is busy")
            conversation.busy = True
            self._items.move_to_end(conversation_id)
            return tuple(dict(item) for item in conversation.messages)

    def finish_turn(
        self,
        conversation_id: str,
        *,
        user_message: str,
        assistant_message: str,
    ) -> dict[str, Any]:
        with self._lock:
            conversation = self._get(conversation_id)

            if not conversation.busy:
                raise DirectConversationError(
                    "direct conversation turn is not active"
                )

            user = user_message.strip()
            assistant = assistant_message.strip()

            if not user or not assistant:
                conversation.busy = False
                raise DirectConversationError(
                    "direct conversation messages must be non-empty"
                )

            conversation.messages.extend(
                (
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                )
            )
            conversation.busy = False
            self._trim(conversation)
            return self._snapshot(conversation_id)

    def abort_turn(self, conversation_id: str) -> None:
        with self._lock:
            conversation = self._items.get(conversation_id)
            if conversation is not None:
                conversation.busy = False

    def _get(self, conversation_id: str) -> _Conversation:
        if not is_direct_conversation_id(conversation_id):
            raise DirectConversationNotFound("direct conversation not found")
        conversation = self._items.get(conversation_id)
        if conversation is None:
            raise DirectConversationNotFound("direct conversation not found")
        return conversation

    def _trim(self, conversation: _Conversation) -> None:
        max_messages = self.max_exchanges * 2

        while len(conversation.messages) > max_messages:
            del conversation.messages[:2]

        while (
            sum(len(item["content"]) for item in conversation.messages)
            > self.max_chars
            and len(conversation.messages) >= 2
        ):
            del conversation.messages[:2]

    def _snapshot(self, conversation_id: str) -> dict[str, Any]:
        conversation = self._items[conversation_id]
        return {
            "schema_version": DIRECT_CONVERSATION_SCHEMA_VERSION,
            "conversation_id": conversation_id,
            "status": "busy" if conversation.busy else "ready",
            "exchange_count": len(conversation.messages) // 2,
            "message_count": len(conversation.messages),
            "char_count": sum(
                len(item["content"]) for item in conversation.messages
            ),
            "max_exchanges": self.max_exchanges,
            "max_chars": self.max_chars,
            "persistent": False,
            "harness_session": False,
            "creates_harness_run": False,
            "grants_authority": False,
        }
