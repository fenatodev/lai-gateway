from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.authorization_capture import (
    collect_authorization_capture_stub,
    render_authorization_capture_stub,
)
from lai_gateway.config import GatewayConfig

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class AuthorizationCaptureStubTest(unittest.TestCase):
    def test_capture_intent_is_recorded_but_not_effective(self) -> None:
        payload = collect_authorization_capture_stub(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="approve public navigation plan",
            approval_intent=True,
        )
        capture = payload["capture"]
        self.assertEqual(payload["operation"], "authorization-capture-stub")
        self.assertEqual(capture["status"], "captured_non_effective")
        self.assertTrue(capture["approval_intent"])
        self.assertTrue(capture["approval_captured"])
        self.assertFalse(capture["approval_validated"])
        self.assertFalse(capture["effective_authorization"])
        self.assertFalse(capture["capture_persisted"])
        self.assertFalse(capture["dispatch_enabled"])
        self.assertFalse(capture["adapter_executed"])
        self.assertFalse(payload["security"]["capture_elevates_permissions"])

    def test_without_explicit_intent_capture_stays_pending(self) -> None:
        payload = collect_authorization_capture_stub(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
        )
        capture = payload["capture"]
        self.assertEqual(capture["status"], "pending")
        self.assertFalse(capture["approval_intent"])
        self.assertFalse(capture["approval_captured"])
        self.assertFalse(capture["effective_authorization"])

    def test_blocked_request_cannot_be_approved_by_stub(self) -> None:
        payload = collect_authorization_capture_stub(
            adapter_id="browser",
            requested_capability="browser.remove_files",
            approval_intent=True,
        )
        capture = payload["capture"]
        self.assertEqual(capture["status"], "blocked")
        self.assertFalse(capture["approval_captured"])
        self.assertFalse(capture["effective_authorization"])
        self.assertEqual(capture["decision_outcome"], "deny")

    def test_capture_stub_does_not_expose_sensitive_parameter_values(self) -> None:
        payload = collect_authorization_capture_stub(
            adapter_id="n8n",
            requested_capability="n8n.plan_workflow",
            parameters={"api_key": "private-value", "name": "safe workflow"},
            approval_intent=True,
            approved_by="operator",
        )
        text = json.dumps(payload, sort_keys=True)
        self.assertIn("[redacted]", text)
        self.assertIn("safe workflow", text)
        self.assertNotIn("private-value", text)
        self.assertFalse(payload["capture"]["effective_authorization"])

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_authorization_capture_stub(
            adapter_id="voice",
            requested_capability="voice.plan",
            approval_intent=True,
            approved_by="operator",
        )
        rendered = render_authorization_capture_stub(payload)
        self.assertIn("authorization-capture-stub", rendered)
        self.assertIn("approval_captured: true", rendered)
        self.assertIn("effective_authorization: false", rendered)
        self.assertIn("dispatch_enabled: false", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "authorization-capture-stub",
                "--adapter",
                "voice",
                "--capability",
                "voice.plan",
                "--approval-intent",
                "--approved-by",
                "operator",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["capture"]["status"], "captured_non_effective")
        self.assertFalse(cli_payload["capture"]["effective_authorization"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_authorization_capture_stub_endpoint_is_non_effective(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/authorization-capture-stub?adapter=browser&capability=browser.navigate_public&approval_intent=confirm"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "authorization-capture-stub")
        self.assertEqual(payload["capture"]["status"], "captured_non_effective")
        self.assertFalse(payload["capture"]["effective_authorization"])
        self.assertFalse(payload["capture"]["dispatch_enabled"])
        self.assertFalse(payload["security"]["persists_authorization"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()
