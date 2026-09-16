# LAI — documentação de produto

Índice canônico pós-PR90. O LAI busca ser um sistema operacional pessoal de IA local, open-source-first e modular. Direção de produto não é evidência de capacidade operacional.

## Documentos atuais

- **guia operacional público** — [Quickstart](../quickstart.md): instalação local source-first, diagnóstico e primeiro uso restrito.
- **checklist operacional público** — [Release checklist](../release_checklist.md): verificação source-only de versão, commit, CI e gates locais.
- **guia visual público** — [Workbench visual guide](../workbench_visual_guide.md): mapa sanitizado do Workbench, Governance e `local_status`.
- **normativo** — [Roadmap](roadmap.md): sequência normativa pós-PR89, dependências e gates.
- **matriz de estado, descritivo** — [Implementation matrix](implementation_matrix.md): maturidade, evidência e disponibilidade ao usuário.
- **prontidão alpha, critérios normativos** — [Alpha readiness](alpha_readiness.md): limitações conhecidas e decisão go/no-go.
- **descritivo, consolidação de revisão externa** — [Consolidação das revisões](roadmap_review_consolidation.md): insumos externos, decisões aceitas e adiadas.
- **normativo** — [Padrão de produto](lai_product_standard.md): princípios de produto.
- **normativo** — [Decisões arquiteturais](lai_architecture_decisions.md): separação de domínio, canal, autonomia e capacidade; contratos de direção, não comprovação de execução.

## Precedência documental

Para sequência prevalece o roadmap; para estado atual, a matriz; para publicação, os critérios de readiness. Contratos arquiteturais não concedem autoridade nem substituem evidência de runtime. As políticas do repositório continuam aplicáveis. Revisões externas e specs históricas não sobrepõem os documentos normativos atuais; em conflito sobre implementação, conferir código/testes e corrigir a matriz, sem inferir capacidades de uma intenção normativa.

## Histórico e insumos

Os documentos `pr_*.md` têm rótulo **spec de PR / histórico**: são registros históricos do escopo e da aceitação de cada PR; não são orientação operacional atual nem prova de maturidade posterior. Nenhum histórico foi removido.

- **histórico** — [Fila antiga](lai_next_prs.md): histórica, substituída pelo roadmap.
- **revisão externa / histórico** — [Revisão Astra](astra_architecture_review.md) e [revisão Codex/Astra](codex_astra_architecture_review.md): insumos históricos, sem autoridade automática.
- **descritivo / insumo de revisão externa** — [Prompt de revisão](roadmap_review_prompt.md): instrumento de coleta, não decisão.
- **spec de PR / histórico** — [PR89](pr_89_roadmap_alpha_readiness.md): baseline histórico da consolidação.

GPT-6/Astra, Claude e Codex são revisores. Recomendações precisam de confronto com código, testes e decisão humana versionada. Documentos antigos fora desta lista devem ser lidos no contexto da versão e do escopo em que foram escritos.
