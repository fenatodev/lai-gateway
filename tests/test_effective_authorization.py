from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.config import GatewayConfig
from lai_gateway.effective_authorization import collect_effective_authorization, render_effective_authorization

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class EffectiveAuthorizationTest(unittest.TestCase):
    def test_validated_capture_authorizes_only_dry_run_scope(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="simulate public navigation",
            approval_intent=True,
            approved_by="user",
        )
        effective = payload["effective"]
        self.assertEqual(payload["operation"], "effective-authorization")
        self.assertEqual(effective["status"], "effective_for_dry_run_safe_operation")
        self.assertEqual(effective["operation_scope"], "adapter-dry-run")
        self.assertTrue(effective["effective_authorization"])
        self.assertTrue(effective["scope_authorized"])
        self.assertFalse(effective["adapter_capability_authorized"])
        self.assertFalse(effective["dispatch_enabled"])
        self.assertFalse(effective["adapter_dispatched"])
        self.assertFalse(effective["adapter_executed"])
        self.assertFalse(effective["executes_tools"])
        self.assertFalse(payload["authorization_persisted"])
        self.assertFalse(payload["security"]["adapter_capability_elevated"])

    def test_without_approval_intent_stays_pending(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
        )
        effective = payload["effective"]
        self.assertEqual(effective["status"], "pending")
        self.assertFalse(effective["effective_authorization"])
        self.assertFalse(effective["scope_authorized"])
        self.assertFalse(effective["adapter_capability_authorized"])

    def test_non_dry_run_scope_is_blocked(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=True,
            operation_scope="adapter-dispatch",
        )
        effective = payload["effective"]
        self.assertEqual(effective["status"], "blocked")
        self.assertFalse(effective["effective_authorization"])
        self.assertFalse(effective["scope_authorized"])
        self.assertFalse(effective["adapter_capability_authorized"])

    def test_blocked_underlying_request_cannot_become_effective(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="browser",
            requested_capability="browser.delete_everything",
            approval_intent=True,
        )
        effective = payload["effective"]
        self.assertEqual(effective["status"], "blocked")
        self.assertFalse(effective["effective_authorization"])
        self.assertEqual(effective["dry_run_status"], "blocked")

    def test_sensitive_parameter_is_not_exposed(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="n8n",
            requested_capability="n8n.plan_workflow",
            parameters={"api_key": "private-value", "name": "workflow"},
            approval_intent=True,
        )
        text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("private-value", text)
        self.assertIn("[redacted]", text)
        self.assertIn("workflow", text)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_effective_authorization(
            adapter_id="voice",
            requested_capability="voice.plan",
            approval_intent=True,
        )
        rendered = render_effective_authorization(payload)
        self.assertIn("effective-authorization", rendered)
        self.assertIn("operation_scope: adapter-dry-run", rendered)
        self.assertIn("effective_authorization: true", rendered)
        self.assertIn("adapter_capability_authorized: false", rendered)
        self.assertIn("dispatch_enabled: false", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "effective-authorization",
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
        self.assertTrue(cli_payload["effective"]["effective_authorization"])
        self.assertFalse(cli_payload["effective"]["adapter_capability_authorized"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_effective_authorization_endpoint_is_scope_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/effective-authorization?adapter=browser&capability=browser.navigate_public&approve=true"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "effective-authorization")
        self.assertTrue(payload["effective"]["effective_authorization"])
        self.assertFalse(payload["effective"]["adapter_capability_authorized"])
        self.assertFalse(payload["dispatch_enabled"])
        self.assertFalse(payload["adapter_executed"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()
