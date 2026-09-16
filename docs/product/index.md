# LAI — documentação de produto

Índice canônico pós-PR90. O LAI busca ser um sistema operacional pessoal de IA local, open-source-first e modular. Direção de produto não é evidência de capacidade operacional.

## Documentos atuais

- [Roadmap](roadmap.md): sequência normativa pós-PR89, dependências e gates.
- [Implementation matrix](implementation_matrix.md): maturidade, evidência e disponibilidade ao usuário.
- [Alpha readiness](alpha_readiness.md): limitações conhecidas e decisão go/no-go.
- [Consolidação das revisões](roadmap_review_consolidation.md): insumos externos, decisões aceitas e adiadas.
- [Padrão de produto](lai_product_standard.md): princípios de produto.
- [Decisões arquiteturais](lai_architecture_decisions.md): separação de domínio, canal, autonomia e capacidade; contratos de direção, não comprovação de execução.

Para sequência prevalece o roadmap; para estado atual, a matriz; para publicação, os critérios de readiness. Contratos arquiteturais não concedem autoridade nem substituem evidência de runtime. As políticas do repositório continuam aplicáveis.

## Histórico e insumos

Os documentos `pr_*.md` são registros históricos do escopo e da aceitação de cada PR; não são orientação operacional atual nem prova de maturidade posterior. Nenhum histórico foi removido.

- [Fila antiga](lai_next_prs.md): histórica, substituída pelo roadmap.
- [Revisão Astra](astra_architecture_review.md) e [revisão Codex/Astra](codex_astra_architecture_review.md): insumos históricos, sem autoridade automática.
- [Prompt de revisão](roadmap_review_prompt.md): instrumento de coleta, não decisão.
- [PR89](pr_89_roadmap_alpha_readiness.md): baseline histórico da consolidação.

GPT-6/Astra, Claude e Codex são revisores. Recomendações precisam de confronto com código, testes e decisão humana versionada. Documentos antigos fora desta lista devem ser lidos no contexto da versão e do escopo em que foram escritos.
