from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalOperatorRuntimeCliTest(unittest.TestCase):
    def test_cli_runs_green_chain_without_manual_stage_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "local-operator-runtime",
                    "--repo-root",
                    tmp,
                    "--task-id",
                    "cli-operator-green",
                    "--domain",
                    "dev",
                    "--channel",
                    "chat",
                    "--autonomy-zone",
                    "green",
                    "--capability",
                    "local.validation",
                    "--allowed-path",
                    "lai_gateway/**",
                    "--proposed-command",
                    "git --version",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema_version"], "local-operator-runtime/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["stage_status"]["file_pack"], "written")
        self.assertEqual(payload["stage_status"]["review"], "ready")
        self.assertEqual(
            payload["stage_status"]["approval"],
            "ready_without_approval",
        )
        self.assertEqual(payload["stage_status"]["executor"], "ready")
        self.assertFalse(payload["executes_commands"])
        self.assertFalse(payload["security"]["calls_harness"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["effective_authorization"])


if __name__ == "__main__":
    unittest.main()
