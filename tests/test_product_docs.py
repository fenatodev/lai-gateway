import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DOCS = ROOT / "docs" / "product"


class ProductDocsTest(unittest.TestCase):
    def test_post_pr90_canonical_artifacts_exist(self) -> None:
        for name in (
            "index.md",
            "roadmap_review_consolidation.md",
            "roadmap.md",
            "implementation_matrix.md",
            "alpha_readiness.md",
            "roadmap_review_prompt.md",
            "pr_89_roadmap_alpha_readiness.md",
        ):
            path = PRODUCT_DOCS / name
            self.assertTrue(path.exists(), name)
            self.assertGreater(len(path.read_text(encoding="utf-8")), 200, name)

    def test_roadmap_preserves_lai_architecture_dimensions(self) -> None:
        text = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        for term in ("domínio", "canal", "autonomia", "capacidade"):
            self.assertIn(term, text)
        for reviewer in ("GPT-6", "Astra", "Claude", "Codex"):
            self.assertIn(reviewer, text)
        self.assertIn("não são autoridade automática", text)

    def test_matrix_distinguishes_contract_from_implemented(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        for state in ("implemented", "experimental", "contract", "simulated", "planned", "Disponível ao usuário"):
            self.assertIn(state, text)
        self.assertIn("browser | contract", text)
        self.assertIn("n8n | contract", text)
        self.assertIn("voice | contract", text)
        self.assertIn("local_status adapter | experimental", text)
        self.assertIn("instalação pública | planned", text)

    def test_alpha_readiness_blocks_overclaiming(self) -> None:
        text = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        for forbidden_claim in (
            "browser agent completo",
            "automação n8n real",
            "voz operacional",
            "MCP tool execution generalizado",
        ):
            self.assertIn(forbidden_claim, text)
        for criterion in ("Limitações conhecidas", "Quickstart reproduzível", "instalação limpa", "versionamento", "overclaiming", "restart recovery", "No-go"):
            self.assertIn(criterion, text)
        self.assertIn("Ainda não está apto a ser chamado de produto completo", text)


    def test_canonical_index_links_resolve_and_readme_points_to_it(self) -> None:
        text = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+\.md)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue((PRODUCT_DOCS / link).is_file(), link)
        self.assertIn("históricos", text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("](docs/product/index.md)", readme)

    def test_roadmap_gates_precede_external_capabilities(self) -> None:
        text = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| PR(\d+) \| (.+)$", text, re.MULTILINE)
        self.assertEqual([int(number) for number, _ in rows], list(range(90, 101)))
        milestones = dict(rows)
        for number, terms in {
            "93": ("Identidade testável", "usuário/cliente/agente/serviço"),
            "94": ("authorization non-dry-run", "revalidação no executor"),
            "95": ("Persistência", "expiração", "revogação", "consumo único", "restart recovery", "duplicação de efeito"),
        }.items():
            for term in terms:
                self.assertIn(term, milestones[number])
            self.assertLess(text.index(f"| PR{number} |"), text.index("## Capacidades externas"))
        external = text.split("## Capacidades externas", 1)[1]
        self.assertIn("depois de PR93, PR94 e PR95", external)
        for capability in ("browser autenticado", "n8n activation", "MCP tool execution amplo", "publicação", "envio de mensagens", "candidaturas", "formulários", "automações externas", "uso de credenciais"):
            self.assertIn(capability, external)

    def test_matrix_does_not_promote_contracts_or_dry_run_to_execution(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        rows = {}
        for line in text.splitlines():
            if line.startswith("| "):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0]] = cells[1:]
        for area in ("browser", "n8n", "voice", "MCP execution", "social/career", "document/media", "identidade usuário/cliente/agente/serviço"):
            self.assertEqual(rows[area][0], "contract", area)
        self.assertEqual(rows["effective authorization"][0], "experimental")
        self.assertEqual(rows["adapter dry-run"][0], "simulated")
        for term in ("adapter-dry-run", "authorization_persisted=false", "declarado", "simulado", "efetivamente imposto"):
            self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
