from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkbenchLocalOperatorUiTest(unittest.TestCase):
    def test_workbench_exposes_fixed_profiles_without_command_field(self) -> None:
        html = (ROOT / "lai_gateway/static/index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('id="local-operator-profile"', html)
        self.assertIn('data-action="run-local-operator"', html)
        self.assertIn('id="local-operator-output"', html)

        for profile in (
            "status",
            "diff-check",
            "diff-stat",
            "compile",
            "gate-tests",
            "full-check",
        ):
            self.assertIn(f'value="{profile}"', html)

        self.assertNotIn('id="local-operator-command"', html)
        self.assertNotIn('id="local-operator-repo-root"', html)

    def test_browser_posts_only_selected_profile(self) -> None:
        js = (ROOT / "lai_gateway/static/app.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'requestJson("/v1/gateway/local-operator"',
            js,
        )
        self.assertIn("body: JSON.stringify({ profile })", js)
        self.assertNotIn("local-operator-command", js)
        self.assertNotIn("local-operator-repo-root", js)

    def test_gateway_body_rejects_extra_operator_fields(self) -> None:
        server = (ROOT / "lai_gateway/server.py").read_text(
            encoding="utf-8"
        )

        start = server.index("def _read_workbench_local_operator_body")
        end = server.index("def _read_memory_context_body", start)
        reader = server[start:end]

        self.assertIn('allowed_keys={"profile"}', reader)
        self.assertNotIn("command", reader)
        self.assertNotIn("repo_root", reader)
        self.assertNotIn("execute", reader)

    def test_gateway_operator_route_does_not_call_harness(self) -> None:
        server = (ROOT / "lai_gateway/server.py").read_text(
            encoding="utf-8"
        )

        start = server.index(
            'if parsed.path == "/v1/gateway/local-operator"'
        )
        end = server.index(
            'if parsed.path == "/v1/gateway/memory-context"',
            start,
        )
        route = server[start:end]

        self.assertIn("collect_workbench_local_operator", route)
        self.assertIn("Path(__file__).resolve().parents[1]", route)
        self.assertNotIn("self.server.client", route)
        self.assertNotIn('body["repo_root"]', route)
        self.assertNotIn('body["command"]', route)


if __name__ == "__main__":
    unittest.main()
