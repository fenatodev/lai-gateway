from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests.fake_harness as fake
from lai_gateway.config import GatewayConfig
from lai_gateway.errors import ConfigError, HarnessHTTPError
from lai_gateway.harness_client import (
    HarnessClient,
    MCP_REDACTED_VALUE,
    normalize_run_list_payload,
    sanitize_mcp_payload,
    sanitize_mobile_harness_payload,
    sanitize_run_events_payload,
)

from .fake_harness import TOKEN, fake_harness


class HarnessClientTest(unittest.TestCase):
    def test_fetches_contract_status_readiness_and_sessions_with_bearer_auth(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            contract = client.gateway_contract()
            self.assertEqual(contract["version"], "0.4.7")
            self.assertEqual(client.status()["product"], "lai harness")
            self.assertEqual(client.readiness()["overall"], "ready")
            listed_sessions = client.list_sessions()
            created_session = client.create_session()
            fetched_session = client.get_session("cs-1234567890abcdef")
            for payload in (listed_sessions, created_session, fetched_session):
                shown = str(payload)
                self.assertNotIn("repository", payload)
                self.assertNotIn("/home/example/private", shown)
                self.assertNotIn("workspace_path", shown)
                self.assertNotIn("cwd", shown)
            self.assertEqual(listed_sessions["sessions"][0]["session_id"], "cs-1234567890abcdef")
            self.assertEqual(created_session["session"]["session_id"], "cs-1234567890abcdef")
            self.assertEqual(fetched_session["session"]["session_id"], "cs-1234567890abcdef")
            deleted = client.delete_session("cs-1234567890abcdef")
            self.assertTrue(deleted["session"]["deleted"])
            self.assertEqual(deleted["session"]["session_id"], "cs-1234567890abcdef")
            self.assertNotIn("/home/example/private", str(deleted))

    def test_fetches_and_creates_read_only_runs_with_bounded_body(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))

            listed = client.list_runs(limit=1)
            created = client.create_read_only_run(
                mode="plan",
                task="Summarize current state.",
                session_id="cs-1234567890abcdef",
            )
            fetched = client.get_run("cr-1234567890abcdef")
            events = client.get_run_events("cr-1234567890abcdef")

            for payload in (listed, created, fetched):
                shown = str(payload)
                self.assertNotIn("repository", payload)
                self.assertNotIn("/home/example/private", shown)
                self.assertNotIn("workspace_path", shown)
                self.assertNotIn("metrics_file", shown)
                self.assertNotIn("audit_file", shown)
            self.assertEqual(listed["runs"][0]["control_run_id"], "cr-1234567890abcdef")
            self.assertEqual(created["run"]["control_run_id"], "cr-1234567890abcdef")
            self.assertEqual(fetched["run"]["status"], "succeeded")
            self.assertEqual(events["control_run_id"], "cr-1234567890abcdef")
            self.assertEqual([event["event"] for event in events["events"]], ["queued", "started", "finished"])
            shown = str(events)
            self.assertNotIn("repository", events)
            self.assertNotIn("/home/example/private", shown)
            self.assertNotIn("leaked fake response", shown)
            self.assertNotIn("leaked task text", shown)
            self.assertNotIn("leaked stderr", shown)
            self.assertNotIn("stdout", shown)
            self.assertNotIn("stderr", shown)
            self.assertNotIn("task", shown)
            self.assertEqual(fake.LAST_RUN_BODY, {
                "mode": "plan",
                "session_id": "cs-1234567890abcdef",
                "task": "Summarize current state.",
            })

    def test_rejects_malformed_control_run_and_session_ids_before_network(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))

            for session_id in ("s_test", "cs-123", "cs-zzzzzzzzzzzzzzzz", "cs-1234567890abcdef/extra"):
                with self.subTest(session_id=session_id):
                    with self.assertRaises(ConfigError):
                        client.get_session(session_id)
                    with self.assertRaises(ConfigError):
                        client.delete_session(session_id)
                    with self.assertRaises(ConfigError):
                        client.create_read_only_run(mode="plan", task="x", session_id=session_id)

            for run_id in ("cr_test", "run-1", "cr-123", "cr-zzzzzzzzzzzzzzzz", "cr-1234567890abcdef/extra"):
                with self.subTest(run_id=run_id):
                    with self.assertRaises(ConfigError):
                        client.get_run(run_id)
                    with self.assertRaises(ConfigError):
                        client.get_run_events(run_id)
    def test_mobile_harness_sanitizer_strips_local_paths_and_raw_run_text(self):
        payload = sanitize_mobile_harness_payload({
            "repository": "/home/example/private/repo",
            "session": {
                "session_id": "cs-1234567890abcdef",
                "cwd": "/home/example/private/repo",
            },
            "run": {
                "control_run_id": "cr-1234567890abcdef",
                "stdout": "raw output",
                "note": "see /home/example/private/repo/src/app.py and src/app.py",
            },
            "events": [{"event": "started", "details": {"stderr": "raw error", "path": "src/app.py"}}],
        })

        shown = str(payload)
        self.assertNotIn("repository", payload)
        self.assertNotIn("/home/example/private", shown)
        self.assertNotIn("cwd", shown)
        self.assertNotIn("stdout", shown)
        self.assertNotIn("stderr", shown)
        self.assertIn("[redacted-local-path]", shown)
        self.assertIn("src/app.py", shown)


    def test_run_events_sanitizer_removes_output_task_and_transcript_fields(self):
        payload = sanitize_run_events_payload({
            "control_run_id": "cr-1234567890abcdef",
            "stdout": "secret output",
            "stderr": "secret error",
            "task": "secret task",
            "transcripts": [{"content": "hidden"}],
            "events": [{"event": "started", "details": {"turns": ["hidden"], "output_truncated": False}}],
        })

        shown = str(payload)
        self.assertNotIn("secret output", shown)
        self.assertNotIn("secret error", shown)
        self.assertNotIn("secret task", shown)
        self.assertNotIn("hidden", shown)
        self.assertEqual(payload["events"][0]["details"]["output_truncated"], False)


    def test_run_list_normalizer_only_promotes_control_run_shaped_legacy_ids(self):
        payload = {
            "runs": [
                {"run_id": "cr-1234567890abcdef", "status": "queued"},
                {"run_id": "1788786034784-598834", "status": "observed"},
            ]
        }

        normalized = normalize_run_list_payload(payload)

        self.assertEqual(normalized["runs"][0]["control_run_id"], "cr-1234567890abcdef")
        self.assertNotIn("control_run_id", normalized["runs"][1])



    def test_fetches_mcp_broker_metadata_and_policy_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))

            status = client.mcp_status()
            tools = client.mcp_tools()
            policy = client.mcp_policy_check(
                operation="call-tool",
                server="desktop-commander",
                tool="start_process",
            )

            self.assertEqual(status["overall"], "ready")
            self.assertEqual(status["server_count"], 1)
            self.assertFalse(status["security"]["executes_tools"])
            self.assertEqual(tools["servers"][0]["name"], "desktop-commander")
            self.assertEqual(policy["decision"], "DENY")
            self.assertFalse(policy["executed"])
            self.assertIn("MCP tool execution is not enabled", policy["reason"])

            with self.assertRaises(ConfigError):
                client.mcp_policy_check(operation="execute-tool")

    def test_redacts_secret_shaped_mcp_payload_fields(self):
        payload = sanitize_mcp_payload({
            "overall": "ready",
            "security": {
                "executes_tools": False,
                "prints_credentials": False,
                "authorization": "Bearer harness-secret-value",
            },
            "servers": [{
                "name": "desktop-commander",
                "env": {
                    "LAI_GATEWAY_MODEL_API_KEY": "model-secret-value",
                    "NORMAL_SETTING": "safe",
                },
            }],
        })

        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["prints_credentials"])
        self.assertEqual(payload["security"]["authorization"], MCP_REDACTED_VALUE)
        self.assertEqual(payload["servers"][0]["env"]["LAI_GATEWAY_MODEL_API_KEY"], MCP_REDACTED_VALUE)
        self.assertEqual(payload["servers"][0]["env"]["NORMAL_SETTING"], "safe")

    def test_rejects_write_modes_before_contacting_harness(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            with self.assertRaises(ConfigError):
                client.create_read_only_run(mode="implement", task="change files")

    def test_wrong_token_returns_bounded_harness_http_error(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text("wrong", encoding="utf-8")
            client = HarnessClient(GatewayConfig(harness_url=harness.url, token_file=token_file))
            with self.assertRaises(HarnessHTTPError) as caught:
                client.status()
            self.assertEqual(caught.exception.status, 401)


if __name__ == "__main__":
    unittest.main()
