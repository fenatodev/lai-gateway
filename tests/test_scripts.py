from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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
            self.assertIn("lai-gateway 0.1.5", result.stdout)
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
            self.assertEqual(version.stdout.strip(), "lai-gateway 0.1.5")

    def test_launch_local_can_print_ui_before_serving_without_opening_browser(self) -> None:
        repo = Path(__file__).parents[1]
        env = {**os.environ, "LAI_GATEWAY_OPEN_BROWSER": "0", "PYTHON": sys.executable}
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
            first = proc.stdout.readline().strip()
            second = proc.stdout.readline().strip()
            self.assertEqual(first, "lai-gateway UI: http://127.0.0.1:18787/")
            self.assertEqual(second, "lai-gateway listening on http://127.0.0.1:18787")
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


if __name__ == "__main__":
    unittest.main()
