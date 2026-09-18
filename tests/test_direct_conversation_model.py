from __future__ import annotations

import unittest
from unittest.mock import patch

from lai_gateway.model import collect_model_chat


class DirectConversationModelTest(unittest.TestCase):
    def test_one_shot_chat_remains_first_turn(self) -> None:
        with patch(
            "lai_gateway.model._run_conversation_chat_completion"
        ) as run:
            run.return_value = {
                "status": "ready",
                "network_call": True,
                "message": "resposta",
            }

            payload = collect_model_chat(
                env={},
                prompt="olá",
            )

        self.assertEqual(run.call_args.kwargs["history"], ())
        self.assertTrue(payload["conversation"]["first_turn"])
        self.assertEqual(
            payload["conversation"]["history_message_count"],
            0,
        )
        self.assertFalse(
            payload["conversation"]["creates_harness_run"]
        )

    def test_valid_history_is_passed_to_local_model(self) -> None:
        history = (
            {"role": "user", "content": "meu nome é teste"},
            {"role": "assistant", "content": "entendido"},
        )

        with patch(
            "lai_gateway.model._run_conversation_chat_completion"
        ) as run:
            run.return_value = {
                "status": "ready",
                "network_call": True,
                "message": "continuação",
            }

            payload = collect_model_chat(
                env={},
                prompt="qual informação eu disse?",
                history=history,
            )

        self.assertEqual(
            run.call_args.kwargs["history"],
            history,
        )
        self.assertFalse(payload["conversation"]["first_turn"])
        self.assertTrue(
            payload["conversation"]["history_accepted"]
        )
        self.assertEqual(
            payload["conversation"]["history_message_count"],
            2,
        )

    def test_invalid_history_fails_closed_without_model_call(self) -> None:
        invalid_history = (
            {
                "role": "assistant",
                "content": "não pode começar por assistant",
            },
        )

        with patch(
            "lai_gateway.model._run_conversation_chat_completion"
        ) as run:
            payload = collect_model_chat(
                env={},
                prompt="teste",
                history=invalid_history,
            )

        run.assert_not_called()
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(
            payload["conversation"]["history_accepted"]
        )
        self.assertFalse(
            payload["conversation"]["creates_harness_run"]
        )


if __name__ == "__main__":
    unittest.main()
