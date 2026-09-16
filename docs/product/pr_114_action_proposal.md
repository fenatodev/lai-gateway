# PR114 — Action proposal

## Objetivo

Implementar `action-proposal/v1`: uma proposta unificada e read-only que declara domínio, canal, autonomia, capacidade, alvo, dados, efeito e risco antes de aprovação ou execução.

## Escopo

- Adicionar coletor `collect_action_proposal` e renderização textual segura.
- Adicionar CLI `lai-gateway action-proposal --json`.
- Adicionar API protegida `/v1/gateway/action-proposal`.
- Adicionar card mínimo no Workbench.
- Atualizar docs de produto, matriz, readiness e testes.

## Fora de escopo

- Não cria approval inbox.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não executa tools.
- Não chama Harness.
- Não escreve estado local.
- Não faz HOME scan.
- Não faz ingestão implícita.
- Não libera capacidades externas.

## Critério de aceite

A proposta deve declarar os quatro eixos arquiteturais — domínio, canal, autonomia e capacidade — além de alvo, dados, efeito e risco. Dados vindos de `objective-state/v1` devem permanecer marcados como conteúdo não confiável.

Testes devem cobrir proposta completa, derivação a partir de objective state, redaction de segredos, ausência de grant/dispatch/execução/escrita/efeito externo, CLI, API protegida e documentação canônica.
