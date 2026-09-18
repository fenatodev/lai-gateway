from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DirectConversationUiTest(unittest.TestCase):
    def test_workbench_exposes_direct_conversation_session(self) -> None:
        html = (
            ROOT / "lai_gateway/static/index.html"
        ).read_text(encoding="utf-8")

        js = (
            ROOT / "lai_gateway/static/app.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'id="direct-conversation-pill"',
            html,
        )
        self.assertIn(
            'data-action="new-direct-conversation"',
            html,
        )
        self.assertIn(
            'let activeDirectConversationId = "";',
            js,
        )
        self.assertIn(
            'requestJson("/v1/gateway/conversations"',
            js,
        )
        self.assertIn(
            "conversation_id: activeDirectConversationId",
            js,
        )

    def test_direct_conversation_path_never_creates_local_chat_run(self) -> None:
        js = (
            ROOT / "lai_gateway/static/app.js"
        ).read_text(encoding="utf-8")

        start = js.index(
            "function setDirectConversationState"
        )

        end = js.index(
            "async function loadLocalChatModelsForSelectedWorkspace",
            start,
        )

        block = js[start:end]

        self.assertIn(
            "/v1/gateway/conversations",
            block,
        )
        self.assertIn(
            "/v1/gateway/chat",
            block,
        )
        self.assertNotIn(
            'requestJson("/v1/local-chat/runs"',
            block,
        )

    def test_new_conversation_is_blocked_while_direct_turn_is_pending(self) -> None:
        js = (
            ROOT / "lai_gateway/static/app.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "directConversationPending",
            js,
        )
        self.assertIn(
            "aguarde a resposta atual antes de iniciar uma nova conversa",
            js,
        )

    def test_work_and_apply_routes_remain_present(self) -> None:
        js = (
            ROOT / "lai_gateway/static/app.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'requestJson("/v1/local-chat/runs"',
            js,
        )
        self.assertIn(
            'action === "apply-current-local-review"',
            js,
        )
        self.assertIn(
            "window.confirm(confirmation)",
            js,
        )


if __name__ == "__main__":
    unittest.main()
