# PR 92 — release checklist e guia visual mínimo do Workbench

## Objetivo

Entregar o gate PR92 do roadmap: versão/artefato identificáveis, release
checklist source-only e guia visual mínimo do Workbench com evidência sanitizada.

## Escopo

- Criar `docs/release_checklist.md`.
- Criar `docs/workbench_visual_guide.md`.
- Linkar os documentos a partir de `README.md`, `docs/product/index.md`,
  `docs/product/roadmap.md` e `docs/product/alpha_readiness.md`.
- Fortalecer testes documentais para versionamento, release checklist e guia
  visual.

## Fora de escopo

- Bump de versão.
- Tag, release GitHub, PyPI, binário ou instalador one-click.
- Mudança funcional de UI.
- Harness, adapters, autorização non-dry-run, browser, n8n, voz, MCP execution,
  social/career, envio de mensagens ou processamento de documentos.

## Decisões

O artefato identificável atual é source-first: versão declarada em
`lai_gateway.__version__` e `pyproject.toml`, mais commit integrado em `main` por
PR com CI verde. O checklist operacional não concede autoridade de publicação.

O guia visual é sanitizado e descritivo. Ele explica como reconhecer o fluxo
Workbench/Governance/local_status, mas não afirma que `local_status` prova
autorização geral.

## Riscos

- Prometer release público antes de readiness.
- Confundir checklist com publicação automática.
- Expor segredos em evidência visual.
- Sugerir que Governance/local_status habilita adapters externos.

## Gates

- `docs/release_checklist.md` descreve comandos e no-go sem publicar nada.
- `docs/workbench_visual_guide.md` descreve evidência visual sanitizada.
- README e índice canônico apontam para ambos.
- Testes documentais protegem ausência de overclaiming.
- `python3 -m unittest tests.test_product_docs -v` verde.
- `PYTHON=python3 make check` verde.
- `git diff --check` verde.
