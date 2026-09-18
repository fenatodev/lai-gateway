from __future__ import annotations

import unittest
from pathlib import Path

from lai_gateway.model import collect_model_chat


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchGovernedDevFlowTest(unittest.TestCase):
    def test_direct_model_chat_never_creates_harness_run(self) -> None:
        payload = collect_model_chat(
            env={},
            prompt="ola",
            timeout_seconds=1.0,
            max_tokens=64,
        )

        conversation = payload.get("conversation", {})
        security = payload.get("security", {})

        self.assertTrue(conversation.get("direct_gateway_chat"))
        self.assertFalse(conversation.get("creates_harness_run"))
        self.assertFalse(security.get("creates_harness_run"))
        self.assertFalse(security.get("harness_fallback"))
        self.assertFalse(security.get("permission_elevation"))

    def test_workbench_has_explicit_three_phase_routing(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'let activeWorkbenchPhase = "observe";',
            js,
        )
        self.assertIn(
            'activeWorkbenchPhase === "observe"',
            js,
        )
        self.assertIn(
            'activeWorkbenchPhase === "work"',
            js,
        )
        self.assertIn(
            'activeWorkbenchPhase === "promote"',
            js,
        )

    def test_observe_routes_to_direct_gateway_chat(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        start = js.index("async function sendWorkbenchDirectChat")
        end = js.index(
            "async function loadLocalChatModelsForSelectedWorkspace",
            start,
        )
        direct = js[start:end]

        self.assertIn(
            'requestJson("/v1/gateway/chat"',
            direct,
        )
        self.assertNotIn(
            'requestJson("/v1/local-chat/runs"',
            direct,
        )
        self.assertIn(
            "creates_harness_run",
            direct,
        )

    def test_work_routes_only_to_existing_local_chat_work_path(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        start = js.index(
            'action === "create-local-chat-run"'
        )
        end = js.index(
            'action === "get-local-chat-events"',
            start,
        )
        action = js[start:end]

        self.assertIn(
            'if (activeWorkbenchPhase !== "work")',
            action,
        )
        self.assertIn(
            "LOCAL_CHAT_WORK_MODES.has(mode)",
            action,
        )
        self.assertIn(
            'requestJson("/v1/local-chat/runs"',
            action,
        )

    def test_apply_does_not_create_new_harness_run(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        start = js.index(
            'if (activeWorkbenchPhase === "promote")'
        )
        end = js.index(
            'if (activeWorkbenchPhase !== "work")',
            start,
        )
        promote = js[start:end]

        self.assertIn(
            "currentLocalReview",
            promote,
        )
        self.assertIn(
            "loadLocalReviewForCurrentRun",
            promote,
        )
        self.assertNotIn(
            'requestJson("/v1/local-chat/runs"',
            promote,
        )

    def test_review_transition_sets_apply_phase(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        start = js.index("function setLocalReview(payload)")
        end = js.index(
            "async function loadLocalChatModelsForSelectedWorkspace",
            start,
        )
        block = js[start:end]

        self.assertIn(
            'activeWorkbenchPhase = "promote"',
            block,
        )

    def test_promotion_still_requires_explicit_confirmation(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        start = js.index(
            'action === "apply-current-local-review"'
        )
        end = js.index(
            'action === "discard-current-local-review"',
            start,
        )
        apply_block = js[start:end]

        self.assertIn(
            "window.confirm(confirmation)",
            apply_block,
        )
        self.assertIn(
            "currentLocalReview.patchSha",
            apply_block,
        )
        self.assertIn(
            "/promotion",
            apply_block,
        )

    def test_pr131_local_operator_route_still_present(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )
        server = (ROOT / "lai_gateway/server.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'requestJson("/v1/gateway/local-operator"',
            js,
        )
        self.assertIn(
            'parsed.path == "/v1/gateway/local-operator"',
            server,
        )


if __name__ == "__main__":
    unittest.main()
