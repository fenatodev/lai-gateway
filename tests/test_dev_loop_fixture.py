from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.approval_inbox import collect_approval_inbox
from lai_gateway.dev_loop_fixture import collect_dev_loop_fixture, render_dev_loop_fixture

SECRET = "token=supersecretvalue"


class DevLoopFixtureTest(unittest.TestCase):
    def _enqueue_local_dev(self, workspace: Path, scope_root: Path) -> dict[str, object]:
        return collect_approval_inbox(
            workspace_root=workspace,
            inbox_action="enqueue",
            domain="project",
            channel="workbench",
            autonomy="high",
            capability="dev-loop-fixture",
            action="prepare local fixture review",
            target="tests/fixtures/local-dev-loop.md",
            data="sanitized proposal fields",
            effect="fixture review only",
            risk="low",
            scope_root=scope_root,
        )

    def test_runs_observe_work_review_apply_fixture_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "project"
            workspace.mkdir()
            enqueue = self._enqueue_local_dev(workspace, root)
            payload = collect_dev_loop_fixture(workspace_root=workspace, scope_root=root)
        self.assertEqual(enqueue["overall"], "ready")
        self.assertEqual(payload["operation"], "dev-loop-fixture")
        self.assertEqual(payload["schema_version"], "dev-loop-fixture/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["fixture"]["fixture_only"])
        self.assertFalse(payload["fixture"]["source_checkout_modified"])
        self.assertFalse(payload["security"]["effective_authorization"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["uses_credentials"])
        self.assertFalse(payload["security"]["sends_messages"])
        self.assertFalse(payload["security"]["publishes"])
        self.assertFalse(payload["security"]["calls_harness"])
        self.assertFalse(payload["security"]["source_checkout_write"])
        self.assertFalse(payload["security"]["merge_allowed"])
        self.assertFalse(payload["security"]["publication_allowed"])
        self.assertEqual([step["phase"] for step in payload["fixture"]["steps"]], ["observe", "work", "review", "apply"])

    def test_missing_or_external_approval_blocks_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "project"
            workspace.mkdir()
            missing = collect_dev_loop_fixture(workspace_root=workspace, scope_root=root)
            collect_approval_inbox(
                workspace_root=workspace,
                inbox_action="enqueue",
                domain="project",
                channel="workbench",
                autonomy="high",
                capability="social-post",
                action="send message",
                target="external service",
                data="sanitized proposal fields",
                effect="publish externally",
                risk="high",
                scope_root=root,
            )
            blocked = collect_dev_loop_fixture(workspace_root=workspace, scope_root=root)
        self.assertEqual(missing["overall"], "needs_approval")
        self.assertEqual(blocked["overall"], "blocked")
        self.assertIn("local non-external", blocked["reason"])
        self.assertFalse(blocked["security"]["executes_tools"])
        self.assertFalse(blocked["security"]["external_side_effects"])

    def test_rejects_traversal_out_of_scope_and_secret_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "project"
            workspace.mkdir()
            traversal = collect_dev_loop_fixture(workspace_root=workspace, inbox_file="../bad.jsonl", scope_root=root)
            out_of_scope = collect_dev_loop_fixture(workspace_root=workspace, scope_root=workspace / "nested")
            inbox = workspace / ".lai"
            inbox.mkdir()
            (inbox / "approval-inbox.jsonl").write_text(SECRET + "\n", encoding="utf-8")
            secret = collect_dev_loop_fixture(workspace_root=workspace, scope_root=root)
        self.assertEqual(traversal["overall"], "blocked")
        self.assertEqual(out_of_scope["overall"], "blocked")
        self.assertEqual(secret["overall"], "blocked")
        self.assertFalse(secret["data_touched"]["filesystem_write"])
        self.assertFalse(secret["security"]["issues_grants"])

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            workspace = root / "project"
            workspace.mkdir()
            enqueue = self._enqueue_local_dev(workspace, root)
            approval_id = enqueue["inbox"]["entries"][0]["approval_id"]
            payload = collect_dev_loop_fixture(workspace_root=workspace, approval_id=approval_id, phase="review", scope_root=root)
            text = render_dev_loop_fixture(payload)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "dev-loop-fixture",
                    "--workspace-root",
                    str(workspace),
                    "--approval-id",
                    approval_id,
                    "--phase",
                    "review",
                    "--json",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        cli_payload = json.loads(result.stdout)
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(cli_payload["operation"], "dev-loop-fixture")
        self.assertEqual(cli_payload["schema_version"], "dev-loop-fixture/v1")
        self.assertEqual(cli_payload["phase"], "review")
        self.assertIn("dev-loop-fixture/v1", text)
        for output in (result.stdout, result.stderr, text):
            self.assertNotIn("Bearer", output)
            self.assertNotIn(SECRET, output)


if __name__ == "__main__":
    unittest.main()
