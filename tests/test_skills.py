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
from lai_gateway.server import GatewayHTTPServer
from lai_gateway.skills import collect_skills_registry, render_skills_registry

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


class SkillsRegistryTest(unittest.TestCase):
    def test_builtin_skills_are_small_composable_and_non_authorizing(self) -> None:
        payload = collect_skills_registry()
        ids = {skill["id"] for skill in payload["skills"]}
        self.assertEqual(ids, {"grill", "architect", "spec", "frontend", "dev", "security", "scout"})
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["executes_adapters"])
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertFalse(payload["security"]["channels_elevate_permissions"])
        for skill in payload["skills"]:
            self.assertIn("domain", skill)
            self.assertIn("channels", skill)
            self.assertIn("autonomy", skill)
            self.assertIn("requested_capabilities", skill)
            self.assertFalse(skill["grants_permissions"])

    def test_skill_filter_is_read_only_and_missing_safe(self) -> None:
        payload = collect_skills_registry(skill_id="security")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["skills"][0]["id"], "security")
        missing = collect_skills_registry(skill_id="unknown")
        self.assertEqual(missing["overall"], "missing")
        self.assertEqual(missing["skills"], [])

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_skills_registry()
        rendered = render_skills_registry(payload)
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "skills", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "skills-registry")
        self.assertIn("grants_permissions: false", rendered)
        self.assertNotIn("Bearer", result.stdout + result.stderr + rendered)

    def test_gateway_skills_endpoint_is_read_only_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                status, headers, body = read_url(f"{gateway.url}/v1/gateway/skills?skill_id=dev")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["operation"], "skills-registry")
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["skills"][0]["id"], "dev")
        self.assertFalse(payload["security"]["grants_permissions"])
        self.assertFalse(payload["executes_adapters"])
        self.assertNotIn(TOKEN, body)
        self.assertNotIn("Bearer", body)


if __name__ == "__main__":
    unittest.main()
