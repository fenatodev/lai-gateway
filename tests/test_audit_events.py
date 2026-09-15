import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.audit_events import collect_audit_events, render_audit_events
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


class AuditEventsTest(unittest.TestCase):
    def test_audit_events_derive_ordered_timeline_without_persistence_or_execution(self) -> None:
        payload = collect_audit_events(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
            parameters={"url": "https://example.test"},
        )
        self.assertEqual(payload["operation"], "audit-events")
        self.assertEqual(payload["event_count"], 4)
        self.assertFalse(payload["persisted"])
        self.assertFalse(payload["writes_log_file"])
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["dispatch_enabled"])
        self.assertFalse(payload["effective_authorization"])
        self.assertEqual([event["sequence"] for event in payload["events"]], [1, 2, 3, 4])
        self.assertEqual(
            [event["event_type"] for event in payload["events"]],
            ["permission_decision", "policy_evaluation", "authorization_record", "adapter_invocation_proposal"],
        )
        for event in payload["events"]:
            self.assertFalse(event["persisted"])
            self.assertFalse(event["executes_tools"])
            self.assertFalse(event["grants_permission"])
            self.assertFalse(event["dispatch_enabled"])
            self.assertFalse(event["effective_authorization"])
            self.assertEqual(event["requested_capability"], "browser.navigate_public")
            self.assertEqual(event["parameter_count"], 1)

    def test_denied_request_still_gets_audit_events_without_authority(self) -> None:
        payload = collect_audit_events(adapter_id="browser", requested_capability="browser.secret_mode")
        self.assertEqual(payload["proposal"]["status"], "blocked")
        self.assertEqual(payload["events"][0]["status"], "deny")
        self.assertFalse(payload["events"][0]["requires_human_approval"])
        self.assertFalse(payload["security"]["audit_events_elevate_permissions"])

    def test_secret_shaped_parameters_are_not_exposed_by_audit_events(self) -> None:
        payload = collect_audit_events(
            adapter_id="n8n",
            requested_capability="n8n.workflow.activate",
            action="Authorization: Bearer abc",
            parameters={"token": "ghp_example", "safe": "ok"},
        )
        rendered = render_audit_events(payload)
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("ghp_example", serialized + rendered)
        self.assertNotIn("Bearer abc", serialized + rendered)
        self.assertIn("[redacted]", json.dumps(payload["proposal"], sort_keys=True))
        for event in payload["events"]:
            self.assertNotIn("parameters", event)

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_audit_events(
            collect_audit_events(adapter_id="voice", requested_capability="voice.capture_microphone")
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "audit-events",
                "--adapter",
                "voice",
                "--capability",
                "voice.capture_microphone",
                "--param",
                "device=default",
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
        self.assertEqual(payload["operation"], "audit-events")
        self.assertEqual(payload["event_count"], 4)
        self.assertIn("writes_log_file: false", rendered)
        self.assertIn("read_only: true", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)
        self.assertNotIn(TOKEN, result.stdout + result.stderr + rendered)

    def test_gateway_audit_events_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/audit-events?adapter_id=document_media&capability=document.ocr&param=file=local-note"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "audit-events")
        self.assertEqual(payload["event_count"], 4)
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["writes_log_file"])
        self.assertFalse(payload["security"]["persists_audit_log"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
