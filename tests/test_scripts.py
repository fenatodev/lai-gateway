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
            self.assertTrue(gateway.exists())
            self.assertTrue(ui.exists())
            self.assertIn(f"lai-gateway {__version__}", result.stdout)
            self.assertNotIn("TOKEN", gateway.read_text(encoding="utf-8").upper())
            self.assertNotIn("TOKEN", ui.read_text(encoding="utf-8").upper())
            version = subprocess.run(
                [str(gateway), "--version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            self.assertEqual(version.stdout.strip(), f"lai-gateway {__version__}")

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


if __name__ == "__main__":
    unittest.main()
