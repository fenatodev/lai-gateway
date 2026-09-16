import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.context_pack import collect_context_pack, render_context_pack
from lai_gateway.memory_context import collect_memory_context


class ContextPackTest(unittest.TestCase):
    def test_builds_explicit_local_context_pack_without_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / ".lai").mkdir()
            (workspace / ".lai" / "objective-state.json").write_text(json.dumps({
                "schema_version": "objective-state/v1",
                "project_id": "demo",
                "objective": "Ship the local context pack",
                "status": "active",
                "tasks": [{
                    "task_id": "t1",
                    "title": "Collect selected local context",
                    "status": "doing",
                    "domain": "project",
                    "channel": "workbench",
                    "autonomy": "none",
                    "capability": "context-pack",
                    "target": "notes.md",
                    "risk": "low",
                }],
            }), encoding="utf-8")
            (workspace / "notes.md").write_text("Local design note for context pack.", encoding="utf-8")
            remembered = collect_memory_context(
                memory_action="remember",
                context_kind="project",
                project_id="demo",
                note="Prefer explicit local context only.",
                memory_dir=".lai/memory",
                scope_root=workspace,
                actor="user",
                channel="test",
                domain="context-pack",
            )
            self.assertEqual(remembered["overall"], "ready")

            payload = collect_context_pack(
                workspace_root=workspace,
                project_id="demo",
                documents=["notes.md"],
                scope_root=Path.cwd(),
            )

        self.assertEqual(payload["operation"], "context-pack")
        self.assertEqual(payload["schema_version"], "context-pack/v1")
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["context_pack"]["project_id"], "demo")
        self.assertGreaterEqual(payload["context_pack"]["source_count"], 3)
        source_types = {source["source_type"] for source in payload["context_pack"]["sources"]}
        self.assertIn("objective", source_types)
        self.assertIn("objective-task", source_types)
        self.assertIn("memory", source_types)
        self.assertIn("document", source_types)
        self.assertTrue(payload["security"]["read_only"])
        self.assertTrue(payload["security"]["untrusted_content"])
        self.assertFalse(payload["security"]["content_grants_authority"])
        self.assertFalse(payload["security"]["effective_authorization"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["consumes_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["scans_home"])
        self.assertFalse(payload["security"]["recursive_scan"])
        self.assertFalse(payload["security"]["implicit_ingestion"])
        self.assertFalse(payload["security"]["embeddings_required"])
        self.assertFalse(payload["security"]["embedding_generation"])

    def test_rejects_traversal_out_of_scope_and_secret_documents(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / "secret.md").write_text("token=supersecretvalue123", encoding="utf-8")
            traversal = collect_context_pack(
                workspace_root=workspace,
                documents=["../escape.md"],
                scope_root=Path.cwd(),
            )
            outside = collect_context_pack(
                workspace_root=Path(tmp).parent,
                documents=["secret.md"],
                scope_root=workspace,
            )
            secret = collect_context_pack(
                workspace_root=workspace,
                documents=["secret.md"],
                scope_root=Path.cwd(),
            )

        for payload in (traversal, outside, secret):
            self.assertEqual(payload["overall"], "blocked")
            self.assertFalse(payload["security"]["filesystem_write"])
            self.assertFalse(payload["security"]["executes_tools"])
            self.assertFalse(payload["security"]["external_side_effects"])
        self.assertIn("selected document source is blocked", secret["reason"])
        self.assertNotIn("supersecretvalue123", json.dumps(secret))

    def test_memory_secret_is_redacted_not_authoritative(self) -> None:
        payload = collect_context_pack(
            workspace_root=".",
            project_id="demo",
            documents=[],
            scope_root=Path.cwd(),
        )
        self.assertNotEqual(payload["overall"], "blocked")
        self.assertFalse(payload["security"]["memory_grants_authority"])
        self.assertFalse(payload["security"]["approval_inferred"])

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            (workspace / "notes.md").write_text("hello context", encoding="utf-8")
            payload = collect_context_pack(
                workspace_root=workspace,
                documents=["notes.md"],
                scope_root=Path.cwd(),
            )
            rendered = render_context_pack(payload)
            command = [
                sys.executable,
                "-m",
                "lai_gateway",
                "context-pack",
                "--workspace-root",
                str(workspace),
                "--document",
                "notes.md",
                "--json",
            ]
            completed = subprocess.run(command, check=False, text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("context-pack/v1", completed.stdout)
        self.assertIn("read_only: true", rendered)
        self.assertIn("executes_tools: false", rendered)
        self.assertNotIn("Bearer", completed.stdout + rendered)
        self.assertNotIn("token=", completed.stdout + rendered)


if __name__ == "__main__":
    unittest.main()
