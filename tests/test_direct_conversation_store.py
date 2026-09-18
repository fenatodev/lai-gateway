from __future__ import annotations

import unittest

from lai_gateway.direct_conversation import (
    DirectConversationBusy,
    DirectConversationError,
    DirectConversationNotFound,
    DirectConversationStore,
)


class DirectConversationStoreTest(unittest.TestCase):
    def test_sessions_are_isolated(self) -> None:
        store = DirectConversationStore()

        first = store.create()["conversation_id"]
        second = store.create()["conversation_id"]

        store.begin_turn(first)
        store.finish_turn(
            first,
            user_message="contexto primeiro",
            assistant_message="resposta primeiro",
        )

        self.assertEqual(
            store.begin_turn(second),
            (),
        )
        store.abort_turn(second)

    def test_reset_removes_history(self) -> None:
        store = DirectConversationStore()
        conversation_id = store.create()["conversation_id"]

        store.begin_turn(conversation_id)
        store.finish_turn(
            conversation_id,
            user_message="antes",
            assistant_message="resposta",
        )

        snapshot = store.reset(conversation_id)

        self.assertEqual(snapshot["exchange_count"], 0)
        self.assertEqual(snapshot["message_count"], 0)

    def test_history_is_bounded_by_exchange_count(self) -> None:
        store = DirectConversationStore(
            max_exchanges=2,
            max_chars=10_000,
        )
        conversation_id = store.create()["conversation_id"]

        for index in range(5):
            store.begin_turn(conversation_id)
            store.finish_turn(
                conversation_id,
                user_message=f"u{index}",
                assistant_message=f"a{index}",
            )

        snapshot = store.snapshot(conversation_id)

        self.assertEqual(snapshot["exchange_count"], 2)
        self.assertEqual(snapshot["message_count"], 4)

    def test_history_is_bounded_by_chars_without_splitting_pair(self) -> None:
        store = DirectConversationStore(
            max_exchanges=8,
            max_chars=20,
        )
        conversation_id = store.create()["conversation_id"]

        for index in range(3):
            store.begin_turn(conversation_id)
            store.finish_turn(
                conversation_id,
                user_message=f"user-{index}",
                assistant_message=f"answer-{index}",
            )

        snapshot = store.snapshot(conversation_id)

        self.assertLessEqual(snapshot["char_count"], 20)
        self.assertEqual(snapshot["message_count"] % 2, 0)

    def test_same_session_rejects_concurrent_turn(self) -> None:
        store = DirectConversationStore()
        conversation_id = store.create()["conversation_id"]

        store.begin_turn(conversation_id)

        with self.assertRaises(DirectConversationBusy):
            store.begin_turn(conversation_id)

        store.abort_turn(conversation_id)

    def test_finish_requires_active_turn(self) -> None:
        store = DirectConversationStore()
        conversation_id = store.create()["conversation_id"]

        with self.assertRaises(DirectConversationError):
            store.finish_turn(
                conversation_id,
                user_message="user",
                assistant_message="assistant",
            )

    def test_old_idle_session_is_evicted_at_capacity(self) -> None:
        store = DirectConversationStore(max_sessions=2)

        first = store.create()["conversation_id"]
        store.create()
        store.create()

        with self.assertRaises(DirectConversationNotFound):
            store.snapshot(first)

    def test_invalid_bounds_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DirectConversationStore(max_sessions=0)


if __name__ == "__main__":
    unittest.main()
