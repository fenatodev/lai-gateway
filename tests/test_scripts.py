from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from lai_gateway import __version__

from .fake_harness import TOKEN, fake_harness


class ScriptTest(unittest.TestCase):
    def test_install_local_writes_secret_free_wrappers_to_requested_bin_dir(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            env = {**os.environ, "LAI_GATEWAY_INSTALL_BIN": str(bin_dir), "PYTHON": sys.executable}
            result = subprocess.run(
                ["bash", "scripts/install-local.sh"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            gateway = bin_dir / "lai-gateway"
            ui = bin_dir / "lai-gateway-ui"
            mobile = bin_dir / "lai-gateway-mobile"
            model = bin_dir / "lai-gateway-model"
            self.assertTrue(gateway.exists())
            self.assertTrue(ui.exists())
            self.assertTrue(mobile.exists())
            self.assertTrue(model.exists())
            self.assertIn(f"lai-gateway {__version__}", result.stdout)
            self.assertNotIn("TOKEN", gateway.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", ui.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", mobile.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", model.read_text(encoding="utf-8").upper())
            self.assertIn("repo_dir=", ui.read_text(encoding="utf-8"))
            self.assertIn("repo_dir=", mobile.read_text(encoding="utf-8"))
            self.assertIn("repo_dir=", model.read_text(encoding="utf-8"))
            mobile_help = subprocess.run(
                [str(mobile), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("lai-gateway-mobile", mobile_help.stdout)
            model_help = subprocess.run(
                [str(model), "--help"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertIn("lai-gateway-model", model_help.stdout)
            version = subprocess.run(
                [str(gateway), "--version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertEqual(version.stdout.strip(), f"lai-gateway {__version__}")


    def test_launch_mobile_help_and_missing_candidate_are_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        help_result = subprocess.run(
            ["bash", "scripts/launch-mobile.sh", "--help"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        missing = subprocess.run(
            ["bash", "scripts/launch-mobile.sh"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )

        self.assertIn("lai-gateway-mobile", help_result.stdout)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--candidate-ip is required", missing.stderr)
        self.assertNotIn("Bearer", help_result.stdout + help_result.stderr + missing.stdout + missing.stderr)


    def test_launch_local_checks_harness_then_serves_without_opening_browser(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_OPEN_BROWSER": "0",
                "PYTHON": sys.executable,
                "LAI_GATEWAY_HARNESS_URL": harness.url,
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            proc = subprocess.Popen(
                ["bash", "scripts/launch-local.sh", "--bind", "127.0.0.1", "--port", "18787"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert proc.stdout is not None
                self.assertEqual(proc.stdout.readline().strip(), "lai-gateway dev: ready")
                self.assertEqual(proc.stdout.readline().strip(), f"harness: {harness.url}")
                self.assertEqual(proc.stdout.readline().strip(), "access: loopback")
                self.assertEqual(proc.stdout.readline().strip(), "ui: http://127.0.0.1:18787/")
                self.assertEqual(
                    proc.stdout.readline().strip(),
                    "lai-gateway listening on http://127.0.0.1:18787",
                )
                with urlopen(Request("http://127.0.0.1:18787/healthz"), timeout=5) as response:
                    self.assertEqual(response.status, 200)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.stderr is not None:
                    proc.stderr.close()

    def test_launch_local_blocks_when_harness_is_not_ready(self) -> None:
        repo = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            env = {
                **os.environ,
                "LAI_GATEWAY_OPEN_BROWSER": "0",
                "PYTHON": sys.executable,
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:9",
                "LAI_GATEWAY_TOKEN_FILE": str(token_file),
            }
            result = subprocess.run(
                ["bash", "scripts/launch-local.sh", "--bind", "127.0.0.1", "--port", "18788"],
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("overall: blocked", result.stderr)
            self.assertIn("harness_status", result.stderr)
            self.assertNotIn(TOKEN, result.stderr)


    def test_launch_model_help_and_key_guard_are_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        help_result = subprocess.run(
            ["bash", "scripts/launch-model.sh", "--help"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
        )
        with tempfile.TemporaryDirectory() as tmp:
            missing = subprocess.run(
                ["bash", "scripts/launch-model.sh", "--key-file", str(Path(tmp) / "missing-key"), "--plan-only"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
        self.assertIn("lai-gateway-model", help_result.stdout)
        self.assertNotIn("Bearer", help_result.stdout + help_result.stderr + missing.stdout + missing.stderr)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("model API key file is not ready", missing.stderr)


    def test_launch_model_does_not_put_bearer_key_in_shell_curl_arguments(self) -> None:
        repo = Path(__file__).parents[1]
        script = (repo / "scripts" / "launch-model.sh").read_text(encoding="utf-8")
        self.assertNotIn("curl -fsS -H", script)
        self.assertNotIn("Authorization: Bearer $(cat", script)
        self.assertIn("probe_models_endpoint", script)


if __name__ == "__main__":
    unittest.main()
