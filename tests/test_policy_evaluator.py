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
from lai_gateway.policy_evaluator import collect_policy_evaluation, render_policy_evaluation
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


class PolicyEvaluatorTest(unittest.TestCase):
    def test_declared_but_ungranted_capability_requires_approval(self) -> None:
        payload = collect_policy_evaluation(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
        )
        decision = payload["decision"]
        statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules"]}
        self.assertEqual(payload["operation"], "policy-evaluator")
        self.assertTrue(payload["policy_only"])
        self.assertEqual(decision["outcome"], "requires_approval")
        self.assertTrue(decision["requires_human_approval"])
        self.assertEqual(statuses["adapter.registered"], "pass")
        self.assertEqual(statuses["capability.declared"], "pass")
        self.assertEqual(statuses["capability.granted"], "fail")
        self.assertEqual(statuses["human_approval.boundary"], "requires_approval")
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_undeclared_capability_is_denied(self) -> None:
        payload = collect_policy_evaluation(adapter_id="browser", requested_capability="browser.secret_mode")
        decision = payload["decision"]
        statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules"]}
        self.assertEqual(decision["outcome"], "deny")
        self.assertEqual(statuses["capability.declared"], "fail")
        self.assertFalse(decision["requires_human_approval"])
        self.assertFalse(decision["executes_tools"])

    def test_missing_adapter_fails_closed(self) -> None:
        payload = collect_policy_evaluation(adapter_id="missing", requested_capability="missing.execute")
        decision = payload["decision"]
        statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules"]}
        self.assertEqual(decision["outcome"], "deny")
        self.assertEqual(statuses["adapter.registered"], "fail")
        self.assertEqual(statuses["capability.declared"], "fail")
        self.assertFalse(decision["grants_permission"])

    def test_channel_and_action_text_do_not_elevate_or_leak_secret_shaped_input(self) -> None:
        payload = collect_policy_evaluation(
            adapter_id="n8n",
            requested_capability="n8n.activate_workflow",
            actor="user",
            channel="voice",
            domain="automation",
            action="Authorization: Bearer sk-test-secret",
        )
        rendered = render_policy_evaluation(payload)
        decision = payload["decision"]
        self.assertEqual(decision["outcome"], "requires_approval")
        self.assertEqual(decision["action"], "[redacted]")
        self.assertFalse(decision["grants_permission"])
        self.assertNotIn("sk-test-secret", json.dumps(payload) + rendered)
        self.assertNotIn("Bearer", json.dumps(payload) + rendered)

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_policy_evaluation(
            collect_policy_evaluation(adapter_id="voice", requested_capability="voice.capture_microphone")
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "policy-eval",
                "--adapter",
                "voice",
                "--capability",
                "voice.capture_microphone",
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
        self.assertEqual(payload["operation"], "policy-evaluator")
        self.assertEqual(payload["decision"]["outcome"], "requires_approval")
        self.assertIn("grants_permissions: false", rendered)
        self.assertIn("executes_tools: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)
        self.assertNotIn(TOKEN, result.stdout + result.stderr + rendered)

    def test_gateway_policy_eval_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/policy-eval?adapter_id=document_media&capability=document.ocr"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "policy-evaluator")
        self.assertEqual(payload["decision"]["outcome"], "requires_approval")
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
