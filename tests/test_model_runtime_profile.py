import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.model import write_model_runtime_config
from lai_gateway.model_runtime_profile import collect_model_runtime_profile, render_model_runtime_profile


class ModelRuntimeProfileTest(unittest.TestCase):
    def _configured_runtime(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        key = root / "model-api-key"
        key.write_text("local-test-key-value-1234567890\n", encoding="utf-8")
        key.chmod(0o600)
        config = root / "model-runtime.json"
        write_model_runtime_config(
            base_url="http://127.0.0.1:18082",
            model_name="local-test-model",
            api_key_file=key,
            path=config,
        )
        return config, key

    def test_profile_summarizes_config_without_probe_or_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            config, _key = self._configured_runtime(tmp)
            payload = collect_model_runtime_profile(config_path=config)
        self.assertEqual(payload["operation"], "model-runtime-profile")
        self.assertEqual(payload["schema_version"], "model-runtime-profile/v1")
        self.assertIn(payload["overall"], {"ready", "needs_probe"})
        self.assertTrue(payload["profile"]["base_url_configured"])
        self.assertTrue(payload["profile"]["model_configured"])
        self.assertEqual(payload["profile"]["model"], "local-test-model")
        self.assertFalse(payload["profile"]["diagnostic_probe_performed"])
        self.assertFalse(payload["security"]["network_access"])
        self.assertFalse(payload["security"]["local_openai_probe"])
        self.assertFalse(payload["security"]["starts_runtime"])
        self.assertFalse(payload["security"]["downloads_models"])
        self.assertFalse(payload["security"]["cloud_fallback"])
        self.assertFalse(payload["security"]["modifies_files"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["calls_harness"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["external_side_effects"])

    def test_missing_config_needs_config_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            config = Path(tmp) / "missing.json"
            payload = collect_model_runtime_profile(config_path=config)
        self.assertEqual(payload["overall"], "needs_config")
        self.assertFalse(payload["data_touched"]["filesystem_write"])
        self.assertFalse(config.exists())
        self.assertFalse(payload["security"]["modifies_files"])

    def test_rejects_public_runtime_config_without_network(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            config = Path(tmp) / "model-runtime.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "provider": "openai-compatible",
                "base_url": "https://api.example.com",
                "model": "remote-model",
                "api_key_file": str(Path(tmp) / "key"),
            }), encoding="utf-8")
            payload = collect_model_runtime_profile(config_path=config)
        self.assertEqual(payload["overall"], "blocked")
        self.assertFalse(payload["security"]["network_access"])
        self.assertFalse(payload["security"]["uses_credentials"])
        self.assertNotIn("remote-model", json.dumps(payload))

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            config, key = self._configured_runtime(tmp)
            payload = collect_model_runtime_profile(config_path=config)
            rendered = render_model_runtime_profile(payload)
            env = dict(os.environ)
            env.pop("LAI_GATEWAY_MODEL_API_KEY", None)
            completed = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "model-runtime-profile", "--config-path", str(config), "--json"],
                check=False,
                text=True,
                capture_output=True,
                env=env,
            )
        combined = completed.stdout + completed.stderr + rendered
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("model-runtime-profile/v1", completed.stdout)
        self.assertIn("read_only: true", rendered)
        self.assertIn("starts_runtime: false", rendered)
        self.assertIn("local_openai_probe: false", rendered)
        self.assertNotIn("local-test-key-value", combined)
        self.assertNotIn(str(key), combined)
        self.assertNotIn("Bearer", combined)


if __name__ == "__main__":
    unittest.main()
