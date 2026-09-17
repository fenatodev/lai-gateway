from __future__ import annotations

import json
import subprocess
import sys
import unittest

from lai_gateway.external_capability_gate import collect_external_capability_gate, render_external_capability_gate


class ExternalCapabilityGateTest(unittest.TestCase):
    def test_selects_public_source_inspection_without_enabling_runtime(self) -> None:
        payload = collect_external_capability_gate(candidate="browser.public_source_inspection")
        self.assertEqual(payload["operation"], "external-capability-gate")
        self.assertEqual(payload["schema_version"], "external-capability-gate/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["decision"], "go_for_limited_public_read_only_candidate")
        self.assertTrue(payload["selected_candidate_go"])
        self.assertFalse(payload["selected_candidate_enabled_by_gate"])
        self.assertFalse(payload["external_capability_enabled"])
        self.assertFalse(payload["effective_authorization"])
        security = payload["security"]
        self.assertTrue(security["read_only"])
        self.assertFalse(security["network_access"])
        self.assertFalse(security["uses_authenticated_browser"])
        self.assertFalse(security["uses_cookies"])
        self.assertFalse(security["executes_tools"])
        self.assertFalse(security["dispatches_adapter"])
        self.assertFalse(security["issues_grants"])
        self.assertFalse(security["consumes_grants"])

    def test_sensitive_candidates_remain_no_go(self) -> None:
        for candidate in (
            "browser.authenticated_session",
            "n8n.execute_workflow",
            "mcp.call_tool",
            "social_career.send_message",
        ):
            payload = collect_external_capability_gate(candidate=candidate)
            self.assertEqual(payload["overall"], "blocked", candidate)
            self.assertEqual(payload["decision"], "no_go_for_selected_candidate")
            self.assertFalse(payload["selected_candidate_go"])
            self.assertFalse(payload["external_capability_enabled"])
            self.assertFalse(payload["security"]["uses_credentials"])
            self.assertFalse(payload["security"]["executes_tools"])
            self.assertFalse(payload["security"]["sends_messages"])

    def test_unknown_candidate_fails_closed(self) -> None:
        payload = collect_external_capability_gate(candidate="browser.cookies.now")
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["selected_candidate_go"])
        self.assertIn("candidate is not in the explicit PR120 catalog", json.dumps(payload))

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_external_capability_gate(candidate="browser.authenticated_session")
        rendered = render_external_capability_gate(payload)
        self.assertIn("external-capability-gate/v1", rendered)
        self.assertIn("external_capability_enabled: false", rendered)
        self.assertIn("uses_credentials: false", rendered)
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "external-capability-gate", "--candidate", "browser.public_source_inspection", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["schema_version"], "external-capability-gate/v1")
        self.assertNotIn("Bearer", result.stdout + result.stderr)
        self.assertNotIn("sk-", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
