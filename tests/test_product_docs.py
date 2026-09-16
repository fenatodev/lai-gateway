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
        for state in ("implemented", "experimental", "contract", "simulado/dry-run", "planned", "Disponível ao usuário"):
            self.assertIn(state, text)
        self.assertIn("browser | contract", text)
        self.assertIn("n8n | contract", text)
        self.assertIn("voice | contract", text)
        self.assertIn("local_status adapter | experimental", text)
        self.assertIn("instalação pública | planned", text)

    def test_alpha_readiness_blocks_overclaiming(self) -> None:
        text = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        promise = text.split("## Promessa pública permitida", 1)[1].split("## ", 1)[0]
        self.assertIn(
            "Não declarar browser agent completo, automação n8n real, voz operacional, "
            "MCP tool execution generalizado, automação social/carreira com envio real, "
            "processamento completo de documentos/mídia ou instalação one-click universal.",
            promise,
        )
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
        self.assertIn(
            "Browser/n8n/MCP/social reais ficam depois de PR93, PR94 e PR95, fora da sequência até PR100.",
            external,
        )
        self.assertIn(
            "Continuam bloqueados na expansão governada: browser autenticado, n8n activation, "
            "MCP tool execution amplo, publicação, envio de mensagens, candidaturas, formulários, "
            "automações externas e uso de credenciais.", external,
        )
        for capability in ("browser autenticado", "n8n activation", "MCP tool execution amplo", "publicação", "envio de mensagens", "candidaturas", "formulários", "automações externas", "uso de credenciais"):
            self.assertIn(capability, external)

    def test_matrix_does_not_promote_contracts_or_dry_run_to_execution(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        rows = {}
        for line in text.splitlines():
            if line.startswith("| ") and not line.startswith("| ---"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0]] = cells[1:]
        for area in ("browser", "n8n", "voice", "MCP execution", "social/career", "document/media", "identidade usuário/cliente/agente/serviço"):
            self.assertEqual(rows[area][0], "contract", area)
        self.assertEqual(rows["effective authorization"][0], "experimental")
        self.assertEqual(rows["adapter dry-run"][0], "implemented")
        self.assertEqual(rows["adapter dry-run"][1], "simulado/dry-run")
        self.assertEqual(
            rows["Área"],
            ["Maturidade", "Tipo de execução", "Disponível ao usuário", "Evidência", "Limite conhecido", "Próximo marco"],
        )
        for area, cells in rows.items():
            if area != "Área":
                self.assertEqual(len(cells), 6, area)
                self.assertIn(cells[0], {"implemented", "experimental", "contract", "planned"}, area)
                self.assertRegex(cells[3], r"\[[^]]+\]\([^)]+\.md\)|\[[^]]+\]\([^)]+\.(?:py|js|sh)\)")
        self.assertIn(
            "Sem execução de tools por esse adapter; apenas metadata/policy-check; executes_tools=false.",
            rows["MCP execution"][4],
        )
        self.assertNotIn("Model Lab / Scout", rows)
        self.assertIn("adapters.py", rows["Model Lab"][3])
        self.assertIn("skills.py", rows["Scout"][3])
        self.assertEqual(rows["Scout"][1], "metadados de skill")
        self.assertIn(
            "Apenas adapter-dry-run; adapter_capability_authorized=false; authorization_persisted=false",
            rows["effective authorization"][4],
        )
        for term in ("adapter-dry-run", "authorization_persisted=false", "declarado", "simulado", "efetivamente imposto"):
            self.assertIn(term, text)


    def test_public_restrictions_are_complete_in_canonical_documents(self) -> None:
        restrictions = (
            "Browser, n8n, voz, execução real de tools MCP, social e automações externas "
            "governadas não estão disponíveis como funcionalidades prontas. "
            "Contratos e simulações não autorizam execução real.",
            "local_status é apenas o primeiro adapter seguro restrito; não prova autorização geral.",
            "Telegram outbound tem limite conhecido: não possui aprovação durável por mensagem.",
        )
        for name in ("roadmap.md", "alpha_readiness.md", "implementation_matrix.md"):
            text = (PRODUCT_DOCS / name).read_text(encoding="utf-8")
            for restriction in restrictions:
                with self.subTest(document=name, restriction=restriction):
                    self.assertIn(restriction, text)

    def test_readme_preserves_public_caveats(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        scope = text.split("## Current scope", 1)[1].split("## Requirements", 1)[0]
        for statement in (
            "Effective authorization currently covers only `adapter-dry-run`; the real "
            "`local_status` handler is a separate, tightly allowlisted in-process path, "
            "not proof of general authorization.",
            "Browser, n8n, voice, broad MCP execution and social/career automation "
            "are not ready-to-use features.",
            "It is not general agent messaging authority or durable per-message approval.",
            "New governed sends require explicit approval of content and destination plus the roadmap gates.",
            "A public technical alpha is planned, not declared ready or complete.",
        ):
            self.assertIn(statement, scope)
        for name in ("index.md", "roadmap.md", "implementation_matrix.md", "alpha_readiness.md"):
            self.assertIn(f"](docs/product/{name})", scope)

    def test_index_classifies_documents_and_defines_precedence(self) -> None:
        text = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        for classification in (
            "**normativo** — [Roadmap]",
            "**matriz de estado, descritivo** — [Implementation matrix]",
            "**prontidão alpha, critérios normativos** — [Alpha readiness]",
            "**descritivo, consolidação de revisão externa** — [Consolidação das revisões]",
            "**revisão externa / histórico** — [Revisão Astra]",
            "**spec de PR / histórico**",
        ):
            self.assertIn(classification, text)
        self.assertIn(
            "Para sequência prevalece o roadmap; para estado atual, a matriz; "
            "para publicação, os critérios de readiness.", text,
        )
        self.assertIn(
            "Revisões externas e specs históricas não sobrepõem os documentos normativos atuais", text,
        )

    def test_matrix_evidence_links_exist(self) -> None:
        text = (PRODUCT_DOCS / "implementation_matrix.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+)\)", text)
        self.assertTrue(links)
        for link in links:
            self.assertTrue((PRODUCT_DOCS / link).is_file(), link)


    def test_public_quickstart_exists_and_is_source_first(self) -> None:
        quickstart = ROOT / "docs" / "quickstart.md"
        self.assertTrue(quickstart.is_file())
        text = quickstart.read_text(encoding="utf-8")
        for statement in (
            "source checkout validation",
            "editable local wrapper installation without `pip install`",
            "scripts/install-local.sh",
            "export PATH=\"$HOME/.local/bin:$PATH\"",
            "PYTHON=python3 make check",
            "lai-gateway-stack-check",
            "--harness-repo /path/to/workspace/lai-harness-checkout",
            "lai-gateway doctor",
            "lai-gateway readiness",
            "lai-gateway dev --bind 127.0.0.1 --port 8787 --no-open",
            "http://127.0.0.1:8787/",
            "lai-gateway stack-start --check-only",
        ):
            self.assertIn(statement, text)

    def test_public_quickstart_does_not_overclaim_alpha_capabilities(self) -> None:
        text = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
        for statement in (
            "It does not cover a one-click installer, PyPI release, hosted service, cloud",
            "authenticated browser sessions, real n8n activation, broad MCP",
            "external message/publication automation",
            "prove general adapter authorization",
            "does not enable browser, n8n, voice, MCP",
            "LAI is a finished product.",
        ):
            self.assertIn(statement, text)
        self.assertNotIn("one-click installer is ready", text)
        self.assertNotIn("browser automation is ready", text)
        self.assertNotIn("n8n workflows are ready", text)

    def test_pr91_is_linked_from_canonical_public_docs(self) -> None:
        self.assertTrue((PRODUCT_DOCS / "pr_91_public_quickstart.md").is_file())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        index = (PRODUCT_DOCS / "index.md").read_text(encoding="utf-8")
        roadmap = (PRODUCT_DOCS / "roadmap.md").read_text(encoding="utf-8")
        alpha = (PRODUCT_DOCS / "alpha_readiness.md").read_text(encoding="utf-8")
        self.assertIn("](docs/quickstart.md)", readme)
        self.assertIn("[Quickstart](../quickstart.md)", index)
        self.assertIn("`docs/quickstart.md`", roadmap)
        self.assertIn("Após o PR91, `docs/quickstart.md`", alpha)
        self.assertIn("não transforma o alpha em produto completo", alpha)

if __name__ == "__main__":
    unittest.main()
