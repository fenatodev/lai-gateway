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
from lai_gateway.identity import collect_identity_binding, render_identity_binding
from lai_gateway.permission_decision import collect_permission_decision
from lai_gateway.policy_evaluator import collect_policy_evaluation
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


class IdentityBindingTest(unittest.TestCase):
    def test_identity_binding_verifies_user_client_agent_service(self) -> None:
        payload = collect_identity_binding(
            user_id="user-a",
            client_id="workbench",
            agent_id="lai-agent",
            service_id="lai-gateway",
            identity_source="test-fixture",
        )
        identity = payload["identity"]
        self.assertEqual(payload["operation"], "identity-binding")
        self.assertTrue(payload["identity_verified"])
        self.assertEqual(identity["status"], "verified")
        self.assertEqual(identity["user_id"], "user-a")
        self.assertEqual(identity["client_id"], "workbench")
        self.assertEqual(identity["agent_id"], "lai-agent")
        self.assertEqual(identity["service_id"], "lai-gateway")
        self.assertTrue(identity["identity_binding_id"].startswith("pid-"))
        self.assertFalse(identity["grants_permission"])
        self.assertFalse(identity["executes_tools"])

    def test_forged_claim_is_rejected_without_permission_grant(self) -> None:
        payload = collect_identity_binding(
            user_id="user-a",
            client_id="workbench",
            agent_id="lai-agent",
            service_id="lai-gateway",
            identity_source="test-fixture",
            claimed_user_id="attacker",
        )
        identity = payload["identity"]
        self.assertFalse(payload["identity_verified"])
        self.assertEqual(identity["status"], "blocked")
        self.assertIn("user_id", identity["rejected_claims"])
        self.assertFalse(payload["security"]["identity_elevates_permissions"])

    def test_client_or_service_drift_is_detected(self) -> None:
        baseline = collect_identity_binding(
            user_id="user-a",
            client_id="workbench",
            agent_id="lai-agent",
            service_id="lai-gateway",
            identity_source="test-fixture",
        )["identity"]["identity_binding_id"]
        changed = collect_identity_binding(
            user_id="user-a",
            client_id="other-client",
            agent_id="lai-agent",
            service_id="lai-gateway",
            identity_source="test-fixture",
            expected_identity_binding_id=baseline,
        )
        self.assertFalse(changed["identity_verified"])
        self.assertTrue(changed["identity"]["identity_drift"])
        self.assertEqual(changed["identity"]["reason"], "identity binding drift detected")

    def test_untrusted_identity_blocks_permission_decision(self) -> None:
        payload = collect_permission_decision(
            adapter_id="local_status",
            requested_capability="local_status.status",
            identity_source="untrusted-chat-text",
        )
        decision = payload["decision"]
        self.assertFalse(payload["identity_verified"])
        self.assertEqual(decision["outcome"], "deny")
        self.assertEqual(decision["reason"], "identity source is not trusted")
        self.assertIsNone(decision["granted_capability"])
        self.assertFalse(decision["grants_permission"])

    def test_policy_evaluation_includes_identity_rule(self) -> None:
        payload = collect_policy_evaluation(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            identity_source="test-fixture",
        )
        statuses = {rule["rule_id"]: rule["status"] for rule in payload["rules"]}
        self.assertTrue(payload["identity_verified"])
        self.assertEqual(statuses["identity.verified"], "pass")
        self.assertEqual(payload["decision"]["outcome"], "requires_approval")

    def test_cli_identity_binding_is_secret_free(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "identity-binding",
                "--user-id",
                "Authorization: Bearer sk-test-secret",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=10,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["identity"]["user_id"], "[redacted]")
        self.assertNotIn("sk-test-secret", output)
        self.assertNotIn("Bearer", output)

    def test_gateway_identity_binding_uses_server_origin_and_rejects_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/identity-binding?claimed_client_id=spoofed")
        payload = json.loads(body)
        identity = payload["identity"]
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(identity["identity_source"], "gateway-loopback")
        self.assertEqual(identity["client_id"], "gateway-loopback")
        self.assertFalse(payload["identity_verified"])
        self.assertIn("client_id", identity["rejected_claims"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
