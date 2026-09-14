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
from lai_gateway.dev_control import collect_dev_control_policy, render_dev_control_policy
from lai_gateway.harness_client import READ_ONLY_RUN_MODES, WORK_RUN_MODES
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


class DevControlPolicyTest(unittest.TestCase):
    def test_policy_separates_conversation_plan_work_and_promotion(self) -> None:
        payload = collect_dev_control_policy()
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["policy_only"])
        self.assertFalse(payload["executes_work"])
        self.assertFalse(payload["modifies_files"])
        self.assertEqual(set(payload["surfaces"]["plan"]["allowed_modes"]), set(READ_ONLY_RUN_MODES))
        self.assertEqual(set(payload["surfaces"]["workbench_work"]["allowed_modes"]), set(WORK_RUN_MODES))
        self.assertFalse(payload["surfaces"]["conversation"]["creates_harness_run"])
        self.assertTrue(payload["surfaces"]["promotion"]["human_approval_required"])
        self.assertIn("write_mode_via_generic_harness_runs", payload["forbidden"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_render_and_cli_are_secret_free(self) -> None:
        rendered = render_dev_control_policy(collect_dev_control_policy())
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "dev-control", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "dev-control-policy")
        self.assertIn("grants_permissions: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)

    def test_gateway_dev_control_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/dev-control")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "dev-control-policy")
        self.assertFalse(payload["executes_work"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
