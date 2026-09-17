from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.local_task_file_pack import collect_local_task_file_pack
from lai_gateway.local_task_review_gate import collect_local_task_review_gate, render_local_task_review_gate


class LocalTaskReviewGateTest(unittest.TestCase):

    def test_review_output_propagates_non_authorizing_approval_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task = self._task()
            task["autonomy_zone"] = "yellow"
            task["approval_required"] = True

            try:
                outbox = self._outbox(task_id=task["task_id"])
            except TypeError:
                outbox = self._outbox()
                outbox["task_id"] = task["task_id"]

            task_file, outbox_file = self._write_pack(repo, task, outbox)

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["autonomy_zone"], "yellow")
            self.assertTrue(payload["approval_required"])
            self.assertFalse(payload["effective_authorization"])
            self.assertFalse(payload["executes_commands"])

    def _write_pack(self, repo: Path, task_id: str = "task-review-ok", zone: str = "green") -> tuple[str, str]:
        payload = collect_local_task_file_pack(
            repo=repo,
            task_id=task_id,
            autonomy_zone=zone,
            allowed_paths=["docs/product/*.md"],
            write=True,
        )
        return payload["task_file"], payload["outbox_file"]

    def test_ready_for_safe_file_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo)

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["schema_version"], "local-task-review-gate/v1")
            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(payload["decision"], "ready")
            self.assertFalse(payload["effective_authorization"])
            self.assertFalse(payload["executes_commands"])
            self.assertFalse(payload["calls_harness"])
            self.assertFalse(payload["executes_tools"])
            self.assertFalse(payload["dispatches_adapter"])
            self.assertFalse(payload["issues_grants"])
            self.assertFalse(payload["consumes_grants"])

    def test_missing_file_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=".lai-ai/tasks/missing.task.json",
                outbox_file=".lai-ai/outbox/missing.outbox.json",
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertEqual(payload["decision"], "invalid")

    def test_path_traversal_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_review_gate(
                repo=repo,
                task_file="../outside.task.json",
                outbox_file=".lai-ai/outbox/x.outbox.json",
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertEqual(payload["decision"], "invalid")

    def test_review_output_propagates_non_authorizing_approval_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(
                repo,
                task_id="task-review-approval",
                zone="yellow",
            )

            task_path = repo / task_file
            task_record = json.loads(task_path.read_text(encoding="utf-8"))
            task_record["approval_required"] = True
            task_path.write_text(json.dumps(task_record), encoding="utf-8")

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["autonomy_zone"], "yellow")
            self.assertTrue(payload["approval_required"])
            self.assertFalse(payload["effective_authorization"])
            self.assertFalse(payload["executes_commands"])

    def test_red_zone_task_record_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo, task_id="task-red", zone="green")
            task_path = repo / task_file
            task_record = json.loads(task_path.read_text(encoding="utf-8"))
            task_record["autonomy_zone"] = "red"
            task_path.write_text(json.dumps(task_record), encoding="utf-8")

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertEqual(payload["decision"], "blocked")

    def test_false_authority_claim_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo, task_id="task-unsafe")
            task_path = repo / task_file
            task_record = json.loads(task_path.read_text(encoding="utf-8"))
            task_record["effective_authorization"] = True
            task_path.write_text(json.dumps(task_record), encoding="utf-8")

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertEqual(payload["decision"], "blocked")

    def test_mismatched_task_ids_are_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo, task_id="task-a")
            outbox_path = repo / outbox_file
            outbox_record = json.loads(outbox_path.read_text(encoding="utf-8"))
            outbox_record["task_id"] = "task-b"
            outbox_path.write_text(json.dumps(outbox_record), encoding="utf-8")

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertEqual(payload["decision"], "invalid")

    def test_render_contains_non_execution_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo)

            payload = collect_local_task_review_gate(
                repo=repo,
                task_file=task_file,
                outbox_file=outbox_file,
            )
            rendered = render_local_task_review_gate(payload)

            self.assertIn("local-task-review-gate", rendered)
            self.assertIn("read_only: true", rendered)
            self.assertIn("effective_authorization: false", rendered)
            self.assertIn("executes_commands: false", rendered)
            self.assertIn("calls_harness: false", rendered)
            self.assertIn("dispatches_adapter: false", rendered)
            self.assertIn("issues_grants: false", rendered)
            self.assertIn("consumes_grants: false", rendered)

    def test_cli_json_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, outbox_file = self._write_pack(repo, task_id="task-cli-review")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "local-task-review-gate",
                    "--repo-root",
                    tmp,
                    "--task-file",
                    task_file,
                    "--outbox-file",
                    outbox_file,
                    "--json",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "local-task-review-gate")
            self.assertEqual(payload["overall"], "ready")
            self.assertFalse(payload["effective_authorization"])
            self.assertFalse(payload["executes_commands"])


if __name__ == "__main__":
    unittest.main()
