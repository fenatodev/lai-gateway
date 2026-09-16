from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lai_gateway.action_proposal import collect_action_proposal, render_action_proposal


class ActionProposalTest(unittest.TestCase):
    def test_complete_explicit_action_proposal_is_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_action_proposal(
                workspace_root=workspace,
                scope_root=Path(tmp),
                actor="user",
                domain="project",
                channel="workbench",
                autonomy="high",
                capability="dev-local-change",
                action="prepare PR114 action proposal",
                target="lai_gateway/action_proposal.py",
                data="objective state and explicit request fields",
                effect="create a reviewable local proposal only",
                risk="low",
            )
        self.assertEqual(payload["operation"], "action-proposal")
        self.assertEqual(payload["schema_version"], "action-proposal/v1")
        self.assertEqual(payload["overall"], "ready")
        proposal = payload["proposal"]
        self.assertEqual(proposal["domain"], "project")
        self.assertEqual(proposal["channel"], "workbench")
        self.assertEqual(proposal["autonomy"], "high")
        self.assertEqual(proposal["capability"], "dev-local-change")
        self.assertEqual(proposal["target"], "lai_gateway/action_proposal.py")
        self.assertEqual(proposal["data"], "objective state and explicit request fields")
        self.assertEqual(proposal["effect"], "create a reviewable local proposal only")
        self.assertEqual(proposal["risk"], "low")
        self.assertTrue(proposal["proposal_only"])
        self.assertFalse(proposal["effective_authorization"])
        self.assertFalse(payload["security"]["issues_grants"])
        self.assertFalse(payload["security"]["dispatches_adapter"])
        self.assertFalse(payload["security"]["executes_tools"])
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["filesystem_write"])
        self.assertFalse(payload["security"]["implicit_ingestion"])

    def test_can_derive_untrusted_objective_task_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            state_dir = workspace / ".lai"
            state_dir.mkdir(parents=True)
            (state_dir / "objective-state.json").write_text(json.dumps({
                "schema_version": "objective-state/v1",
                "project_id": "lai-gateway",
                "objective": "Alpha operacional local",
                "tasks": [{
                    "id": "pr114",
                    "title": "Build unified action proposal",
                    "status": "todo",
                    "domain": "project",
                    "channel": "workbench",
                    "autonomy": "high",
                    "capability": "action-proposal",
                    "target": "lai_gateway/action_proposal.py",
                    "risk": "medium",
                }],
            }), encoding="utf-8")
            payload = collect_action_proposal(
                workspace_root=workspace,
                scope_root=Path(tmp),
                task_id="pr114",
                data="objective-state/v1 selected task",
                effect="produce proposal JSON only",
            )
        proposal = payload["proposal"]
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(proposal["source"], "objective-state-untrusted")
        self.assertEqual(proposal["objective_task_id"], "pr114")
        self.assertEqual(proposal["capability"], "action-proposal")
        self.assertEqual(proposal["risk"], "medium")
        self.assertTrue(payload["objective_state"]["content_read"])
        self.assertTrue(payload["objective_state"]["untrusted_content"])
        self.assertFalse(payload["objective_state"]["content_grants_authority"])
        self.assertFalse(payload["security"]["approval_inferred"])

    def test_secret_shapes_are_redacted_and_blocked_state_does_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_action_proposal(
                workspace_root=workspace,
                state_file="../bad.json",
                scope_root=Path(tmp),
                action="send token=supersecretvalue",
                data="password=supersecretvalue",
                effect="publish externally",
                capability="social-post",
                target="external-service",
                domain="project",
                channel="workbench",
                autonomy="high",
                risk="high",
            )
        text = json.dumps(payload)
        self.assertEqual(payload["overall"], "blocked")
        self.assertTrue(payload["security"]["secret_redacted"])
        self.assertTrue(payload["security"]["proposed_external_effect"])
        self.assertNotIn("supersecretvalue", text)
        self.assertFalse(payload["security"]["external_side_effects"])
        self.assertFalse(payload["security"]["executes_tools"])

    def test_render_and_cli_are_secret_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            workspace = Path(tmp) / "project"
            workspace.mkdir()
            payload = collect_action_proposal(
                workspace_root=workspace,
                scope_root=Path(tmp),
                domain="project",
                channel="cli",
                autonomy="none",
                capability="action-proposal",
                action="explain proposal",
                target="docs/product/action_proposal.md",
                data="explicit fields",
                effect="render only",
                risk="low",
            )
            text = render_action_proposal(payload)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "action-proposal",
                    "--workspace-root",
                    str(workspace),
                    "--domain",
                    "project",
                    "--channel",
                    "cli",
                    "--autonomy",
                    "none",
                    "--capability",
                    "action-proposal",
                    "--action",
                    "explain proposal",
                    "--target",
                    "docs/product/action_proposal.md",
                    "--data",
                    "explicit fields",
                    "--effect",
                    "render only",
                    "--risk",
                    "low",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        cli_payload = json.loads(result.stdout)
        self.assertEqual(cli_payload["operation"], "action-proposal")
        self.assertEqual(cli_payload["schema_version"], "action-proposal/v1")
        self.assertIn("action-proposal/v1", text)
        self.assertIn("effective_authorization: false", text)
        self.assertNotIn("Bearer", result.stdout)
        self.assertNotIn("token=", result.stdout)


if __name__ == "__main__":
    unittest.main()
