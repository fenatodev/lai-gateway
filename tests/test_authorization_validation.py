from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.authorization_validation import (
    collect_authorization_validation_gate,
    render_authorization_validation_gate,
)
from lai_gateway.config import GatewayConfig

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class AuthorizationValidationGateTest(unittest.TestCase):
    def test_captured_approval_validates_but_stays_non_effective(self) -> None:
        payload = collect_authorization_validation_gate(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
            approval_intent=True,
            approved_by="fernando",
        )
        validation = payload["validation"]
        self.assertEqual(payload["operation"], "authorization-validation-gate")
        self.assertEqual(validation["status"], "validated_non_effective")
        self.assertTrue(validation["approval_captured"])
        self.assertTrue(validation["approval_validated"])
        self.assertFalse(validation["effective_authorization"])
        self.assertFalse(validation["validation_persisted"])
        self.assertFalse(validation["dispatch_enabled"])
        self.assertFalse(validation["adapter_dispatched"])

    def test_without_capture_gate_stays_pending(self) -> None:
        payload = collect_authorization_validation_gate(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=False,
        )
        validation = payload["validation"]
        self.assertEqual(validation["status"], "pending")
        self.assertFalse(validation["approval_captured"])
        self.assertFalse(validation["approval_validated"])
        self.assertFalse(validation["effective_authorization"])

    def test_blocked_request_cannot_validate(self) -> None:
        payload = collect_authorization_validation_gate(
            adapter_id="browser",
            requested_capability="browser.delete_everything",
            approval_intent=True,
        )
        validation = payload["validation"]
        self.assertEqual(validation["status"], "blocked")
        self.assertFalse(validation["approval_validated"])
        self.assertEqual(validation["decision_outcome"], "deny")
        self.assertFalse(validation["dispatch_enabled"])

    def test_sensitive_parameter_is_not_exposed(self) -> None:
        payload = collect_authorization_validation_gate(
            adapter_id="n8n",
            requested_capability="n8n.plan_workflow",
            parameters={"api_key": "private-value", "name": "lead workflow"},
            approval_intent=True,
        )
        text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("private-value", text)
        self.assertIn("[redacted]", text)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_authorization_validation_gate(
            adapter_id="voice",
            requested_capability="voice.plan",
            approval_intent=True,
            approved_by="user",
        )
        rendered = render_authorization_validation_gate(payload)
        self.assertIn("authorization-validation-gate", rendered)
        self.assertIn("approval_validated: true", rendered)
        self.assertIn("effective_authorization: false", rendered)
        self.assertIn("dispatch_enabled: false", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "authorization-validation-gate",
                "--adapter",
                "voice",
                "--capability",
                "voice.plan",
                "--approve",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["validation"]["status"], "validated_non_effective")
        self.assertTrue(cli_payload["validation"]["approval_validated"])
        self.assertFalse(cli_payload["validation"]["effective_authorization"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_authorization_validation_endpoint_is_non_effective(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/authorization-validation-gate?adapter=browser&capability=browser.navigate_public&approve=true"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "authorization-validation-gate")
        self.assertTrue(payload["validation"]["approval_validated"])
        self.assertFalse(payload["validation"]["effective_authorization"])
        self.assertFalse(payload["validation"]["adapter_dispatched"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()
