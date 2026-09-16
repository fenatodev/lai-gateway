from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.objective_state import collect_objective_state, render_objective_state


class ObjectiveStateTest(unittest.TestCase):
    def test_missing_state_is_needs_state_without_writing_or_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_objective_state(workspace_root=workspace, scope_root=Path(tmp))
        self.assertEqual(payload["operation"], "objective-state")
        self.assertEqual(payload["schema_version"], "objective-state/v1")
        self.assertEqual(payload["overall"], "needs_state")
        self.assertFalse(payload["data_touched"]["content_read"])
        self.assertFalse(payload["data_touched"]["filesystem_write"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["scans_home"])
        self.assertFalse(payload["security"]["implicit_ingestion"])

    def test_loads_explicit_workspace_objective_state_as_untrusted_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            state_dir = workspace / ".lai"
            state_dir.mkdir(parents=True)
            state_file = state_dir / "objective-state.json"
            state_file.write_text(json.dumps({
                "schema_version": "objective-state/v1",
                "project_id": "lai-gateway",
                "objective": "Alpha operacional local",
                "status": "active",
                "tasks": [{
                    "id": "pr113",
                    "title": "Objective state read-only",
                    "status": "doing",
                    "domain": "project",
                    "channel": "workbench",
                    "autonomy": "high",
                    "capability": "objective-state",
                    "target": ".lai/objective-state.json",
                    "risk": "low",
                }],
                "checkpoints": [{"id": "cp1", "summary": "PR112 merged"}],
            }), encoding="utf-8")
            payload = collect_objective_state(workspace_root=workspace, scope_root=Path(tmp))
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["state"]["project_id"], "lai-gateway")
        self.assertEqual(payload["state"]["objective"], "Alpha operacional local")
        self.assertEqual(payload["state"]["tasks"][0]["domain"], "project")
        self.assertEqual(payload["state"]["tasks"][0]["channel"], "workbench")
        self.assertEqual(payload["state"]["tasks"][0]["capability"], "objective-state")
        self.assertTrue(payload["data_touched"]["content_read"])
        self.assertEqual(payload["data_touched"]["state_file"], ".lai/objective-state.json")
        self.assertTrue(payload["storage"]["state_sha256"])
        self.assertTrue(payload["security"]["untrusted_content"])
        self.assertFalse(payload["security"]["content_grants_authority"])

    def test_rejects_traversal_absolute_out_of_scope_symlink_and_secret_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = Path(tmp)
            workspace = scope / "project"
            workspace.mkdir()
            outside = scope / "outside"
            outside.mkdir()
            self.assertEqual(collect_objective_state(workspace_root=outside, scope_root=workspace)["overall"], "blocked")
            self.assertEqual(collect_objective_state(workspace_root=workspace, state_file="../x.json", scope_root=scope)["overall"], "blocked")
            self.assertEqual(collect_objective_state(workspace_root=workspace, state_file=str(scope / "x.json"), scope_root=scope)["overall"], "blocked")
            state_dir = workspace / ".lai"
            state_dir.mkdir()
            target = outside / "objective-state.json"
            target.write_text("{}", encoding="utf-8")
            (state_dir / "linked.json").symlink_to(target)
            self.assertEqual(collect_objective_state(workspace_root=workspace, state_file=".lai/linked.json", scope_root=scope)["overall"], "blocked")
            secret_file = state_dir / "objective-state.json"
            secret_file.write_text('{"schema_version":"objective-state/v1","objective":"token=supersecretvalue"}', encoding="utf-8")
            secret_payload = collect_objective_state(workspace_root=workspace, scope_root=scope)
        self.assertEqual(secret_payload["overall"], "blocked")
        self.assertNotIn("supersecretvalue", json.dumps(secret_payload))

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            (workspace / ".lai").mkdir(parents=True)
            (workspace / ".lai" / "objective-state.json").write_text(json.dumps({
                "schema_version": "objective-state/v1",
                "project_id": "lai-gateway",
                "objective": "Sem segredos",
                "tasks": [{"id": "t1", "title": "Checar estado", "status": "todo"}],
            }), encoding="utf-8")
            payload = collect_objective_state(workspace_root=workspace, scope_root=Path(tmp))
            text = render_objective_state(payload)
            result = subprocess.run(
                [sys.executable, "-m", "lai_gateway", "objective-state", "--workspace-root", str(workspace), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "objective-state")
        self.assertEqual(cli_payload["schema_version"], "objective-state/v1")
        self.assertIn("objective-state/v1", text)
        self.assertIn("read_only: true", text)
        self.assertNotIn("Bearer", result.stdout)
        self.assertNotIn("token=", result.stdout)


if __name__ == "__main__":
    unittest.main()
