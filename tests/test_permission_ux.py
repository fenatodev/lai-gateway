import json
import subprocess
import sys
import unittest

from lai_gateway.permission_ux import collect_permission_ux, render_permission_ux


class PermissionUxTest(unittest.TestCase):
    def test_flow_distinguishes_intent_decision_effective_grant_and_execution(self) -> None:
        payload = collect_permission_ux(
            adapter_id="local_status",
            requested_capability="local_status.status",
            actor="user",
            channel="workbench",
            domain="governance",
            action="consultar status local seguro",
            approval_intent=True,
            approved_by="workbench",
            operation_scope="local-status-read",
        )
        self.assertEqual(payload["operation"], "permission-ux")
        self.assertEqual(payload["schema_version"], "permission-ux/v1")
        self.assertEqual([stage["stage_id"] for stage in payload["stages"]], [
            "intent",
            "identity",
            "decision",
            "record",
            "approval_capture",
            "effective_authorization",
            "single_use_grant",
            "execution",
        ])
        self.assertEqual(payload["decision"]["outcome"], "allow")
        self.assertTrue(payload["effective"]["effective_authorization"])
        self.assertEqual(payload["grant"]["status"], "missing")
        self.assertFalse(payload["grant"]["checked"])
        self.assertFalse(payload["grant"]["issued"])
        self.assertFalse(payload["grant"]["consumed"])
        self.assertFalse(payload["execution"]["dispatch_requested"])
        self.assertFalse(payload["execution"]["adapter_executed"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["external_side_effects"])

    def test_blocked_or_external_capability_stays_non_executing(self) -> None:
        payload = collect_permission_ux(
            adapter_id="n8n",
            requested_capability="n8n.activate_workflow",
            actor="user",
            channel="workbench",
            domain="automation",
            action="ativar workflow n8n real",
            approval_intent=True,
            approved_by="workbench",
            operation_scope="n8n-local-plan",
        )
        self.assertNotEqual(payload["decision"]["outcome"], "allow")
        self.assertFalse(payload["effective"]["effective_authorization"])
        self.assertFalse(payload["execution"]["adapter_executed"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertIn("execução", "\n".join(stage["label"].lower() for stage in payload["stages"]))

    def test_supplied_grant_is_marked_unverified_without_store_access(self) -> None:
        payload = collect_permission_ux(
            adapter_id="local_status",
            requested_capability="local_status.status",
            actor="user",
            channel="workbench",
            domain="governance",
            action="consultar status local seguro",
            approval_intent=True,
            approved_by="workbench",
            operation_scope="local-status-read",
            authorization_grant_id="agr-example",
        )
        self.assertEqual(payload["grant"]["status"], "provided_unverified")
        self.assertFalse(payload["grant"]["checked"])
        self.assertFalse(payload["grant"]["consumed"])
        self.assertFalse(payload["execution"]["adapter_executed"])

    def test_render_and_cli_are_secret_free(self) -> None:
        secret = "sk-test-secret-value"
        payload = collect_permission_ux(
            adapter_id="local_status",
            requested_capability="local_status.status",
            actor="user",
            channel="cli",
            domain="governance",
            action=secret,
            parameters={"token": secret},
            approval_intent=True,
            approved_by="cli",
            operation_scope="local-status-read",
        )
        text = render_permission_ux(payload)
        self.assertNotIn(secret, json.dumps(payload))
        self.assertNotIn(secret, text)
        self.assertIn("permission-ux/v1", text)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "permission-ux",
                "--adapter",
                "local_status",
                "--capability",
                "local_status.status",
                "--action",
                secret,
                "--param",
                f"token={secret}",
                "--approve",
                "--approved-by",
                "cli",
                "--operation-scope",
                "local-status-read",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertNotIn(secret, result.stdout)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "permission-ux")
        self.assertFalse(cli_payload["security"]["issues_grants"])


if __name__ == "__main__":
    unittest.main()
