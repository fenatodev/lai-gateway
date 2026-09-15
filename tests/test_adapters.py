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
    def test_mcp_foundation_remains_governed_without_tool_execution(self) -> None:
        payload = collect_adapter_registry()
        self.assertEqual(payload["overall"], "ready")
        self.assertGreaterEqual(payload["count"], 1)
        adapter = next(item for item in payload["adapters"] if item["id"] == "mcp")
        self.assertEqual(adapter["id"], "mcp")
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["grants_permissions"])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertFalse(payload["security"]["tool_execution_enabled"])
        self.assertFalse(payload["security"]["grants_permissions"])

    def test_browser_adapter_contract_is_registered_without_execution(self) -> None:
        payload = collect_adapter_registry(adapter_id="browser")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "browser")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["network_access_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertIn("browser.authenticated_session", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_n8n_adapter_contract_is_registered_without_workflow_execution(self) -> None:
        payload = collect_adapter_registry(adapter_id="n8n")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "n8n")
        self.assertEqual(adapter["kind"], "automation_adapter")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["workflow_execution_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertFalse(adapter["external_side_effects_enabled"])
        self.assertIn("n8n.activate_workflow", adapter["human_approval_required_for"])
        self.assertIn("n8n.credentialed_node", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_voice_adapter_contract_is_registered_without_audio_capture_or_action_execution(self) -> None:
        payload = collect_adapter_registry(adapter_id="voice")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "voice")
        self.assertEqual(adapter["kind"], "interface_adapter")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["audio_capture_enabled"])
        self.assertFalse(adapter["wake_word_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertFalse(adapter["external_side_effects_enabled"])
        self.assertIn("voice.capture_microphone", adapter["human_approval_required_for"])
        self.assertIn("voice.invoke_action", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_model_lab_adapter_contract_is_registered_without_downloads_or_benchmarks(self) -> None:
        payload = collect_adapter_registry(adapter_id="model_lab")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "model_lab")
        self.assertEqual(adapter["kind"], "evaluation_adapter")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["model_download_enabled"])
        self.assertFalse(adapter["benchmark_execution_enabled"])
        self.assertFalse(adapter["runtime_mutation_enabled"])
        self.assertFalse(adapter["network_access_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertIn("model_lab.download_model", adapter["human_approval_required_for"])
        self.assertIn("model_lab.run_benchmark", adapter["human_approval_required_for"])
        self.assertIn("model_lab.change_runtime_config", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_social_career_adapter_contract_is_registered_without_external_side_effects(self) -> None:
        payload = collect_adapter_registry(adapter_id="social_career")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "social_career")
        self.assertEqual(adapter["kind"], "automation_adapter")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["publication_enabled"])
        self.assertFalse(adapter["message_sending_enabled"])
        self.assertFalse(adapter["application_submission_enabled"])
        self.assertFalse(adapter["form_submission_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertFalse(adapter["external_side_effects_enabled"])
        self.assertIn("social_career.publish_post", adapter["human_approval_required_for"])
        self.assertIn("social_career.submit_application", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_document_media_adapter_contract_is_registered_without_external_or_destructive_processing(self) -> None:
        payload = collect_adapter_registry(adapter_id="document_media")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["count"], 1)
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "document_media")
        self.assertEqual(adapter["kind"], "content_adapter")
        self.assertEqual(adapter["autonomy"], "contract_only")
        self.assertEqual(adapter["entrypoints"], [])
        self.assertEqual(adapter["granted_capabilities"], [])
        self.assertTrue(adapter["requires_policy_check"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["document_ingestion_enabled"])
        self.assertFalse(adapter["ocr_enabled"])
        self.assertFalse(adapter["transcription_enabled"])
        self.assertFalse(adapter["external_upload_enabled"])
        self.assertFalse(adapter["destructive_processing_enabled"])
        self.assertEqual(adapter["filesystem_scope"], "repo_or_explicit_sandbox_only")
        self.assertIn("document.read_external_path", adapter["human_approval_required_for"])
        self.assertIn("media.upload_external", adapter["human_approval_required_for"])
        self.assertFalse(payload["security"]["tool_execution_enabled"])

    def test_local_status_adapter_is_registered_as_local_only(self) -> None:
        payload = collect_adapter_registry(adapter_id="local_status")
        self.assertEqual(payload["overall"], "ready")
        adapter = payload["adapters"][0]
        self.assertEqual(adapter["id"], "local_status")
        self.assertEqual(adapter["status"], "local_handler")
        self.assertEqual(adapter["granted_capabilities"], ["local_status.status", "local_status.echo"])
        self.assertTrue(adapter["local_handler_registered"])
        self.assertFalse(adapter["executes_tools"])
        self.assertFalse(adapter["network_access_enabled"])
        self.assertFalse(adapter["credentialed_access_enabled"])
        self.assertFalse(adapter["filesystem_write_enabled"])
        self.assertFalse(adapter["shell_execution_enabled"])
        self.assertFalse(adapter["external_side_effects_enabled"])

    def test_adapter_filter_and_cli_are_secret_free(self) -> None:
        missing = collect_adapter_registry(adapter_id="missing")
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
