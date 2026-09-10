from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lai_gateway.config import GatewayConfig
from lai_gateway.stack import (
    _harness_start_env,
    _probe_harness,
    _start_harness,
    collect_local_stack_status,
    render_local_stack,
    resolve_harness_repo,
    start_local_stack,
)


class LocalStackTest(unittest.TestCase):
    def test_check_only_is_secret_free_and_does_not_start_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "control-token"
            token.write_text("secret-token-value", encoding="utf-8")
            repo = Path(tmp) / "lai-local-agent"
            repo.mkdir()
            config = GatewayConfig.from_env({
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:18765",
                "LAI_GATEWAY_TOKEN_FILE": str(token),
                "LAI_GATEWAY_BIND": "127.0.0.1",
                "LAI_GATEWAY_PORT": "18787",
            })
            with patch("lai_gateway.stack._run_model_start") as model, \
                 patch("lai_gateway.stack._start_harness") as harness, \
                 patch("lai_gateway.stack._start_gateway") as gateway:
                payload = start_local_stack(config, harness_repo=repo, check_only=True)
            self.assertIn(payload["overall"], {"planned", "ready"})
            self.assertTrue(payload["check_only"])
            self.assertFalse(payload["security"]["tokens_printed"])
            rendered = render_local_stack(payload)
            self.assertIn("would_run: lai-server-start", rendered)
            self.assertNotIn("secret-token-value", json.dumps(payload))
            self.assertNotIn("secret-token-value", rendered)
            model.assert_not_called()
            harness.assert_not_called()
            gateway.assert_not_called()

    def test_collect_status_reports_ready_when_harness_and_gateway_are_ready(self) -> None:
        config = GatewayConfig.from_env({
            "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:18765",
            "LAI_GATEWAY_TOKEN_FILE": str(Path("/tmp/control-token")),
            "LAI_GATEWAY_BIND": "127.0.0.1",
            "LAI_GATEWAY_PORT": "18787",
        })
        with patch("lai_gateway.stack._probe_harness", return_value={"ready": True, "url": config.harness_url}), \
             patch("lai_gateway.stack._probe_gateway", return_value={"ready": True, "url": "http://127.0.0.1:18787/"}), \
             patch("lai_gateway.stack._command_exists", return_value=True):
            payload = collect_local_stack_status(config, harness_repo=Path("/tmp/lai-local-agent"))
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["urls"]["gateway"], "http://127.0.0.1:18787/")

    def test_resolve_harness_repo_honors_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LAI_HARNESS_REPO_DIR": tmp}, clear=False):
                self.assertEqual(resolve_harness_repo(), Path(tmp).resolve())

    def test_probe_harness_requires_ready_readiness_and_verified_work_sandbox(self) -> None:
        config = GatewayConfig.from_env({
            "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:18765",
            "LAI_GATEWAY_TOKEN_FILE": str(Path("/tmp/control-token")),
        })
        client = MagicMock()
        client.status.return_value = {
            "product": "lai harness",
            "version": "0.5.0",
            "repository": "/repo",
            "capabilities": {
                "local_chat_work_runs": True,
                "sandbox_workspace_write": True,
                "verified_sandbox_ready": False,
            },
        }
        client.readiness.return_value = {"overall": "ready"}
        with patch("lai_gateway.stack.HarnessClient", return_value=client):
            payload = _probe_harness(config)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["detail"], "verified_sandbox_ready=false")

    def test_harness_start_env_loads_daily_sandbox_without_overriding_explicit_env(self) -> None:
        daily = SimpleNamespace(
            sandbox_image="python:3.12-bookworm@sha256:" + "a" * 64,
            sandbox_python="python3",
        )
        with patch.dict(os.environ, {"LAI_REMOTE_SANDBOX_PYTHON": "python-custom"}, clear=True), \
             patch("lai_gateway.stack.read_daily_config", return_value=daily):
            env = _harness_start_env()
        self.assertEqual(env["LAI_REMOTE_SANDBOX_IMAGE"], daily.sandbox_image)
        self.assertEqual(env["LAI_REMOTE_SANDBOX_PYTHON"], "python-custom")

    def test_start_harness_passes_daily_sandbox_environment_to_child(self) -> None:
        config = GatewayConfig.from_env({
            "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:18765",
            "LAI_GATEWAY_TOKEN_FILE": str(Path("/tmp/control-token")),
        })
        daily = SimpleNamespace(
            sandbox_image="python:3.12-bookworm@sha256:" + "b" * 64,
            sandbox_python="python3",
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            logs = Path(tmp) / "logs"
            repo.mkdir()
            logs.mkdir()
            fake_proc = SimpleNamespace(pid=12345)
            with patch("lai_gateway.stack._command_exists", return_value=True), \
                 patch("lai_gateway.stack.read_daily_config", return_value=daily), \
                 patch("subprocess.Popen", return_value=fake_proc) as popen:
                payload = _start_harness(config, repo, logs)
        self.assertEqual(payload["status"], "started")
        child_env = popen.call_args.kwargs["env"]
        self.assertEqual(child_env["LAI_REMOTE_SANDBOX_IMAGE"], daily.sandbox_image)
        self.assertEqual(child_env["LAI_REMOTE_SANDBOX_PYTHON"], "python3")


if __name__ == "__main__":
    unittest.main()
