import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lai_gateway.config import GatewayConfig
from lai_gateway.onboarding import collect_onboarding_status, render_onboarding_status

from .fake_harness import TOKEN, fake_harness


class OnboardingStatusTest(unittest.TestCase):
    def test_onboarding_reports_sanitized_next_steps_without_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "missing-control-token"
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with patch(
                "lai_gateway.onboarding.collect_model_status",
                return_value={"overall": "needs_config", "model_config": {"configured": False}},
            ):
                payload = collect_onboarding_status(config=config)
        rendered = render_onboarding_status(payload)
        body = json.dumps(payload, sort_keys=True) + rendered

        self.assertEqual(payload["operation"], "onboarding")
        self.assertEqual(payload["schema_version"], "onboarding-next-steps/v1")
        self.assertEqual(payload["overall"], "blocked")
        cards = {card["area"]: card for card in payload["cards"]}
        self.assertEqual(cards["token"]["status"], "blocked")
        self.assertEqual(cards["modelo"]["status"], "warn")
        self.assertEqual(cards["documento"]["status"], "warn")
        self.assertGreaterEqual(len(payload["next_steps"]), 2)
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertFalse(payload["security"]["prints_paths"])
        self.assertFalse(payload["security"]["starts_server"])
        self.assertFalse(payload["security"]["modifies_files"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["grants_authority"])
        self.assertNotIn(str(token_file), body)
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)

    def test_onboarding_document_workspace_uses_restricted_metadata_only_status(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        workspace = repo / "state" / "onboarding-test-workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        document = workspace / "note.md"
        document.write_text("texto local\n", encoding="utf-8")
        try:
            with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
                token_file = Path(tmp) / "token"
                token_file.write_text(TOKEN, encoding="utf-8")
                config = GatewayConfig(harness_url=harness.url, token_file=token_file)
                with patch(
                    "lai_gateway.onboarding.collect_model_status",
                    return_value={"overall": "ready", "model_config": {"configured": True}},
                ):
                    payload = collect_onboarding_status(config=config, workspace_root=workspace)
            cards = {card["area"]: card for card in payload["cards"]}
            self.assertEqual(cards["documento"]["status"], "ready")
            self.assertFalse(payload["security"]["prints_document_content"])
            body = json.dumps(payload, sort_keys=True)
            self.assertNotIn("texto local", body)
            self.assertNotIn(str(workspace), body)
        finally:
            try:
                document.unlink()
                workspace.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
