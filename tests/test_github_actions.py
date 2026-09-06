from __future__ import annotations

import unittest
from pathlib import Path


class GitHubActionsTest(unittest.TestCase):
    def test_ci_runs_on_pr_main_and_version_tags(self) -> None:
        ci = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pull_request:", ci)
        self.assertIn("branches: [main]", ci)
        self.assertIn("tags: ['v*']", ci)
        self.assertIn("Python ${{ matrix.python-version }}", ci)

    def test_actions_are_pinned_to_full_commit_shas(self) -> None:
        ci = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", ci)
        self.assertIn("actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97", ci)
        self.assertNotIn("actions/checkout@v", ci)
        self.assertNotIn("actions/setup-python@v", ci)


if __name__ == "__main__":
    unittest.main()
