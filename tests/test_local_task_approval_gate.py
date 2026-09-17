from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.local_task_approval_gate import (
    collect_local_task_approval_gate,
    render_local_task_approval_gate,
)


ROOT = Path(__file__).resolve().parents[1]


class LocalTaskApprovalGateTest(unittest.TestCase):
    def _review(self, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": "local-task-review-gate/v1",
            "overall": "ready",
            "decision": "ready",
            "task_id": "task-approval",
            "read_only": True,
            "autonomy_zone": "green",
            "effective_authorization": False,
            "executes_commands": False,
            "calls_harness": False,
            "executes_tools": False,
            "dispatches_adapter": False,
            "issues_grants": False,
            "consumes_grants": False,
            "uses_credentials": False,
            "sends_messages": False,
            "publishes": False,
            "merges_main": False,
            "external_side_effects": False,
            "checks": [{"name": "review", "status": "ok", "detail": "ready"}],
        }
        payload.update(overrides)
        return payload

    def _write_review(self, repo: Path, payload: dict[str, object]) -> str:
        rel = Path(".lai-ai") / "reviews" / f"{payload.get('task_id', 'task')}.json"
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
        return rel.as_posix()

    def test_ready_without_approval_requires_green_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            review_file = self._write_review(repo, self._review())

            payload = collect_local_task_approval_gate(repo=repo, review_file=review_file)

            self.assertEqual(payload["overall"], "ready_without_approval")
            self.assertEqual(payload["decision"], "ready_without_approval")
            self.assertFalse(payload["requires_human_approval"])
            self.assertFalse(payload["execution_authorized"])
            self.assertFalse(payload["issues_grants"])
            self.assertFalse(payload["external_side_effects"])

    def test_missing_green_zone_evidence_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            review = self._review()
            review.pop("autonomy_zone")
            review_file = self._write_review(repo, review)

            payload = collect_local_task_approval_gate(repo=repo, review_file=review_file)

            self.assertEqual(payload["overall"], "needs_approval")
            self.assertTrue(payload["requires_human_approval"])
            self.assertFalse(payload["execution_authorized"])

    def test_yellow_review_requires_approval(self) -> None:
        payload = collect_local_task_approval_gate(
            review_payload=self._review(autonomy_zone="yellow")
        )

        self.assertEqual(payload["overall"], "needs_approval")
        self.assertTrue(payload["requires_human_approval"])

    def test_blocked_review_stays_blocked(self) -> None:
        payload = collect_local_task_approval_gate(
            review_payload=self._review(overall="blocked", decision="blocked")
        )

        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["execution_authorized"])

    def test_unsafe_authority_claim_is_blocked(self) -> None:
        payload = collect_local_task_approval_gate(
            review_payload=self._review(effective_authorization=True)
        )

        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["execution_authorized"])

    def test_invalid_schema_is_invalid(self) -> None:
        payload = collect_local_task_approval_gate(
            review_payload=self._review(schema_version="wrong/v1")
        )

        self.assertEqual(payload["overall"], "invalid")

    def test_path_traversal_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = collect_local_task_approval_gate(
                repo=Path(tmp),
                review_file="../review.json",
            )

            self.assertEqual(payload["overall"], "invalid")

    def test_render_contains_non_execution_controls(self) -> None:
        text = render_local_task_approval_gate(
            collect_local_task_approval_gate(review_payload=self._review())
        )

        for term in (
            "read_only: true",
            "approval_effective: false",
            "execution_authorized: false",
            "executes_commands: false",
            "issues_grants: false",
            "external_side_effects: false",
        ):
            self.assertIn(term, text)

    def test_cli_json_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            review_file = self._write_review(repo, self._review())
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "local-task-approval-gate",
                    "--review-file",
                    review_file,
                    "--repo-root",
                    str(repo),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], "local-task-approval-gate/v1")
        self.assertEqual(payload["overall"], "ready_without_approval")
        self.assertFalse(payload["execution_authorized"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
