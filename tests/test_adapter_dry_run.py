from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.adapter_dry_run import collect_adapter_dry_run, render_adapter_dry_run
from lai_gateway.config import GatewayConfig

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class AdapterDryRunTest(unittest.TestCase):
    def test_declared_capability_gets_simulated_dry_run_without_dispatch(self) -> None:
        payload = collect_adapter_dry_run(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
        )
        dry_run = payload["dry_run"]
        self.assertEqual(payload["operation"], "adapter-dry-run")
        self.assertEqual(dry_run["status"], "simulated")
        self.assertTrue(dry_run["dry_run_executed"])
        self.assertTrue(dry_run["requires_human_approval"])
        self.assertFalse(dry_run["effective_authorization"])
        self.assertFalse(dry_run["dispatch_enabled"])
        self.assertFalse(dry_run["adapter_dispatched"])
        self.assertFalse(dry_run["adapter_executed"])
        self.assertFalse(payload["security"]["dry_run_elevates_permissions"])
        self.assertEqual(payload["audit"]["event_count"], 4)
        self.assertEqual(len(dry_run["audit_event_ids"]), 4)
        self.assertIn("planned browser browser.navigate_public", dry_run["simulated_result"])

    def test_missing_adapter_is_blocked_before_dry_run_execution(self) -> None:
        payload = collect_adapter_dry_run(
            adapter_id="missing",
            requested_capability="missing.call",
        )
        dry_run = payload["dry_run"]
        self.assertEqual(dry_run["status"], "blocked")
        self.assertFalse(dry_run["dry_run_executed"])
        self.assertEqual(dry_run["simulated_result"], "not_run")
        self.assertFalse(dry_run["adapter_dispatched"])

    def test_undeclared_capability_is_blocked(self) -> None:
        payload = collect_adapter_dry_run(
            adapter_id="browser",
            requested_capability="browser.delete_everything",
        )
        dry_run = payload["dry_run"]
        self.assertEqual(dry_run["status"], "blocked")
        self.assertEqual(dry_run["decision_outcome"], "deny")
        self.assertFalse(dry_run["dry_run_executed"])
        self.assertFalse(dry_run["dispatch_enabled"])

    def test_input_parameters_do_not_leak_sensitive_values(self) -> None:
        payload = collect_adapter_dry_run(
            adapter_id="n8n",
            requested_capability="n8n.plan_workflow",
            parameters={"api_key": "private-value", "name": "lead workflow"},
        )
        text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("private-value", text)
        self.assertIn("[redacted]", text)
        self.assertIn("lead workflow", text)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_adapter_dry_run(
            adapter_id="voice",
            requested_capability="voice.plan",
            parameters={"topic": "daily brief"},
        )
        rendered = render_adapter_dry_run(payload)
        self.assertIn("adapter-dry-run", rendered)
        self.assertIn("dry_run_only: true", rendered)
        self.assertIn("dispatch_enabled: false", rendered)
        self.assertIn("adapter_dispatched: false", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "adapter-dry-run",
                "--adapter",
                "voice",
                "--capability",
                "voice.plan",
                "--param",
                "topic=daily brief",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["dry_run"]["status"], "simulated")
        self.assertFalse(cli_payload["dry_run"]["adapter_dispatched"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_adapter_dry_run_endpoint_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/adapter-dry-run?adapter=browser&capability=browser.navigate_public"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "adapter-dry-run")
        self.assertEqual(payload["dry_run"]["status"], "simulated")
        self.assertFalse(payload["dry_run"]["adapter_dispatched"])
        self.assertFalse(payload["dry_run"]["effective_authorization"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()
