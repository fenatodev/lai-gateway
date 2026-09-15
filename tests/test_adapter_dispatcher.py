from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.adapter_dispatcher import (
    collect_adapter_dispatcher_interface,
    render_adapter_dispatcher_interface,
)
from lai_gateway.config import GatewayConfig

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class AdapterDispatcherInterfaceTest(unittest.TestCase):
    def test_authorized_dry_run_scope_still_does_not_dispatch(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=True,
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(payload["operation"], "adapter-dispatcher")
        self.assertEqual(dispatcher["status"], "planned_not_dispatched")
        self.assertTrue(dispatcher["effective_authorization"])
        self.assertTrue(dispatcher["scope_authorized"])
        self.assertFalse(dispatcher["adapter_capability_authorized"])
        self.assertFalse(dispatcher["dispatch_permitted"])
        self.assertFalse(dispatcher["handler_registered"])
        self.assertFalse(dispatcher["adapter_dispatched"])
        self.assertFalse(dispatcher["adapter_executed"])
        self.assertEqual(payload["result"], "not_dispatched")

    def test_dispatch_request_is_blocked_without_registered_handler(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=True,
            dispatch_requested=True,
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "blocked")
        self.assertTrue(dispatcher["dispatch_requested"])
        self.assertFalse(dispatcher["dispatch_permitted"])
        self.assertFalse(dispatcher["handler_registered"])
        self.assertFalse(dispatcher["adapter_dispatched"])

    def test_without_approval_remains_pending(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "pending")
        self.assertFalse(dispatcher["effective_authorization"])
        self.assertFalse(dispatcher["dispatch_permitted"])
        self.assertFalse(dispatcher["adapter_dispatched"])

    def test_non_dry_run_scope_is_blocked(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=True,
            operation_scope="browser-real",
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "blocked")
        self.assertFalse(dispatcher["dispatch_permitted"])

    def test_missing_adapter_is_blocked(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="missing",
            requested_capability="missing.call",
            approval_intent=True,
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "blocked")
        self.assertEqual(dispatcher["adapter_status"], "missing")
        self.assertFalse(dispatcher["dispatch_permitted"])

    def test_local_status_plans_registered_handler_without_dispatch(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="local_status",
            requested_capability="local_status.status",
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "planned_local_handler")
        self.assertTrue(dispatcher["handler_registered"])
        self.assertFalse(dispatcher["dispatch_permitted"])
        self.assertFalse(dispatcher["adapter_dispatched"])
        self.assertFalse(dispatcher["adapter_executed"])
        self.assertIsNone(payload["handler_result"])

    def test_local_status_dispatch_executes_only_in_process_handler(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="local_status",
            requested_capability="local_status.status",
            action="safe status check",
            parameters={"label": "public"},
            dispatch_requested=True,
        )
        dispatcher = payload["dispatcher"]
        self.assertEqual(dispatcher["status"], "dispatched_local")
        self.assertTrue(dispatcher["dispatch_permitted"])
        self.assertTrue(dispatcher["handler_registered"])
        self.assertTrue(dispatcher["adapter_dispatched"])
        self.assertTrue(dispatcher["adapter_executed"])
        self.assertFalse(dispatcher["executes_tools"])
        self.assertFalse(dispatcher["external_side_effects"])
        self.assertEqual(payload["result"], "local_status")
        self.assertEqual(payload["handler_result"]["status"], "ok")

    def test_sensitive_action_and_parameters_are_not_exposed(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="n8n",
            requested_capability="n8n.plan_workflow",
            action="use private bearer value",
            parameters={"api_key": "private-value", "name": "workflow"},
            approval_intent=True,
        )
        text = json.dumps(payload, sort_keys=True)
        self.assertNotIn("private-value", text)
        self.assertNotIn("use private bearer value", text)
        self.assertIn("action_sha256", text)
        self.assertFalse(payload["security"]["dispatches_adapter"])

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_adapter_dispatcher_interface(
            adapter_id="voice",
            requested_capability="voice.plan",
            approval_intent=True,
        )
        rendered = render_adapter_dispatcher_interface(payload)
        self.assertIn("adapter-dispatcher", rendered)
        self.assertIn("interface_only: true", rendered)
        self.assertIn("dispatch_permitted: false", rendered)
        self.assertIn("adapter_dispatched: false", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "adapter-dispatcher",
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
        self.assertEqual(cli_payload["dispatcher"]["status"], "planned_not_dispatched")
        self.assertFalse(cli_payload["dispatcher"]["dispatch_permitted"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_endpoint_is_non_dispatching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/adapter-dispatcher?adapter=browser&capability=browser.navigate_public&approve=true"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "adapter-dispatcher")
        self.assertEqual(payload["dispatcher"]["status"], "planned_not_dispatched")
        self.assertFalse(payload["dispatcher"]["dispatch_permitted"])
        self.assertFalse(payload["dispatcher"]["adapter_dispatched"])
        self.assertFalse(payload["dispatcher"]["adapter_executed"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()

