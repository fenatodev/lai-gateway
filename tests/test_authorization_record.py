import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.authorization_record import collect_authorization_record, render_authorization_record
from lai_gateway.config import GatewayConfig
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


class AuthorizationRecordTest(unittest.TestCase):
    def test_requires_approval_decision_yields_non_effective_authorization_record(self) -> None:
        payload = collect_authorization_record(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
        )
        record = payload["record"]
        self.assertEqual(payload["operation"], "authorization-record")
        self.assertTrue(payload["policy_only"])
        self.assertEqual(record["status"], "requires_human_approval")
        self.assertEqual(record["decision_outcome"], "requires_approval")
        self.assertEqual(record["requested_capability"], "browser.navigate_public")
        self.assertTrue(record["requires_human_approval"])
        self.assertFalse(record["approval_captured"])
        self.assertIsNone(record["approved_by"])
        self.assertIsNone(record["approved_at"])
        self.assertFalse(record["effective_authorization"])
        self.assertFalse(record["record_persisted"])
        self.assertFalse(record["grants_permission"])
        self.assertFalse(record["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_denied_decision_yields_blocked_record_without_authorization(self) -> None:
        payload = collect_authorization_record(adapter_id="browser", requested_capability="browser.secret_mode")
        record = payload["record"]
        self.assertEqual(record["status"], "blocked")
        self.assertEqual(record["decision_outcome"], "deny")
        self.assertFalse(record["requires_human_approval"])
        self.assertFalse(record["effective_authorization"])
        self.assertFalse(payload["executes_tools"])

    def test_secret_shaped_action_is_redacted_before_record_materialization(self) -> None:
        payload = collect_authorization_record(
            adapter_id="n8n",
            requested_capability="n8n.activate_workflow",
            action="Authorization: Bearer should-not-leak",
        )
        record = payload["record"]
        self.assertEqual(record["action"], "[redacted]")
        self.assertNotIn("should-not-leak", json.dumps(payload))
        self.assertFalse(record["effective_authorization"])

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_authorization_record(
            collect_authorization_record(adapter_id="voice", requested_capability="voice.capture_microphone")
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "authorization-record",
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
        self.assertEqual(payload["operation"], "authorization-record")
        self.assertEqual(payload["record"]["status"], "requires_human_approval")
        self.assertFalse(payload["record"]["effective_authorization"])
        self.assertIn("approval_captured: false", rendered)
        self.assertIn("effective_authorization: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)
        self.assertNotIn(TOKEN, result.stdout + result.stderr + rendered)

    def test_gateway_authorization_record_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/authorization-record?adapter_id=document_media&capability=document.ocr"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "authorization-record")
        self.assertEqual(payload["record"]["status"], "requires_human_approval")
        self.assertFalse(payload["record"]["effective_authorization"])
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
