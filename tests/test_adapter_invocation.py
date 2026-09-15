import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.adapter_invocation import collect_adapter_invocation_proposal, render_adapter_invocation_proposal
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


class AdapterInvocationProposalTest(unittest.TestCase):
    def test_declared_capability_builds_requires_authorization_proposal(self) -> None:
        payload = collect_adapter_invocation_proposal(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            actor="user",
            channel="workbench",
            domain="web",
            action="open public page",
            parameters={"url": "https://example.invalid"},
        )
        proposal = payload["proposal"]
        self.assertEqual(payload["operation"], "adapter-invocation-proposal")
        self.assertTrue(payload["proposal_only"])
        self.assertEqual(proposal["status"], "requires_authorization")
        self.assertEqual(proposal["decision_outcome"], "requires_approval")
        self.assertEqual(proposal["authorization_status"], "requires_human_approval")
        self.assertFalse(proposal["effective_authorization"])
        self.assertFalse(proposal["dispatch_enabled"])
        self.assertFalse(proposal["executes_tools"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_missing_adapter_builds_blocked_proposal(self) -> None:
        payload = collect_adapter_invocation_proposal(adapter_id="missing", requested_capability="missing.call")
        proposal = payload["proposal"]
        self.assertEqual(proposal["status"], "blocked")
        self.assertEqual(proposal["adapter_status"], "missing")
        self.assertEqual(proposal["decision_outcome"], "deny")
        self.assertFalse(proposal["dispatch_enabled"])
        self.assertFalse(payload["effective_authorization"])

    def test_undeclared_capability_builds_blocked_proposal(self) -> None:
        payload = collect_adapter_invocation_proposal(adapter_id="n8n", requested_capability="n8n.unbounded_execute")
        proposal = payload["proposal"]
        self.assertEqual(proposal["status"], "blocked")
        self.assertEqual(proposal["decision_outcome"], "deny")
        self.assertEqual(proposal["authorization_status"], "blocked")
        self.assertFalse(proposal["grants_permission"])

    def test_secret_shaped_parameters_are_redacted(self) -> None:
        payload = collect_adapter_invocation_proposal(
            adapter_id="social_career",
            requested_capability="social.review_post_draft",
            parameters={"token": "Bearer should-not-print", "caption": "safe draft"},
        )
        rendered = render_adapter_invocation_proposal(payload)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertIn("[redacted]", encoded + rendered)
        self.assertIn("safe draft", encoded + rendered)
        self.assertNotIn("should-not-print", encoded + rendered)
        self.assertNotIn("Bearer", encoded + rendered)

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_adapter_invocation_proposal(
            collect_adapter_invocation_proposal(adapter_id="voice", requested_capability="voice.capture_microphone")
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "adapter-invocation-proposal",
                "--adapter",
                "voice",
                "--capability",
                "voice.capture_microphone",
                "--param",
                "note=hello",
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
        self.assertEqual(payload["operation"], "adapter-invocation-proposal")
        self.assertEqual(payload["proposal"]["status"], "requires_authorization")
        self.assertIn("dispatch_enabled: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)
        self.assertNotIn(TOKEN, result.stdout + result.stderr + rendered)

    def test_gateway_adapter_invocation_proposal_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(
                    f"{gateway.url}/v1/gateway/adapter-invocation-proposal?adapter_id=document_media&capability=document.ocr&param=source:sample.pdf"
                )
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "adapter-invocation-proposal")
        self.assertEqual(payload["proposal"]["status"], "requires_authorization")
        self.assertFalse(payload["executes_tools"])
        self.assertFalse(payload["dispatch_enabled"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
