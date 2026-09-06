from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from lai_gateway.release import collect_release_check, render_release_check


class ReleaseCheckTest(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def _copy_minimal_project(self, repo: Path) -> None:
        source = Path(__file__).parents[1]
        (repo / "lai_gateway").mkdir()
        (repo / "lai_gateway" / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "lai-gateway"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        (repo / "README.md").write_text("# lai-gateway\n", encoding="utf-8")
        self.assertTrue((source / "lai_gateway" / "release.py").exists())

    def test_release_check_blocks_dirty_candidate_without_mutating_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.email", "test@example.invalid")
            self._git(repo, "config", "user.name", "Test")
            self._copy_minimal_project(repo)
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "initial")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            self._git(repo, "checkout", "-b", "feature/release")
            (repo / "README.md").write_text("# changed\n", encoding="utf-8")

            payload = collect_release_check("0.1.0", repo)

            self.assertEqual(payload["overall"], "blocked")
            self.assertEqual(payload["phase"], "blocked")
            self.assertFalse(payload["tag_ready"])
            self.assertTrue(any(c["name"] == "git_status" and c["status"] == "fail" for c in payload["checks"]))
            self.assertIsNone(payload["tag_target"])

    def test_release_check_candidate_branch_is_ready_for_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.email", "test@example.invalid")
            self._git(repo, "config", "user.name", "Test")
            self._copy_minimal_project(repo)
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "initial")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            self._git(repo, "checkout", "-b", "feature/release")

            payload = collect_release_check("0.1.0", repo)

            self.assertEqual(payload["overall"], "ready")
            self.assertEqual(payload["phase"], "ready_for_integration")
            self.assertFalse(payload["tag_ready"])
            self.assertIn("candidate branch", render_release_check(payload))

    def test_release_check_clean_synced_main_is_ready_to_tag_and_tagged_after_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.email", "test@example.invalid")
            self._git(repo, "config", "user.name", "Test")
            self._copy_minimal_project(repo)
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "initial")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

            ready = collect_release_check("0.1.0", repo)
            self.assertEqual(ready["phase"], "ready_to_tag")
            self.assertTrue(ready["tag_ready"])

            self._git(repo, "tag", "-a", "v0.1.0", "-m", "lai-gateway v0.1.0")
            tagged = collect_release_check("0.1.0", repo)
            self.assertEqual(tagged["phase"], "tagged")
            self.assertFalse(tagged["tag_ready"])
            self.assertEqual(tagged["tag_target"], tagged["head"])

    def test_release_check_rejects_wrong_target_and_tag_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.email", "test@example.invalid")
            self._git(repo, "config", "user.name", "Test")
            self._copy_minimal_project(repo)
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "initial")
            self._git(repo, "remote", "add", "origin", str(repo))
            self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            self._git(repo, "tag", "-a", "v0.1.0", "-m", "old")
            (repo / "README.md").write_text("# second\n", encoding="utf-8")
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "second")
            self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")

            wrong = collect_release_check("0.2.0", repo)
            drift = collect_release_check("0.1.0", repo)

            self.assertEqual(wrong["overall"], "blocked")
            self.assertEqual(drift["overall"], "blocked")
            self.assertTrue(any(c["name"] == "tag_state" and c["status"] == "fail" for c in drift["checks"]))


if __name__ == "__main__":
    unittest.main()
