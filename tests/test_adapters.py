import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway.adapters import collect_adapter_registry, render_adapter_registry
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


class AdapterRegistryTest(unittest.TestCase):
    def test_mcp_is_first_governed_adapter_without_tool_execution(self) -> None:
        payload = collect_adapter_registry()
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "mcp")
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["grants_permissions"])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertFalse(payload["security"]["tool_execution_enabled"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_adapter_filter_and_cli_are_secret_free(self) -> None:
        missing = collect_adapter_registry(adapter_id="browser")
        self.assertEqual(missing["overall"], "missing")
        rendered = render_adapter_registry(collect_adapter_registry(adapter_id="mcp"))
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "adapters", "--adapter", "mcp", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "adapter-registry")
        self.assertIn("tool_execution_enabled: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)

    def test_gateway_adapters_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/adapters?adapter_id=mcp")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "adapter-registry")
        self.assertEqual(payload["adapters"][0]["id"], "mcp")
        self.assertFalse(payload["security"]["tool_execution_enabled"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
