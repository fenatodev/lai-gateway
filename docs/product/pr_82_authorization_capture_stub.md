# PR 82 — authorization capture stub

## Objetivo

Criar uma superfície explícita para representar intenção humana de aprovação sem transformar essa intenção em autorização efetiva.

## Escopo

- adicionar `AuthorizationCaptureStub`;
- expor CLI `lai_gateway authorization-capture-stub`;
- expor endpoint `GET /v1/gateway/authorization-capture-stub`;
- conectar o stub ao dry-run de adapter existente;
- manter a captura não persistida, não validada e não efetiva.

## Fora de escopo

- aprovar execução real de adapter;
- persistir autorização;
- validar identidade forte do aprovador;
- criar sessão de aprovação;
- executar browser, n8n, voz, MCP ou documentos;
- conceder capability solicitada.

## Regras

- texto de aprovação não concede permissão;
- canal não concede permissão;
- adapter não concede permissão;
- captura em solicitação bloqueada continua bloqueada;
- `effective_authorization` permanece `false`;
- `dispatch_enabled` permanece `false`.

## Próximo passo

PR 83 deve validar um capture stub contra decisão, policy, dry-run e expiração antes de qualquer autorização efetiva futura.
