# PR 79 - Workbench/UI decision visibility

## Objetivo

Expor no LAI Workbench a cadeia governada de decisão sem criar uma superfície de execução.

O usuário deve conseguir visualizar, a partir da UI local:

1. permission decision;
2. policy evaluation;
3. authorization record;
4. adapter invocation proposal;
5. audit events derivados.

## Escopo

- Adicionar painel de Governança ao Workbench local.
- Permitir informar adapter, capability, ação e um parâmetro público opcional.
- Buscar endpoints read-only já existentes do Gateway.
- Mostrar saída bruta sanitizada em `<pre>` usando `textContent`.
- Manter todas as ações em modo consulta.

## Fora de escopo

- Botão de executar adapter.
- Captura de aprovação humana.
- Persistência de autorização.
- Escrita de log real.
- Chamada de browser, n8n, voz, MCP tool ou serviço externo.
- Elevação de permissão por canal, skill, conteúdo ou texto de aprovação.

## Contrato de segurança

O painel é apenas visibilidade. Ele não transforma `requires_approval` em `allow`, não faz dispatch e não grava autorização efetiva.

A UI deve continuar sem `localStorage`, `sessionStorage` ou `innerHTML` e não deve armazenar tokens. Dados sensíveis formatados como parâmetro devem ser redigidos pelos endpoints antes de aparecerem na tela.

## Validação esperada

- Testes de UI verificam presença do painel e dos botões read-only.
- Testes de assets verificam uso dos endpoints de decisão e ausência de armazenamento local.
- `make check` deve permanecer verde.
