import json
import tempfile
import unittest
from pathlib import Path

from lai_gateway import __version__
from lai_gateway.alpha_readiness import collect_alpha_readiness, render_alpha_readiness

ROOT = Path(__file__).resolve().parents[1]


def ready_release_payload(phase: str = "ready_for_integration") -> dict[str, object]:
    return {
        "overall": "ready",
        "phase": phase,
        "target_version": __version__,
        "expected_tag": f"v{__version__}",
        "branch": "feat/pr100-technical-alpha-readiness",
        "tag_ready": phase == "ready_to_tag",
    }


class AlphaReadinessTest(unittest.TestCase):
    def test_collects_candidate_go_without_publishing_or_granting_authority(self) -> None:
        payload = collect_alpha_readiness(repo=ROOT, release_check_payload=ready_release_payload())
        self.assertEqual(payload["operation"], "alpha-readiness")
        self.assertEqual(payload["schema_version"], "alpha-readiness/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["decision"], "candidate_go")
        self.assertFalse(payload["publication_allowed"])
        self.assertFalse(payload["tag_or_release_created"])
        self.assertFalse(payload["external_capabilities_enabled"])
        self.assertTrue(payload["human_publication_approval_required"])
        self.assertEqual(payload["domain"], "product_alpha_readiness")
        self.assertEqual(payload["channel"], "cli_gateway_workbench")
        self.assertEqual(payload["autonomy"], "read_only_verification")
        self.assertEqual(payload["capability"], "alpha.go_no_go_check")
        self.assertTrue(payload["security"]["read_only"])
        self.assertFalse(payload["security"]["publishes_release"])
        self.assertFalse(payload["security"]["creates_tag"])
        self.assertFalse(payload["security"]["prints_tokens"])
        self.assertTrue(all(check["status"] == "ok" for check in payload["checks"]), payload["checks"])
        encoded = json.dumps(payload)
        self.assertNotIn("Bearer", encoded)
        self.assertNotIn("ghp_", encoded)

    def test_blocks_when_release_check_is_not_ready(self) -> None:
        release = ready_release_payload()
        release["overall"] = "blocked"
        release["phase"] = "blocked"
        payload = collect_alpha_readiness(repo=ROOT, release_check_payload=release)
        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["decision"], "no_go")
        self.assertIn("release_check", [check["name"] for check in payload["checks"] if check["status"] == "fail"])

    def test_blocks_when_required_docs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs" / "product").mkdir(parents=True)
            (repo / "README.md").write_text("incomplete", encoding="utf-8")
            payload = collect_alpha_readiness(repo=repo, release_check_payload=ready_release_payload())
        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["decision"], "no_go")
        self.assertTrue(any(check["name"].startswith("doc:") for check in payload["checks"] if check["status"] == "fail"))

    def test_render_is_secret_free_and_human_gate_is_visible(self) -> None:
        payload = collect_alpha_readiness(repo=ROOT, release_check_payload=ready_release_payload("ready_to_tag"))
        rendered = render_alpha_readiness(payload)
        self.assertIn("alpha-readiness: ready", rendered)
        self.assertIn("decision: candidate_go", rendered)
        self.assertIn("publication_allowed: false", rendered)
        self.assertIn("human_publication_approval_required: true", rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertNotIn("token=", rendered)


if __name__ == "__main__":
    unittest.main()
