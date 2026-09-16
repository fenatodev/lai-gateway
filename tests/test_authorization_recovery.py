from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lai_gateway.authorization_recovery import collect_authorization_recovery, render_authorization_recovery

from .fake_harness import TOKEN


BASE_REQUEST = {
    "adapter_id": "local_status",
    "requested_capability": "local_status.status",
    "actor": "user",
    "channel": "workbench",
    "domain": "governance",
    "action": "safe status check",
    "parameters": {"label": "public"},
    "approval_intent": True,
    "approved_by": "user",
}


class AuthorizationRecoveryTest(unittest.TestCase):
    def _issue(self, root: Path, **overrides: object) -> dict[str, object]:
        request = BASE_REQUEST | overrides
        return collect_authorization_recovery(
            recovery_action="issue",
            authorization_dir=root / "auth",
            scope_root=root,
            ttl_seconds=60,
            **request,
        )

    def test_issue_and_check_recovers_active_grant_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = self._issue(root)
            self.assertEqual(issued["status"], "issued")
            self.assertTrue(issued["authorization_persisted"])
            grant_id = str(issued["authorization_grant_id"])
            recovered = collect_authorization_recovery(
                recovery_action="check",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **BASE_REQUEST,
            )
        self.assertEqual(recovered["status"], "active")
        self.assertTrue(recovered["authorization_active"])
        self.assertTrue(recovered["recovered_after_restart"])
        self.assertFalse(recovered["retry_automatic"])

    def test_consume_is_single_use_and_blocks_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = self._issue(root)
            grant_id = str(issued["authorization_grant_id"])
            first = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **BASE_REQUEST,
            )
            second = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **BASE_REQUEST,
            )
        self.assertEqual(first["status"], "consumed_for_single_use")
        self.assertTrue(first["dispatch_allowed"])
        self.assertTrue(first["authorization_consumed"])
        self.assertEqual(second["status"], "blocked")
        self.assertFalse(second["dispatch_allowed"])
        self.assertIn("already consumed", second["reason"])

    def test_expired_grant_cannot_be_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued_at = datetime(2026, 1, 1, tzinfo=UTC)
            issued = collect_authorization_recovery(
                recovery_action="issue",
                authorization_dir=root / "auth",
                scope_root=root,
                ttl_seconds=1,
                now_utc=issued_at,
                **BASE_REQUEST,
            )
            expired = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=str(issued["authorization_grant_id"]),
                authorization_dir=root / "auth",
                scope_root=root,
                now_utc=issued_at + timedelta(seconds=2),
                **BASE_REQUEST,
            )
        self.assertEqual(expired["status"], "blocked")
        self.assertIn("expired", expired["reason"])
        self.assertFalse(expired["dispatch_allowed"])

    def test_revoked_grant_cannot_be_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = self._issue(root)
            grant_id = str(issued["authorization_grant_id"])
            revoked = collect_authorization_recovery(
                recovery_action="revoke",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **BASE_REQUEST,
            )
            consumed = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **BASE_REQUEST,
            )
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(consumed["status"], "blocked")
        self.assertIn("revoked", consumed["reason"])

    def test_forged_or_changed_request_cannot_consume_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issued = self._issue(root)
            grant_id = str(issued["authorization_grant_id"])
            forged = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                claimed_user_id="other-user",
                **BASE_REQUEST,
            )
            changed = collect_authorization_recovery(
                recovery_action="consume",
                authorization_grant_id=grant_id,
                authorization_dir=root / "auth",
                scope_root=root,
                **(BASE_REQUEST | {"action": "different local status check"}),
            )
        self.assertEqual(forged["status"], "blocked")
        self.assertIn("not effectively authorized", forged["reason"])
        self.assertEqual(changed["status"], "blocked")
        self.assertIn("action_sha256", changed["reason"])

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = self._issue(root, action="use private bearer value", parameters={"api_key": "private-value"})
            rendered = render_authorization_recovery(payload)
        self.assertIn("authorization-recovery", rendered)
        self.assertNotIn("private-value", json.dumps(payload, sort_keys=True))
        self.assertNotIn("use private bearer value", json.dumps(payload, sort_keys=True))
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "authorization-recovery",
                "--recovery-action",
                "issue",
                "--adapter",
                "local_status",
                "--capability",
                "local_status.status",
                "--operation-scope",
                "local-status-read",
                "--action",
                "use private bearer value",
                "--authorization-dir",
                "state/test-authorization-recovery-cli",
                "--approve",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("use private bearer value", result.stdout)
        self.assertNotIn(TOKEN, result.stdout)


if __name__ == "__main__":
    unittest.main()
