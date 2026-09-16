from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.approval_inbox import collect_approval_inbox, render_approval_inbox


class ApprovalInboxTest(unittest.TestCase):
    def test_show_missing_inbox_is_empty_without_writing_or_granting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_approval_inbox(workspace_root=workspace, scope_root=Path(tmp))
            self.assertFalse((workspace / ".lai" / "approval-inbox.jsonl").exists())
        self.assertEqual(payload["operation"], "approval-inbox")
        self.assertEqual(payload["schema_version"], "approval-inbox/v1")
        self.assertEqual(payload["overall"], "empty")
        self.assertEqual(payload["inbox"]["pending_count"], 0)
        self.assertFalse(payload["data_touched"]["filesystem_write"])
        self.assertTrue(payload["security"]["read_only_when_showing"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["uses_credentials"])
        self.assertFalse(payload["security"]["sends_messages"])
        self.assertFalse(payload["security"]["publishes"])

    def test_enqueue_persists_sanitized_pending_approval_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_approval_inbox(
                workspace_root=workspace,
                inbox_action="enqueue",
                actor="user",
                domain="project",
                channel="workbench",
                autonomy="high",
                capability="approval-inbox",
                action="record pending approval",
                target=".lai/approval-inbox.jsonl",
                data="proposal fields only",
                effect="pending human review only",
                risk="low",
                scope_root=Path(tmp),
            )
            raw = (workspace / ".lai" / "approval-inbox.jsonl").read_text(encoding="utf-8")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["inbox"]["pending_count"], 1)
        entry = payload["inbox"]["entries"][0]
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["capability"], "approval-inbox")
        self.assertTrue(entry["approval_record_only"])
        self.assertFalse(entry["effective_authorization"])
        self.assertFalse(entry["issues_grants"])
        self.assertFalse(entry["consumes_grants"])
        self.assertFalse(entry["dispatches_adapter"])
        self.assertFalse(entry["executes_tools"])
        self.assertFalse(entry["external_side_effects"])
        self.assertFalse(entry["uses_credentials"])
        self.assertTrue(payload["data_touched"]["filesystem_write"])
        self.assertIn("approval-inbox/v1", raw)

    def test_secret_shapes_block_enqueue_and_do_not_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_approval_inbox(
                workspace_root=workspace,
                inbox_action="enqueue",
                domain="project",
                channel="workbench",
                autonomy="high",
                capability="approval-inbox",
                action="record pending approval",
                target=".lai/approval-inbox.jsonl",
                data="token=supersecretvalue",
                effect="pending review",
                risk="low",
                scope_root=Path(tmp),
            )
            inbox_path = workspace / ".lai" / "approval-inbox.jsonl"
        self.assertEqual(payload["overall"], "needs_proposal")
        self.assertFalse(inbox_path.exists())
        body = json.dumps(payload)
        self.assertNotIn("supersecretvalue", body)
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["executes_tools"])

    def test_rejects_traversal_absolute_out_of_scope_and_secret_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = Path(tmp)
            workspace = scope / "project"
            workspace.mkdir()
            outside = scope / "outside"
            outside.mkdir()
            self.assertEqual(collect_approval_inbox(workspace_root=outside, scope_root=workspace)["overall"], "blocked")
            self.assertEqual(collect_approval_inbox(workspace_root=workspace, inbox_file="../x.jsonl", scope_root=scope)["overall"], "blocked")
            self.assertEqual(collect_approval_inbox(workspace_root=workspace, inbox_file=str(scope / "x.jsonl"), scope_root=scope)["overall"], "blocked")
            inbox_dir = workspace / ".lai"
            inbox_dir.mkdir()
            secret_inbox = inbox_dir / "approval-inbox.jsonl"
            secret_inbox.write_text('{"schema_version":"approval-inbox/v1","action":"token=supersecretvalue"}\n', encoding="utf-8")
            payload = collect_approval_inbox(workspace_root=workspace, scope_root=scope)
        self.assertEqual(payload["overall"], "blocked")
        self.assertNotIn("supersecretvalue", json.dumps(payload))

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_approval_inbox(
                workspace_root=workspace,
                inbox_action="enqueue",
                domain="project",
                channel="cli",
                autonomy="none",
                capability="approval-inbox",
                action="record pending approval",
                target=".lai/approval-inbox.jsonl",
                data="explicit proposal fields",
                effect="record only",
                risk="low",
                scope_root=Path(tmp),
            )
            text = render_approval_inbox(payload)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "approval-inbox",
                    "--workspace-root",
                    str(workspace),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "approval-inbox")
        self.assertEqual(cli_payload["schema_version"], "approval-inbox/v1")
        self.assertIn("approval-inbox/v1", text)
        self.assertIn("effective_authorization: false", text)
        self.assertNotIn("Bearer", result.stdout)
        self.assertNotIn("token=", result.stdout)


if __name__ == "__main__":
    unittest.main()
