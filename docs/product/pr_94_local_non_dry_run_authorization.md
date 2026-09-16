# PR94 — local non-dry-run authorization

Escopo: provar autorização efetiva para uma única ação real local non-dry-run no `lai-gateway`.

## Objetivo

Adicionar um caminho estreito em que `local_status.status` possa ser autorizado como ação local real, sem dry-run, sem shell, sem rede, sem credenciais e sem filesystem write.

## Regra de arquitetura

A autorização continua separando domínio, canal, autonomia e capacidade. Identidade verificada é pré-condição, mas não concede permissão. Adapter, skill, canal, conteúdo, memória ou texto de aprovação também não concedem permissão.

## Escopo permitido

- adapter: `local_status`
- capability: `local_status.status`
- operation scope: `local-status-read`
- execução: handler Python in-process já existente
- efeitos: leitura local sanitizada, sem segredo, sem write

## Fora de escopo

- `local_status.echo` como autorização non-dry-run
- browser, n8n, voice, MCP tool execution, social/career
- autorização persistida, expiração, revogação e consumo único
- login completo, sessão durável ou approval store
## Critérios de aceite

- `effective_authorization.py` mantém `adapter-dry-run` intacto.
- `local-status-read` só autoriza `local_status.status` com identidade verificada e decisão `allow`.
- O dispatcher só executa `local_status.status` quando a autorização efetiva local é positiva.
- Escopo incorreto, capability incorreta, identidade falsa ou adapter externo bloqueiam.
- Payloads continuam secret-free e sem autoridade externa.
- Testes cobrem casos positivos e negativos.

## Limite deliberado

Este PR não resolve restart recovery nem autorização persistida. Esses pontos pertencem ao PR95.
