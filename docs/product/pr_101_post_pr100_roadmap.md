# PR101 — post-PR100 roadmap

PR101 cria o roadmap normativo pós-PR100. O objetivo é evitar que `candidate_go` técnico vire expansão implícita de escopo.

## Escopo

- Adicionar `docs/product/post_pr100_roadmap.md`.
- Atualizar o índice canônico para apontar o novo roadmap.
- Atualizar o roadmap PR90–PR100 para declarar que a sequência foi concluída e que próximos trabalhos usam o documento pós-PR100.
- Adicionar teste documental para PR101.

## Fora de escopo

- Sem tag.
- Sem release.
- Sem publicação.
- Sem código funcional.
- Sem browser, n8n, MCP tool execution, voz, social/carreira ou credenciais.
- Sem nova autorização por memória, documento, modelo ou ferramenta.

## Gate

- `python3 -m unittest tests.test_product_docs -v` verde.
- `PYTHON=python3 make check` verde.
- `git diff --check` verde.
- Nenhuma promessa pública de produto completo ou capacidade externa pronta.
