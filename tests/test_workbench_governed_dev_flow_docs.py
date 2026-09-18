from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "docs/product"


class WorkbenchGovernedDevFlowDocsTest(unittest.TestCase):
    def test_current_docs_record_pr132_contract(self) -> None:
        for name in (
            "index.md",
            "implementation_matrix.md",
            "post_pr110_operating_plan.md",
            "alpha_readiness.md",
        ):
            content = (PRODUCT / name).read_text(encoding="utf-8")
            self.assertIn(
                "workbench-governed-dev-flow/v1",
                content,
                msg=name,
            )

    def test_contract_preserves_architecture_boundaries(self) -> None:
        content = (
            (PRODUCT / "workbench_governed_dev_flow.md").read_text(
                encoding="utf-8"
            )
            + "\n"
            + (
                PRODUCT
                / "pr_132_conversation_first_governed_dev_flow.md"
            ).read_text(encoding="utf-8")
        ).lower()

        for marker in (
            "direct",
            "harness",
            "review",
            "apply",
            "explicit",
            "no automatic promotion",
            "natural-language",
            "git push",
            "pull requests",
            "merge",
        ):
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
