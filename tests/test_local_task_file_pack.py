from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.local_task_file_pack import collect_local_task_file_pack, render_local_task_file_pack


class LocalTaskFilePackTest(unittest.TestCase):
    def test_plan_does_not_create_files_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_file_pack(
                repo=repo,
                task_id="task-file-pack-plan",
                autonomy_zone="green",
                allowed_paths=["docs/product/*.md"],
                write=False,
            )

            self.assertEqual(payload["schema_version"], "local-task-file-pack/v1")
            self.assertEqual(payload["overall"], "planned")
            self.assertFalse(payload["wrote_files"])
            self.assertFalse((repo / ".lai-ai").exists())
            self.assertFalse(payload["would_execute_commands"])
            self.assertFalse(payload["effective_authorization"])

    def test_write_creates_only_task_and_outbox_json_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_file_pack(
                repo=repo,
                task_id="Task File Pack Write",
                autonomy_zone="green",
                allowed_paths=["docs/product/*.md"],
                proposed_commands=["echo should-not-run"],
                write=True,
            )

            self.assertEqual(payload["overall"], "written")
            self.assertTrue(payload["wrote_files"])
            self.assertEqual(payload["written_files"], [
                ".lai-ai/tasks/task-file-pack-write.task.json",
                ".lai-ai/outbox/task-file-pack-write.outbox.json",
            ])

            task_record = json.loads((repo / payload["task_file"]).read_text(encoding="utf-8"))
            outbox_record = json.loads((repo / payload["outbox_file"]).read_text(encoding="utf-8"))

            self.assertEqual(task_record["schema_version"], "local-task/v1")
            self.assertEqual(outbox_record["schema_version"], "local-task-outbox/v1")
            self.assertEqual(task_record["file_pack_schema_version"], "local-task-file-pack/v1")
            self.assertFalse(task_record["effective_authorization"])
            self.assertFalse(outbox_record["effective_authorization"])
            self.assertEqual(task_record["proposed_commands"], ["echo should-not-run"])

    def test_unsafe_output_root_is_blocked_and_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_file_pack(
                repo=repo,
                task_id="unsafe-root",
                output_root="../outside",
                write=True,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["wrote_files"])
            self.assertEqual(payload["written_files"], [])
            self.assertFalse((repo.parent / "outside").exists())

    def test_red_zone_is_not_written_as_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            payload = collect_local_task_file_pack(
                repo=repo,
                task_id="red-zone",
                autonomy_zone="red",
                write=True,
            )

            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["wrote_files"])
            self.assertFalse((repo / ".lai-ai").exists())

    def test_render_contains_core_non_execution_controls(self):
        payload = collect_local_task_file_pack(
            task_id="render-controls",
            autonomy_zone="green",
            allowed_paths=["docs/product/*.md"],
        )
        rendered = render_local_task_file_pack(payload)

        self.assertIn("local-task-file-pack", rendered)
        self.assertIn("dry_run_only: true", rendered)
        self.assertIn("effective_authorization: false", rendered)
        self.assertIn("executes_commands: false", rendered)
        self.assertIn("calls_harness: false", rendered)
        self.assertIn("dispatches_adapter: false", rendered)
        self.assertIn("issues_grants: false", rendered)
        self.assertIn("consumes_grants: false", rendered)
        self.assertIn("uses_credentials: false", rendered)

    def test_cli_json_plan_is_machine_readable_and_non_executing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "local-task-file-pack",
                    "--repo-root",
                    tmp,
                    "--task-id",
                    "task-cli-file-pack",
                    "--autonomy-zone",
                    "green",
                    "--allowed-path",
                    "docs/product/*.md",
                    "--proposed-command",
                    "echo should-not-run",
                    "--json",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "local-task-file-pack")
            self.assertEqual(payload["overall"], "planned")
            self.assertFalse(payload["wrote_files"])
            self.assertFalse(payload["would_execute_commands"])
            self.assertFalse(payload["would_call_harness"])
            self.assertFalse(payload["would_call_tools"])
            self.assertFalse(payload["would_dispatch_adapter"])
            self.assertFalse(payload["effective_authorization"])
            self.assertFalse((Path(tmp) / ".lai-ai").exists())


if __name__ == "__main__":
    unittest.main()
