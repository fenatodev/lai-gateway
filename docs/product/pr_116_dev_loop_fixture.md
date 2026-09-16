# PR116 — Dev loop fixture

## Objetivo

Adicionar `dev-loop-fixture/v1` como fixture local controlado para validar o caminho Observe/Work/Review/Apply antes de qualquer execução operacional real.

## Escopo

- Lê somente pendências sanitizadas do `approval-inbox/v1` em workspace explícito.
- Seleciona uma aprovação pendente por `approval_id` ou usa a primeira pendente.
- Produz evidência determinística de Observe, Work, Review e Apply.
- Expõe CLI, API protegida e painel mínimo no Workbench.
- Atualiza documentação canônica, matriz, alpha readiness, README e testes.

## Fora de escopo

- Não habilita browser autenticado.
- Não ativa n8n real.
- Não chama MCP amplo.
- Não usa credenciais.
- Não envia mensagem.
- Não publica.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não chama Harness.
- Não executa tools.
- Não escreve source checkout.
- Não faz merge automático.
- Não faz HOME scan.
- Não faz ingestão implícita.

## Segurança

O fixture bloqueia propostas com formato externo ou operacional sensível, incluindo browser, n8n, MCP, credenciais, mensagens, publicação, grants, adapters, tools, Harness, deploy, release e merge.

A etapa `apply` é apenas simulação dentro do fixture. Ela não muda arquivos do projeto e não promove patch para `main`.
