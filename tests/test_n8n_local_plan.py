import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.n8n_local_plan import collect_n8n_local_plan, render_n8n_local_plan

from .fake_harness import TOKEN


class N8nLocalPlanTest(unittest.TestCase):
    def test_plan_is_exact_scope_without_workflow_execution_or_external_effects(self) -> None:
        payload = collect_n8n_local_plan(n8n_action="plan")
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["schema_version"], "n8n-local-plan/v1")
        self.assertEqual(payload["adapter_id"], "n8n")
        self.assertEqual(payload["requested_capability"], "n8n.local_plan_digest")
        self.assertEqual(payload["operation_scope"], "n8n-local-plan")
        self.assertTrue(payload["effective"]["scope_authorized"])
        self.assertTrue(payload["effective"]["identity_verified"])
        self.assertFalse(payload["local_plan_inspected"])
        self.assertFalse(payload["workflow_executed"])
        self.assertFalse(payload["workflow_activated"])
        self.assertFalse(payload["webhook_called"])
        self.assertFalse(payload["calls_n8n_instance"])
        self.assertFalse(payload["external_side_effects"])
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("Bearer", text)

    def test_issue_inspect_and_replay_block_are_single_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = hashlib.sha256(b"public-n8n-plan").hexdigest()
            issued = collect_n8n_local_plan(
                n8n_action="issue",
                authorization_dir=root / "auth",
                scope_root=root,
                workflow_sha256=digest,
            )
            grant_id = str(issued["authorization_grant_id"])
            first = collect_n8n_local_plan(
                n8n_action="inspect",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                workflow_sha256=digest,
            )
            second = collect_n8n_local_plan(
                n8n_action="inspect",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                workflow_sha256=digest,
            )
        self.assertEqual(issued["status"], "issued")
        self.assertEqual(first["status"], "inspected_local_n8n_plan")
        self.assertTrue(first["local_plan_inspected"])
        self.assertFalse(first["workflow_executed"])
        self.assertFalse(first["calls_n8n_instance"])
        self.assertEqual(first["handler_result"]["workflow_sha256"], digest)
        self.assertEqual(first["authorization_consume"]["status"], "consumed_for_single_use")
        self.assertEqual(second["overall"], "blocked")
        self.assertFalse(second["local_plan_inspected"])
        self.assertIn("already consumed", second["reason"])

    def test_changed_workflow_digest_cannot_consume_existing_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_digest = hashlib.sha256(b"first").hexdigest()
            second_digest = hashlib.sha256(b"second").hexdigest()
            issued = collect_n8n_local_plan(
                n8n_action="issue",
                authorization_dir=root / "auth",
                scope_root=root,
                workflow_sha256=first_digest,
            )
            changed = collect_n8n_local_plan(
                n8n_action="inspect",
                authorization_grant_id=str(issued["authorization_grant_id"]),
                authorization_dir=root / "auth",
                scope_root=root,
                workflow_sha256=second_digest,
            )
        self.assertEqual(changed["overall"], "blocked")
        self.assertIn("parameters_sha256", changed["reason"])
        self.assertFalse(changed["local_plan_inspected"])

    def test_forged_identity_cannot_inspect_n8n_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = collect_n8n_local_plan(n8n_action="issue", authorization_dir=root / "auth", scope_root=root)
            forged = collect_n8n_local_plan(
                n8n_action="inspect",
                authorization_grant_id=str(issued["authorization_grant_id"]),
                authorization_dir=root / "auth",
                scope_root=root,
                claimed_user_id="other-user",
            )
        self.assertEqual(forged["overall"], "blocked")
        self.assertFalse(forged["local_plan_inspected"])
        self.assertIn("not effectively authorized", forged["reason"])

    def test_invalid_workflow_digest_is_blocked_without_echoing_raw_value(self) -> None:
        payload = collect_n8n_local_plan(n8n_action="issue", workflow_sha256="private-token-value")
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "blocked")
        self.assertIn("raw workflow JSON is not accepted", payload["reason"])
        self.assertNotIn("private-token-value", text)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_n8n_local_plan(n8n_action="plan")
        rendered = render_n8n_local_plan(payload)
        self.assertIn("n8n-local-plan", rendered)
        self.assertIn("n8n.local_plan_digest", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "n8n-local-plan", "plan", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("n8n.local_plan_digest", result.stdout)
        self.assertNotIn(TOKEN, result.stdout)
        self.assertNotIn("Bearer", result.stdout)


if __name__ == "__main__":
    unittest.main()
