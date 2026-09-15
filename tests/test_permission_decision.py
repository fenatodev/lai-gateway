import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.config import GatewayConfig
from lai_gateway.permission_decision import collect_permission_decision, render_permission_decision
from lai_gateway.server import GatewayHTTPServer

from .fake_harness import TOKEN, fake_harness


class RunningGateway:
    def __init__(self, config: GatewayConfig):
        self.server = GatewayHTTPServer(("127.0.0.1", 0), config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "RunningGateway":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def read_url(url: str) -> tuple[int, dict[str, str], str]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=5) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        return response.status, headers, response.read().decode("utf-8")


class PermissionDecisionTest(unittest.TestCase):
    def test_declared_but_ungranted_adapter_capability_requires_approval(self) -> None:
        payload = collect_permission_decision(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
        )
        decision = payload["decision"]
        self.assertEqual(payload["operation"], "permission-decision")
        self.assertTrue(payload["policy_only"])
        self.assertEqual(decision["outcome"], "requires_approval")
        self.assertEqual(decision["requested_capability"], "browser.navigate_public")
        self.assertIsNone(decision["granted_capability"])
        self.assertGreaterEqual(decision["risk_level"], 3)
        self.assertTrue(decision["requires_human_approval"])
        self.assertFalse(decision["grants_permission"])
        self.assertFalse(decision["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_unknown_capability_is_denied_without_execution(self) -> None:
        payload = collect_permission_decision(adapter_id="browser", requested_capability="browser.secret_mode")
        decision = payload["decision"]
        self.assertEqual(decision["outcome"], "deny")
        self.assertEqual(decision["reason"], "requested capability is not declared by adapter contract")
        self.assertFalse(decision["requires_human_approval"])
        self.assertFalse(payload["executes_tools"])

    def test_missing_adapter_is_denied(self) -> None:
        payload = collect_permission_decision(adapter_id="missing", requested_capability="missing.plan")
        decision = payload["decision"]
        self.assertEqual(decision["outcome"], "deny")
        self.assertEqual(decision["reason"], "adapter is not registered")
        self.assertFalse(decision["grants_permission"])

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_permission_decision(
            collect_permission_decision(adapter_id="n8n", requested_capability="n8n.activate_workflow")
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "permission-decision",
                "--adapter",
                "n8n",
                "--capability",
                "n8n.activate_workflow",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "permission-decision")
        self.assertEqual(payload["decision"]["outcome"], "requires_approval")
        self.assertIn("grants_permissions: false", rendered)
        self.assertIn("executes_tools: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)
        self.assertNotIn(TOKEN, result.stdout + result.stderr + rendered)

    def test_gateway_permission_decision_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/permission-decision?adapter_id=voice&capability=voice.capture_microphone"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "permission-decision")
        self.assertEqual(payload["decision"]["outcome"], "requires_approval")
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
