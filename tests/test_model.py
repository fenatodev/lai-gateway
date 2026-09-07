from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from lai_gateway.model import collect_model_eval, collect_model_files, collect_model_plan, collect_model_runs, collect_model_smoke, collect_model_status, collect_model_task, render_model_eval, render_model_files, render_model_plan, render_model_runs, render_model_smoke, render_model_status, render_model_task


SECRET = "sk-local-secret-value"
MODEL_API_KEY = "model-local-test-key-12345678901234567890"


class FakeOpenAIModelsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/auth/v1/models"):
            if self.headers.get("Authorization") != f"Bearer {MODEL_API_KEY}":
                self.send_response(401)
                self.end_headers()
                return
            body = json.dumps({"object": "list", "data": [{"id": "auth-local-code-model"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
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

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/auth/v1/chat/completions"):
            if self.headers.get("Authorization") != f"Bearer {MODEL_API_KEY}":
                self.send_response(401)
                self.end_headers()
                return
            request_body = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0")).decode("utf-8", errors="replace")
            content = "def lai_add(a, b): return a + b" if "lai_add" in request_body else ('{"lai_json_status":"ok","count":2}' if "lai_json_status" in request_body else "LAI_SMOKE_OK")
            body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/v1/chat/completions":
            request_body = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0")).decode("utf-8", errors="replace")
            content = "def lai_add(a, b): return a + b" if "lai_add" in request_body else ('{"lai_json_status":"ok","count":2}' if "lai_json_status" in request_body else "LAI_SMOKE_OK")
            body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
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

    def test_model_status_probe_uses_redacted_local_model_api_key_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            payload = collect_model_status(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                    "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                    "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
                },
                probe_openai=True,
            )
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["openai_probe"]["status"], "ready")
        self.assertTrue(payload["openai_probe"]["auth_used"])
        self.assertTrue(payload["model_config"]["api_key_configured"])
        self.assertEqual(payload["model_config"]["api_key_file"], str(key_file))
        self.assertNotIn(MODEL_API_KEY, text)
        self.assertNotIn("Bearer", text)

    def test_cli_model_key_create_and_check_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "model-api-key"
            created = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-key-create", "--path", str(key_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            checked = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-key-check", "--path", str(key_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        self.assertEqual(created.returncode, 0)
        self.assertEqual(checked.returncode, 0)
        created_payload = json.loads(created.stdout)
        checked_payload = json.loads(checked.stdout)
        self.assertEqual(created_payload["operation"], "model-key-create")
        self.assertEqual(checked_payload["operation"], "model-key-check")
        self.assertFalse(created_payload["key_printed"])
        self.assertFalse(checked_payload["key_printed"])
        self.assertNotIn("\"key\":", created.stdout)
        self.assertNotIn("Bearer", created.stdout + checked.stdout + created.stderr + checked.stderr)

    def test_model_smoke_reaches_loopback_chat_completion(self) -> None:
        with FakeOpenAIModelsServer() as server:
            payload = collect_model_smoke(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url,
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                }
            )
        rendered = render_model_smoke(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "model-smoke")
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["smoke"]["matched"])
        self.assertTrue(payload["network_calls"]["local_openai_chat_completion"])
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])
        self.assertIn("fixed_prompt_only: true", rendered)
        self.assertNotIn("Bearer", text)

    def test_model_smoke_uses_redacted_api_key_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            payload = collect_model_smoke(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                    "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                    "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
                }
            )
        text = json.dumps(payload, sort_keys=True) + render_model_smoke(payload)
        self.assertEqual(payload["overall"], "ready")
        self.assertTrue(payload["smoke"]["auth_used"])
        self.assertNotIn(MODEL_API_KEY, text)
        self.assertNotIn("Bearer", text)

    def test_model_smoke_blocks_public_urls_before_network(self) -> None:
        with patch("urllib.request.urlopen") as opener:
            payload = collect_model_smoke(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": "http://8.8.8.8:11434",
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                }
            )
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["smoke"]["network_call"])
        opener.assert_not_called()

    def test_cli_model_smoke_json_requires_ready_endpoint_and_is_secret_free(self) -> None:
        env = dict(os.environ)
        env.update({
            "LAI_GATEWAY_MODEL_BASE_URL": "http://8.8.8.8:11434",
            "LAI_GATEWAY_MODEL_NAME": "local-code-model",
            "LAI_GATEWAY_MODEL_API_KEY": SECRET,
        })
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "model-smoke", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-smoke")
        self.assertEqual(payload["overall"], "blocked")
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        self.assertNotIn("Bearer", result.stdout + result.stderr)



    def test_model_task_reaches_loopback_json_mini_completion(self) -> None:
        with FakeOpenAIModelsServer() as server:
            payload = collect_model_task(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url,
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                },
                task="json-mini",
            )
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["task"], "json-mini")
        self.assertTrue(payload["result"]["matched"])
        self.assertIn("lai_json_status", payload["result"]["response_preview"])

    def test_model_task_reaches_loopback_code_mini_completion(self) -> None:
        with FakeOpenAIModelsServer() as server:
            payload = collect_model_task(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url,
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                },
                task="code-mini",
                timeout_seconds=10.0,
            )
        rendered = render_model_task(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "model-task")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["task"], "code-mini")
        self.assertTrue(payload["result"]["matched"])
        self.assertIn("def lai_add", payload["result"]["response_preview"])
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])
        self.assertNotIn("Bearer", text)

    def test_model_task_blocks_public_urls_before_network(self) -> None:
        with patch("urllib.request.urlopen") as opener:
            payload = collect_model_task(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": "http://8.8.8.8:11434",
                    "LAI_GATEWAY_MODEL_NAME": "local-code-model",
                },
                task="code-mini",
            )
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["network_calls"]["local_openai_chat_completion"])
        opener.assert_not_called()

    def test_cli_model_task_json_is_secret_free(self) -> None:
        env = dict(os.environ)
        env.update({
            "LAI_GATEWAY_MODEL_BASE_URL": "http://8.8.8.8:11434",
            "LAI_GATEWAY_MODEL_NAME": "local-code-model",
            "LAI_GATEWAY_MODEL_API_KEY": SECRET,
        })
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "model-task", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-task")
        self.assertEqual(payload["overall"], "blocked")
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        self.assertNotIn("Bearer", result.stdout + result.stderr)

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


    def test_model_status_probe_uses_redacted_local_model_api_key(self) -> None:
        with FakeOpenAIModelsServer() as server:
            payload = collect_model_status(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                    "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                    "LAI_GATEWAY_MODEL_API_KEY": MODEL_API_KEY,
                },
                probe_openai=True,
            )
        text = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["openai_probe"]["status"], "ready")
        self.assertTrue(payload["openai_probe"]["auth_used"])
        self.assertEqual(payload["openai_probe"]["model_count"], 1)
        self.assertIn("LAI_GATEWAY_MODEL_API_KEY=<redacted>", payload["model_config"]["env_keys_present"])
        self.assertNotIn(MODEL_API_KEY, text)
        self.assertNotIn("Bearer", text)

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


    def test_model_files_recommendation_uses_all_scanned_models_before_output_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Recommendation considers all scanned models, not only the displayed max_results slice.
            (root / "aaa-big-coder-00001-of-00001.gguf").write_bytes(b"a" * 64)
            (root / "qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf").write_bytes(b"q" * 128)
            (root / "qwen2.5-coder-7b-instruct-q4_k_m-00002-of-00002.gguf").write_bytes(b"w" * 64)
            (root / "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf").write_bytes(b"m" * 512)
            payload = collect_model_files(paths=[tmp], max_results=1)
        self.assertEqual(len(payload["models"]), 1)
        self.assertEqual(payload["recommended"]["name"], "Ministral-3-8B-Instruct-2512-Q4_K_M")
        self.assertEqual(payload["recommended"]["recommendation_reason"], "validated_baseline")

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
        self.assertIn("--port 18082", text)
        self.assertIn("configure_api_key_file", text)
        self.assertIn("model-api-key", text)
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




    def test_model_eval_runs_fixed_suite_and_can_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            runs_file = Path(tmp) / "model-runs.jsonl"
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            payload = collect_model_eval(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                    "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                    "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
                },
                record=True,
                runs_file=runs_file,
            )
            rendered = render_model_eval(payload)
            recorded = collect_model_runs(path=runs_file, limit=10)
            raw = runs_file.read_text(encoding="utf-8")
        self.assertEqual(payload["operation"], "model-eval")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["summary"]["checks"], 3)
        self.assertEqual(payload["summary"]["ready"], 3)
        self.assertEqual(recorded["count"], 3)
        self.assertIn("model-smoke", recorded["summary"]["operations"])
        self.assertIn("model-task", recorded["summary"]["operations"])
        self.assertIn("model-eval: ready", rendered)
        self.assertNotIn(MODEL_API_KEY, raw + rendered)
        self.assertNotIn("Bearer", raw + rendered)
        self.assertNotIn("Return only this exact one-line", raw + rendered)

    def test_cli_model_eval_json_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            runs_file = Path(tmp) / "model-runs.jsonl"
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            env = dict(os.environ)
            env.update({
                "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
            })
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-eval", "--record", "--runs-file", str(runs_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-eval")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["summary"]["checks"], 3)
        self.assertNotIn(MODEL_API_KEY, result.stdout + result.stderr)
        self.assertNotIn("Bearer", result.stdout + result.stderr)
        self.assertNotIn("Return only this exact one-line", result.stdout + result.stderr)

    def test_model_task_record_writes_prompt_free_secret_free_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            runs_file = Path(tmp) / "model-runs.jsonl"
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            payload = collect_model_task(
                env={
                    "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                    "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                    "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
                },
                task="code-mini",
                record=True,
                runs_file=runs_file,
            )
            recorded = collect_model_runs(path=runs_file, limit=10)
            mode = oct(runs_file.stat().st_mode & 0o777)
            raw = runs_file.read_text(encoding="utf-8")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["record"]["status"], "written")
        self.assertEqual(mode, "0o600")
        self.assertEqual(recorded["operation"], "model-runs")
        self.assertEqual(recorded["count"], 1)
        self.assertEqual(recorded["summary"]["ready"], 1)
        self.assertEqual(recorded["entries"][0]["operation"], "model-task")
        self.assertEqual(recorded["entries"][0]["task"], "code-mini")
        self.assertNotIn(MODEL_API_KEY, raw)
        self.assertNotIn("Bearer", raw)
        self.assertNotIn("Return only this exact one-line", raw)
        self.assertNotIn(str(key_file), raw)

    def test_cli_model_runs_reads_secret_free_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, FakeOpenAIModelsServer() as server:
            runs_file = Path(tmp) / "model-runs.jsonl"
            key_file = Path(tmp) / "model-api-key"
            key_file.write_text(MODEL_API_KEY + "\n", encoding="utf-8")
            key_file.chmod(0o600)
            env = dict(os.environ)
            env.update({
                "LAI_GATEWAY_MODEL_BASE_URL": server.url + "/auth",
                "LAI_GATEWAY_MODEL_NAME": "auth-local-code-model",
                "LAI_GATEWAY_MODEL_API_KEY_FILE": str(key_file),
            })
            write_result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-task", "--task", "code-mini", "--record", "--runs-file", str(runs_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=10,
            )
            read_result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-runs", "--path", str(runs_file), "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        self.assertEqual(write_result.returncode, 0)
        self.assertEqual(read_result.returncode, 0)
        payload = json.loads(read_result.stdout)
        combined = write_result.stdout + write_result.stderr + read_result.stdout + read_result.stderr
        self.assertEqual(payload["operation"], "model-runs")
        self.assertEqual(payload["count"], 1)
        self.assertIn("model-task", payload["summary"]["operations"])
        self.assertNotIn(MODEL_API_KEY, combined)
        self.assertNotIn("Bearer", combined)
        self.assertNotIn("Return only this exact one-line", combined)

    def test_render_model_runs_is_secret_free(self) -> None:
        payload = {
            "operation": "model-runs",
            "version": "0.0.0",
            "overall": "ready",
            "path": "/tmp/model-runs.jsonl",
            "count": 1,
            "summary": {"ready": 1, "failed": 0, "avg_elapsed_ms": 42.0},
            "entries": [{"created_at": "2026-01-01T00:00:00Z", "operation": "model-task", "overall": "ready", "task": "code-mini", "elapsed_ms": 42.0}],
        }
        rendered = render_model_runs(payload)
        self.assertIn("model-task", rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertNotIn("secret", rendered.lower())

    def test_model_files_groups_split_and_prefers_validated_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qwen = root / "qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf"
            qwen_2 = root / "qwen2.5-coder-7b-instruct-q4_k_m-00002-of-00002.gguf"
            ministral = root / "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf"
            mmproj = root / "Ministral-3-8B-Instruct-2512-BF16-mmproj.gguf"
            qwen.write_bytes(b"q" * 128)
            qwen_2.write_bytes(b"w" * 64)
            ministral.write_bytes(b"m" * 512)
            mmproj.write_bytes(b"x" * 32)
            payload = collect_model_files(paths=[tmp], max_results=10)
        rendered = render_model_files(payload)
        text = json.dumps(payload, sort_keys=True) + rendered
        self.assertEqual(payload["operation"], "model-files")
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])
        self.assertEqual(payload["models_found"], 3)
        self.assertEqual(payload["recommended"]["name"], "Ministral-3-8B-Instruct-2512-Q4_K_M")
        self.assertEqual(payload["recommended"]["recommendation_reason"], "validated_baseline")
        recommended_model = payload["models"][0]
        self.assertEqual(recommended_model["name"], "Ministral-3-8B-Instruct-2512-Q4_K_M")
        self.assertFalse(recommended_model["is_split"])
        qwen_model = next(model for model in payload["models"] if model["name"] == "qwen2.5-coder-7b-instruct-q4_k_m")
        self.assertTrue(qwen_model["is_split"])
        self.assertEqual(qwen_model["shard_count"], 2)
        self.assertEqual(qwen_model["shard_total"], 2)
        self.assertTrue(qwen_model["complete"])
        self.assertIn("llama-server.exe", payload["recommended"]["start_runtime_example"])
        self.assertIn("model-key-create", payload["recommended"]["create_api_key_file"])
        self.assertIn("LAI_GATEWAY_MODEL_API_KEY_FILE", payload["recommended"]["configure_api_key_file"])
        self.assertIn("configure_api_key_file", rendered)
        self.assertNotIn("Bearer", text)

    def test_cli_model_files_json_is_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "local-code-q4_k_m.gguf").write_bytes(b"model")
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-files", "--path", tmp, "--json"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-files")
        self.assertEqual(payload["overall"], "ready")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["downloads_models"])
        self.assertEqual(payload["recommended"]["name"], "local-code-q4_k_m")
        self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_cli_model_plan_accepts_windows_llama_cpp_backend(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "model-plan", "--backend", "windows-llama-cpp", "--model-name", "local-code", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "model-plan")
        self.assertEqual(payload["backend"], "windows-llama-cpp")
        self.assertIn("start_runtime_example", payload["commands"])
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["downloads_models"])


if __name__ == "__main__":
    unittest.main()
