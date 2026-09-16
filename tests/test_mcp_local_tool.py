from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.mcp_local_tool import collect_mcp_local_tool, render_mcp_local_tool

from .fake_harness import TOKEN


class McpLocalToolTest(unittest.TestCase):
    def test_plan_is_exact_scope_without_execution_or_external_effects(self) -> None:
        payload = collect_mcp_local_tool(mcp_action="plan")
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["schema_version"], "mcp-local-tool/v1")
        self.assertEqual(payload["adapter_id"], "mcp_local")
        self.assertEqual(payload["requested_capability"], "mcp.local_echo_digest")
        self.assertEqual(payload["operation_scope"], "mcp-local-safe-tool")
        self.assertTrue(payload["effective"]["scope_authorized"])
        self.assertTrue(payload["effective"]["identity_verified"])
        self.assertFalse(payload["local_tool_executed"])
        self.assertFalse(payload["external_side_effects"])
        self.assertFalse(payload["security"]["calls_upstream_mcp"])
        self.assertFalse(payload["security"]["broad_mcp_tool_execution"])
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("Bearer", text)

    def test_issue_run_and_replay_block_are_single_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = hashlib.sha256(b"public-local-mcp").hexdigest()
            issued = collect_mcp_local_tool(
                mcp_action="issue",
                authorization_dir=root / "auth",
                scope_root=root,
                payload_sha256=digest,
            )
            grant_id = str(issued["authorization_grant_id"])
            first = collect_mcp_local_tool(
                mcp_action="run",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                payload_sha256=digest,
            )
            second = collect_mcp_local_tool(
                mcp_action="run",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                payload_sha256=digest,
            )
        self.assertEqual(issued["status"], "issued")
        self.assertEqual(first["status"], "executed_local_mcp_tool")
        self.assertTrue(first["local_tool_executed"])
        self.assertEqual(first["handler_result"]["payload_sha256"], digest)
        self.assertEqual(first["authorization_consume"]["status"], "consumed_for_single_use")
        self.assertEqual(second["overall"], "blocked")
        self.assertFalse(second["local_tool_executed"])
        self.assertIn("already consumed", second["reason"])

    def test_changed_payload_digest_cannot_consume_existing_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_digest = hashlib.sha256(b"first").hexdigest()
            second_digest = hashlib.sha256(b"second").hexdigest()
            issued = collect_mcp_local_tool(
                mcp_action="issue",
                authorization_dir=root / "auth",
                scope_root=root,
                payload_sha256=first_digest,
            )
            changed = collect_mcp_local_tool(
                mcp_action="run",
                authorization_grant_id=str(issued["authorization_grant_id"]),
                authorization_dir=root / "auth",
                scope_root=root,
                payload_sha256=second_digest,
            )
        self.assertEqual(changed["overall"], "blocked")
        self.assertIn("parameters_sha256", changed["reason"])
        self.assertFalse(changed["local_tool_executed"])

    def test_forged_identity_cannot_run_local_mcp_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = collect_mcp_local_tool(mcp_action="issue", authorization_dir=root / "auth", scope_root=root)
            forged = collect_mcp_local_tool(
                mcp_action="run",
                authorization_grant_id=str(issued["authorization_grant_id"]),
                authorization_dir=root / "auth",
                scope_root=root,
                claimed_user_id="other-user",
            )
        self.assertEqual(forged["overall"], "blocked")
        self.assertFalse(forged["local_tool_executed"])
        self.assertIn("not effectively authorized", forged["reason"])

    def test_invalid_payload_is_blocked_without_echoing_raw_value(self) -> None:
        payload = collect_mcp_local_tool(mcp_action="issue", payload_sha256="private-token-value")
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "blocked")
        self.assertIn("raw payload is not accepted", payload["reason"])
        self.assertNotIn("private-token-value", text)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_mcp_local_tool(mcp_action="plan")
        rendered = render_mcp_local_tool(payload)
        self.assertIn("mcp-local-tool", rendered)
        self.assertIn("mcp-local-safe-tool", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "mcp-local-tool", "plan", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mcp.local_echo_digest", result.stdout)
        self.assertNotIn(TOKEN, result.stdout)
        self.assertNotIn("Bearer", result.stdout)


if __name__ == "__main__":
    unittest.main()
