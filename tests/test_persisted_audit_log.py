from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from lai_gateway.config import GatewayConfig
from lai_gateway.persisted_audit_log import collect_persisted_audit_log, render_persisted_audit_log

from .fake_harness import TOKEN, fake_harness
from .test_ui import RunningGateway


class PersistedAuditLogTest(unittest.TestCase):
    def test_default_plan_does_not_write_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = collect_persisted_audit_log(
                adapter_id="browser",
                requested_capability="browser.navigate_public",
                approval_intent=True,
                audit_dir=".lai/audit",
                scope_root=Path(tmp),
            )
            self.assertEqual(payload["status"], "planned")
            self.assertFalse(payload["persisted"])
            self.assertFalse((Path(tmp) / ".lai" / "audit").exists())
            self.assertTrue(payload["security"]["requires_explicit_write"])
            self.assertFalse(payload["security"]["stores_raw_parameters"])

    def test_explicit_write_appends_jsonl_inside_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = collect_persisted_audit_log(
                adapter_id="browser",
                requested_capability="browser.navigate_public",
                action="open public docs",
                approval_intent=True,
                audit_dir=".lai/audit",
                write=True,
                scope_root=Path(tmp),
            )
            self.assertEqual(payload["status"], "written")
            self.assertTrue(payload["persisted"])
            log_path = Path(tmp) / ".lai" / "audit" / "governance-audit.jsonl"
            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["status"], "written")
            self.assertEqual(record["operation_scope"], "adapter-dry-run")
            self.assertFalse(record["adapter_capability_authorized"])
            self.assertFalse(record["dispatch_enabled"])

    def test_second_write_appends_without_truncating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for item in ("one", "two"):
                collect_persisted_audit_log(
                    adapter_id="browser",
                    requested_capability="browser.navigate_public",
                    action=item,
                    approval_intent=True,
                    audit_dir="audit",
                    write=True,
                    scope_root=Path(tmp),
                )
            log_path = Path(tmp) / "audit" / "governance-audit.jsonl"
            self.assertEqual(len(log_path.read_text(encoding="utf-8").splitlines()), 2)

    def test_rejects_path_outside_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = collect_persisted_audit_log(
                adapter_id="browser",
                requested_capability="browser.navigate_public",
                approval_intent=True,
                audit_dir="../outside",
                write=True,
                scope_root=Path(tmp),
            )
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["persisted"])
            self.assertIn("scope root", payload["reason"])

    def test_sensitive_values_and_raw_action_are_not_stored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = collect_persisted_audit_log(
                adapter_id="n8n",
                requested_capability="n8n.plan_workflow",
                action="use token private-action-value",
                parameters={"api_key": "private-param-value"},
                approval_intent=True,
                audit_dir="audit",
                write=True,
                scope_root=Path(tmp),
            )
            text = json.dumps(payload, sort_keys=True)
            self.assertNotIn("private-param-value", text)
            self.assertNotIn("private-action-value", text)
            log_path = Path(tmp) / "audit" / "governance-audit.jsonl"
            line = log_path.read_text(encoding="utf-8")
            self.assertNotIn("private-param-value", line)
            self.assertNotIn("private-action-value", line)

    def test_render_and_cli_are_secret_free(self) -> None:
        payload = collect_persisted_audit_log(
            adapter_id="browser",
            requested_capability="browser.navigate_public",
            approval_intent=True,
        )
        rendered = render_persisted_audit_log(payload)
        self.assertIn("persisted-audit-log", rendered)
        self.assertIn("persisted: false", rendered)
        self.assertIn("append_only: true", rendered)
        self.assertNotIn(TOKEN, rendered)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lai_gateway",
                "persisted-audit-log",
                "--adapter",
                "browser",
                "--capability",
                "browser.navigate_public",
                "--approve",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cli_payload = json.loads(result.stdout)
        self.assertFalse(cli_payload["persisted"])
        self.assertNotIn(TOKEN, result.stdout)

    def test_gateway_endpoint_is_read_only_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(harness_url=harness.url, token_file=token_file)
            with RunningGateway(config) as gateway:
                url = f"{gateway.url}/v1/gateway/persisted-audit-log?adapter=browser&capability=browser.navigate_public&approve=true"
                with urlopen(url, timeout=5) as response:
                    body = response.read().decode("utf-8")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    status = response.status
        self.assertEqual(status, 200)
        self.assertEqual(headers["cache-control"], "no-store")
        payload = json.loads(body)
        self.assertEqual(payload["operation"], "persisted-audit-log")
        self.assertFalse(payload["persisted"])
        self.assertFalse(payload["write_requested"])
        self.assertNotIn(TOKEN, body)


if __name__ == "__main__":
    unittest.main()
