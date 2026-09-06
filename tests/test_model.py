from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from lai_gateway.model import collect_model_plan, collect_model_status, render_model_plan, render_model_status


SECRET = "sk-local-secret-value"


class FakeOpenAIModelsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/models":
            body = json.dumps({"object": "list", "data": [{"id": "local-code-model"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


class FakeOpenAIModelsServer:
    def __enter__(self) -> "FakeOpenAIModelsServer":
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAIModelsHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class ModelStatusTest(unittest.TestCase):
    def test_model_status_reports_missing_runtime_without_secrets(self) -> None:
        env = {
            "LAI_GATEWAY_MODEL_BASE_URL": "http://user:pass@127.0.0.1:11434",
            "LAI_GATEWAY_MODEL_NAME": "local-code-model",
            "LAI_GATEWAY_MODEL_API_KEY": SECRET,
        }
        with patch("lai_gateway.model.shutil.which", return_value=None), patch("lai_gateway.model.Path.exists", return_value=False):
            payload = collect_model_status(env=env)
        rendered = render_model_status(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "model-status")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertIn("LAI_GATEWAY_MODEL_API_KEY=<redacted>", payload["model_config"]["env_keys_present"])
        self.assertNotIn(SECRET, text)
        self.assertNotIn("user:pass", text)
        self.assertNotIn("Bearer", text)

    def test_model_status_detects_docker_as_partial_path(self) -> None:
        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name == "docker" else None
        with patch("lai_gateway.model.shutil.which", side_effect=fake_which), patch("lai_gateway.model.Path.exists", return_value=False):
            payload = collect_model_status(env={})
        self.assertEqual(payload["overall"], "needs_runtime")
        self.assertIn("Docker is available", payload["recommendation"])

    def test_cli_model_status_json_is_secret_free(self) -> None:
        env = dict(os.environ)
        env.update({
            "LAI_GATEWAY_MODEL_BASE_URL": "http://user:pass@127.0.0.1:11434",
            "LAI_GATEWAY_MODEL_NAME": "local-code-model",
            "LAI_GATEWAY_MODEL_API_KEY": SECRET,
        })
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "model-status", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=10,
        )
        self.assertIn(result.returncode, (0, 1))
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-status")
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        self.assertNotIn("user:pass", result.stdout + result.stderr)
        self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_model_status_probe_reaches_loopback_openai_models_endpoint(self) -> None:
        with FakeOpenAIModelsServer() as server:
            payload = collect_model_status(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url,
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                },
                probe_openai=True,
            )
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["openai_probe"]["status"], "ready")
        self.assertTrue(payload["openai_probe"]["network_call"])
        self.assertEqual(payload["openai_probe"]["model_count"], 1)
        self.assertTrue(payload["network_calls"]["local_openai_probe"])

    def test_model_status_probe_blocks_public_or_credentialed_urls_before_network(self) -> None:
        unsafe_urls = [
            "https://127.0.0.1:11434",
            "http://user:pass@127.0.0.1:11434",
            "http://8.8.8.8:11434",
            "http://127.0.0.1:11434?x=1",
        ]
        for url in unsafe_urls:
            with self.subTest(url=url):
                with patch("urllib.request.urlopen") as opener:
                    payload = collect_model_status(
                        env={"LAI_GATEWAY_MODEL_BASE_URL": url},
                        probe_openai=True,
                    )
                self.assertEqual(payload["overall"], "blocked")
                self.assertEqual(payload["openai_probe"]["status"], "blocked")
                self.assertFalse(payload["openai_probe"]["network_call"])
                self.assertFalse(payload["network_calls"]["local_openai_probe"])
                opener.assert_not_called()

    def test_model_plan_auto_prefers_docker_without_mutation(self) -> None:
        def fake_which(name: str) -> str | None:
            return f"/usr/bin/{name}" if name == "docker" else None
        with patch("lai_gateway.model.shutil.which", side_effect=fake_which), patch("lai_gateway.model.Path.exists", return_value=False):
            payload = collect_model_plan(env={}, backend="auto", model_name="qwen-code-local")
        rendered = render_model_plan(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "model-plan")
        self.assertEqual(payload["backend"], "docker")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertIn("qwen-code-local", text)
        self.assertIn("model-status --probe-openai", text)
        self.assertNotIn("Bearer", text)


    def test_model_status_detects_windows_llama_cpp_from_wsl(self) -> None:
        def fake_which(name: str) -> str | None:
            if name == "llama-server.exe":
                return "/mnt/c/Users/fenat/AppData/Local/Microsoft/WinGet/Packages/ggml.llamacpp/llama-server.exe"
            return "/usr/bin/docker" if name == "docker" else None

        with (
            patch("lai_gateway.model.shutil.which", side_effect=fake_which),
            patch("lai_gateway.model._is_wsl", return_value=True),
            patch("lai_gateway.model.Path.exists", return_value=False),
        ):
            payload = collect_model_status(env={})
        rendered = render_model_status(payload)
        self.assertEqual(payload["overall"], "needs_model_config")
        self.assertTrue(payload["windows_commands"]["llama-server.exe"]["available"])
        self.assertIn("windows_runtime_tools: llama-server.exe", rendered)
        self.assertIn("Windows llama.cpp tools", payload["recommendation"])
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])

    def test_model_plan_auto_prefers_windows_llama_cpp_before_docker(self) -> None:
        def fake_which(name: str) -> str | None:
            if name == "llama-cli.exe":
                return "/mnt/c/Users/fenat/AppData/Local/Microsoft/WinGet/Packages/ggml.llamacpp/llama-cli.exe"
            return "/usr/bin/docker" if name == "docker" else None

        with (
            patch("lai_gateway.model.shutil.which", side_effect=fake_which),
            patch("lai_gateway.model._is_wsl", return_value=True),
            patch("lai_gateway.model.Path.exists", return_value=False),
        ):
            payload = collect_model_plan(env={}, backend="auto", model_name="qwen-code-local")
        rendered = render_model_plan(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["backend"], "windows-llama-cpp")
        self.assertIn("llama-server.exe", text)
        self.assertIn("<windows-host-ip>", text)
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertNotIn("Bearer", text)

    def test_cli_model_plan_json_is_secret_free(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "model-plan", "--backend", "llama-cpp", "--model-name", "local-code", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-plan")
        self.assertEqual(payload["backend"], "llama-cpp")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
