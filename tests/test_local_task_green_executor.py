from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.local_task_approval_gate import collect_local_task_approval_gate
from lai_gateway.local_task_file_pack import collect_local_task_file_pack
from lai_gateway.local_task_green_executor import collect_local_task_green_executor, render_local_task_green_executor
from lai_gateway.local_task_review_gate import collect_local_task_review_gate


class LocalTaskGreenExecutorTest(unittest.TestCase):
    def _approved_pack(
        self,
        repo: Path,
        *,
        task_id: str = "task-green-executor",
        zone: str = "green",
        approval_required: bool = False,
        commands: list[str] | None = None,
    ) -> tuple[str, dict, dict]:
        pack = collect_local_task_file_pack(
            repo=repo,
            task_id=task_id,
            autonomy_zone=zone,
            allowed_paths=["docs/product/*.md"],
            proposed_commands=commands or ["git --version"],
            write=True,
        )

        task_file = pack["task_file"]
        task_path = repo / task_file
        task_record = json.loads(task_path.read_text(encoding="utf-8"))
        task_record["requires_human_approval"] = approval_required
        task_path.write_text(json.dumps(task_record), encoding="utf-8")

        review = collect_local_task_review_gate(
            repo=repo,
            task_file=task_file,
            outbox_file=pack["outbox_file"],
        )
        approval = collect_local_task_approval_gate(review_payload=review)
        return task_file, task_record, approval

    def test_executes_green_task_declared_allowlisted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo)

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git --version"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "executed")
            self.assertEqual(payload["task_digest"], approval["task_digest"])
            self.assertTrue(payload["executes_commands"])
            self.assertEqual(payload["planned_commands"], ["git --version"])
            self.assertEqual(payload["command_results"][0]["status"], "success")
            self.assertFalse(payload["calls_harness"])
            self.assertFalse(payload["dispatches_adapter"])
            self.assertFalse(payload["external_side_effects"])

    def test_ready_without_execute_flag_does_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo)

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git --version"],
                execute=False,
            )

            self.assertEqual(payload["overall"], "ready")
            self.assertFalse(payload["executes_commands"])
            self.assertEqual(payload["command_results"], [])

    def test_task_mutation_after_review_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, _task, approval = self._approved_pack(repo)

            task_path = repo / task_file
            task_record = json.loads(task_path.read_text(encoding="utf-8"))
            task_record["allowed_paths"].append("README.md")
            task_path.write_text(json.dumps(task_record), encoding="utf-8")

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                approval_payload=approval,
                commands=["git --version"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertFalse(payload["executes_commands"])
            self.assertEqual(payload["command_results"], [])
            self.assertNotEqual(
                payload["task_digest"],
                approval["task_digest"],
            )

    def test_malformed_approval_digest_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo)
            approval["task_digest"] = "sha256:not-a-digest"

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git --version"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertFalse(payload["executes_commands"])
            self.assertEqual(payload["command_results"], [])

    def test_blocks_yellow_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(
                repo,
                zone="yellow",
                approval_required=True,
            )

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git --version"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["executes_commands"])

    def test_blocks_command_not_declared_by_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo, commands=["git --version"])

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git diff --check"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["executes_commands"])

    def test_blocks_disallowed_declared_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo, commands=["rm -rf ."])

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["rm -rf ."],
                execute=True,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["executes_commands"])

    def test_path_traversal_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_green_executor(
                repo=repo,
                approval_file="../approval.json",
                task_file=".lai-ai/tasks/task.task.json",
                commands=["git --version"],
                execute=True,
            )

            self.assertEqual(payload["overall"], "invalid")
            self.assertFalse(payload["executes_commands"])

    def test_render_contains_executor_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, task, approval = self._approved_pack(repo)

            payload = collect_local_task_green_executor(
                repo=repo,
                task_file=task_file,
                task_payload=task,
                approval_payload=approval,
                commands=["git --version"],
                execute=False,
            )
            rendered = render_local_task_green_executor(payload)

            self.assertIn("local-task-green-executor", rendered)
            self.assertIn("green_zone_only: true", rendered)
            self.assertIn("shell: false", rendered)
            self.assertIn("calls_harness: false", rendered)
            self.assertIn("dispatches_adapter: false", rendered)
            self.assertIn("external_side_effects: false", rendered)

    def test_cli_json_executes_allowlisted_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            task_file, _task, approval = self._approved_pack(repo, task_id="task-green-cli")
            approval_file = ".lai-ai/approvals/task-green-cli.approval.json"
            approval_path = repo / approval_file
            approval_path.parent.mkdir(parents=True, exist_ok=True)
            approval_path.write_text(json.dumps(approval), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "local-task-green-executor",
                    "--repo-root",
                    tmp,
                    "--approval-file",
                    approval_file,
                    "--task-file",
                    task_file,
                    "--command",
                    "git --version",
                    "--execute",
                    "--json",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "local-task-green-executor")
            self.assertEqual(payload["overall"], "executed")
            self.assertTrue(payload["executes_commands"])


if __name__ == "__main__":
    unittest.main()
