# PR102 — release alpha técnico

## Escopo

Preparar a publicação source-first do alpha técnico `0.1.35` com nota de release
versionada, sem mudança funcional. A publicação externa só pode ocorrer depois de
`release-check` e `alpha-readiness` passarem em `main` e de aprovação humana
explícita para tag/release.

## Dimensões LAI

- Domínio: release técnico do `lai-gateway`.
- Canal: Git/GitHub release, quando aprovado separadamente.
- Autonomia: baixa para publicação; humana para tag/release.
- Capacidade: documentação, gates e nota de release; nenhuma capacidade externa.

## Aceitação

- `docs/releases/v0.1.35.md` existe e evita overclaiming.
- `docs/product/index.md` referencia PR102 e a nota de release.
- `post_pr100_roadmap.md` mantém PR102 como release source-first.
- `make check` passa.
- Nenhuma tag, release ou publicação é criada por esta spec isoladamente.

## Fora de escopo

Sem código funcional, browser, n8n, MCP tool execution amplo, voz, social/carreira,
credenciais, PDF/OCR/Office amplo, pacote externo, instalador, serviço hospedado
ou anúncio público automático.
