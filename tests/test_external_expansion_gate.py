import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.external_expansion import collect_external_expansion_gate, render_external_expansion_gate

ROOT = Path(__file__).resolve().parents[1]


class ExternalExpansionGateTest(unittest.TestCase):
    def test_gate_blocks_external_effects_without_enabling_capabilities(self) -> None:
        payload = collect_external_expansion_gate(repo=ROOT)
        self.assertEqual(payload["operation"], "external-expansion-gate")
        self.assertEqual(payload["schema_version"], "external-expansion-gate/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["decision"], "no_go_for_external_effects")
        self.assertFalse(payload["external_expansion_allowed"])
        self.assertFalse(payload["external_capabilities_enabled"])
        self.assertFalse(payload["publication_allowed"])
        self.assertTrue(payload["human_publication_approval_required"])
        self.assertEqual(payload["domain"], "external_capability_governance")
        self.assertEqual(payload["channel"], "cli_gateway_workbench")
        self.assertEqual(payload["autonomy"], "read_only_go_no_go")
        self.assertEqual(payload["capability"], "external_expansion.go_no_go_check")
        blocked = {item["capability"] for item in payload["blocked_external_capabilities"]}
        for capability in (
            "browser.authenticated_session",
            "n8n.activate_workflow",
            "n8n.execute_workflow",
            "mcp.call_tool",
            "credentials.use",
            "social_career.send_message",
            "publication.release_or_announcement",
        ):
            self.assertIn(capability, blocked)
        self.assertTrue(all(check["status"] == "ok" for check in payload["checks"]), payload["checks"])

    def test_runtime_evidence_keeps_limited_paths_narrow(self) -> None:
        payload = collect_external_expansion_gate(repo=ROOT)
        evidence = payload["runtime_evidence"]
        self.assertFalse(evidence["public_browser"]["fetch_attempted"])
        self.assertFalse(evidence["public_browser"]["network_calls"])
        self.assertFalse(evidence["public_browser"]["credentialed_access"])
        self.assertFalse(evidence["mcp_local"]["local_tool_executed"])
        self.assertFalse(evidence["mcp_local"]["executes_upstream_mcp_tools"])
        self.assertFalse(evidence["n8n_local_plan"]["workflow_executed"])
        self.assertFalse(evidence["n8n_local_plan"]["workflow_activated"])
        self.assertFalse(evidence["n8n_local_plan"]["calls_n8n_instance"])
        self.assertFalse(evidence["blocked_permission_ux"]["effective_authorization"])
        self.assertFalse(evidence["blocked_permission_ux"]["adapter_executed"])
        self.assertFalse(payload["security"]["network_access"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])

    def test_missing_docs_blocks_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs" / "product").mkdir(parents=True)
            (repo / "README.md").write_text("external-expansion-gate/v1", encoding="utf-8")
            payload = collect_external_expansion_gate(repo=repo)
        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["decision"], "blocked_by_missing_evidence")
        self.assertTrue(any(check["status"] == "fail" and check["name"].startswith("doc:") for check in payload["checks"]))
        self.assertFalse(payload["external_expansion_allowed"])

    def test_render_and_cli_are_secret_free(self) -> None:
        secret = "sk-test-secret-value"
        payload = collect_external_expansion_gate(repo=ROOT)
        rendered = render_external_expansion_gate(payload)
        encoded = json.dumps(payload)
        self.assertNotIn(secret, encoded + rendered)
        self.assertNotIn("Bearer", encoded + rendered)
        self.assertNotIn("ghp_", encoded + rendered)
        self.assertIn("external-expansion-gate/v1", rendered)
        self.assertIn("external_expansion_allowed: false", rendered)
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "external-expansion-gate", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertNotIn(secret, result.stdout)
        self.assertNotIn("Bearer", result.stdout)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "external-expansion-gate")
        self.assertFalse(cli_payload["security"]["uses_credentials"])
        self.assertFalse(cli_payload["security"]["sends_messages"])


if __name__ == "__main__":
    unittest.main()
