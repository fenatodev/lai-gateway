from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "docs" / "product"


class WorkbenchLocalOperatorDocsTest(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (PRODUCT / name).read_text(encoding="utf-8")

    def test_pr131_is_documented_as_implemented(self) -> None:
        docs = (
            self._read("index.md"),
            self._read("implementation_matrix.md"),
            self._read("post_pr110_operating_plan.md"),
            self._read("alpha_readiness.md"),
        )

        for content in docs:
            self.assertIn(
                "workbench-local-operator/v1",
                content,
            )

        matrix = self._read("implementation_matrix.md")
        self.assertIn(
            "| workbench_local_operator | implemented |",
            matrix,
        )
        self.assertIn(
            "[PR131](pr_131_workbench_local_operator.md)",
            matrix,
        )

    def test_pr131_docs_do_not_overclaim(self) -> None:
        docs = (
            self._read("workbench_local_operator.md")
            + "\n"
            + self._read("pr_131_workbench_local_operator.md")
        ).lower()

        for marker in (
            "local-operator-runtime/v1",
            "arbitrary",
            "harness",
            "authority",
            "credentials",
            "send messages",
            "publish",
            "merge",
            "natural-language",
        ):
            self.assertIn(marker, docs)

        self.assertIn(
            "does not provide general development autonomy",
            docs,
        )


if __name__ == "__main__":
    unittest.main()
