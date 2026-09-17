from __future__ import annotations

import json
import subprocess
import sys
import unittest

from lai_gateway.local_task_dry_run import collect_local_task_dry_run, render_local_task_dry_run


class LocalTaskDryRunTest(unittest.TestCase):
    def test_green_task_is_dry_run_only(self):
        payload = collect_local_task_dry_run(
            task_id="task-test-green",
            autonomy_zone="green",
            allowed_paths=["docs/product/*.md"],
            validation_plan=["python3 -m unittest tests.test_product_docs -v"],
            proposed_commands=["echo should-not-run"],
        )

        self.assertEqual(payload["schema_version"], "local-task-dry-run/v1")
        self.assertEqual(payload["task"]["schema_version"], "local-task/v1")
        self.assertEqual(payload["outbox"]["schema_version"], "local-task-outbox/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["dry_run_only"])
        self.assertFalse(payload["effective_authorization"])
        self.assertFalse(payload["would_execute_commands"])
        self.assertFalse(payload["would_modify_files"])
        self.assertFalse(payload["would_issue_grants"])
        self.assertFalse(payload["would_consume_grants"])
        self.assertFalse(payload["would_dispatch_adapter"])
        self.assertFalse(payload["would_call_harness"])
        self.assertFalse(payload["would_call_tools"])
        self.assertFalse(payload["would_use_credentials"])
        self.assertFalse(payload["would_send_messages"])
        self.assertFalse(payload["would_publish"])
        self.assertFalse(payload["would_merge_main"])

    def test_red_zone_task_is_blocked_without_execution(self):
        payload = collect_local_task_dry_run(
            task_id="task-test-red",
            autonomy_zone="red",
            allowed_paths=["docs/product/*.md"],
        )

        self.assertEqual(payload["overall"], "blocked")
        self.assertTrue(payload["task"]["requires_human_approval"])
        self.assertEqual(payload["outbox"]["status"], "blocked")
        self.assertFalse(payload["effective_authorization"])
        self.assertFalse(payload["would_execute_commands"])
        self.assertIn("merge_to_main", payload["prohibited_operations"])

    def test_render_contains_core_controls(self):
        payload = collect_local_task_dry_run(
            task_id="task-test-render",
            autonomy_zone="yellow",
            allowed_paths=["docs/product/*.md"],
        )
        rendered = render_local_task_dry_run(payload)

        self.assertIn("local-task-dry-run", rendered)
        self.assertIn("dry_run_only: true", rendered)
        self.assertIn("effective_authorization: false", rendered)
        self.assertIn("executes_commands: false", rendered)
        self.assertIn("issues_grants: false", rendered)
        self.assertIn("consumes_grants: false", rendered)
        self.assertIn("dispatches_adapter: false", rendered)
        self.assertIn("uses_credentials: false", rendered)

    def test_cli_json_is_machine_readable_and_non_executing(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "local-task-dry-run",
                "--task-id",
                "task-test-cli",
                "--autonomy-zone",
                "green",
                "--allowed-path",
                "docs/product/*.md",
                "--validation",
                "python3 -m unittest tests.test_product_docs -v",
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

        self.assertEqual(payload["operation"], "local-task-dry-run")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["task"]["task_id"], "task-test-cli")
        self.assertEqual(payload["task"]["allowed_paths"], ["docs/product/*.md"])
        self.assertEqual(payload["task"]["proposed_commands"], ["echo should-not-run"])
        self.assertFalse(payload["would_execute_commands"])
        self.assertFalse(payload["effective_authorization"])


if __name__ == "__main__":
    unittest.main()
