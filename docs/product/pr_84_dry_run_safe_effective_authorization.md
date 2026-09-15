# PR 84 — Dry-run-safe effective authorization

## Objetivo

Introduzir uma autorização efetiva extremamente limitada para operações internas consideradas dry-run-safe.

Este PR não autoriza execução real de adapter. Ele apenas permite representar `effective_authorization=true` quando a aprovação humana foi capturada, validada e o escopo autorizado é exclusivamente `adapter-dry-run`.

## Escopo

Incluído:

- Novo módulo `effective_authorization`.
- Nova CLI `lai_gateway effective-authorization`.
- Novo endpoint `GET /v1/gateway/effective-authorization`.
- Testes para escopo seguro, bloqueio de escopo real e ausência de vazamento de segredo.

Excluído:

- Dispatcher real de adapter.
- Execução de browser, n8n, voz, modelos ou documentos.
- Persistência de autorização.
- Persistência de audit log.
- Uso de credenciais.
## Regra crítica

A autorização efetiva deste PR é de escopo operacional, não de capability do adapter.

Mesmo quando `effective_authorization=true`:

- `operation_scope=adapter-dry-run`
- `scope_authorized=true`
- `adapter_capability_authorized=false`
- `dispatch_enabled=false`
- `adapter_dispatched=false`
- `adapter_executed=false`
- `executes_tools=false`
- `grants_permission=false`

## Risco tratado

Aprovação validada não pode virar permissão ampla. Qualquer escopo diferente de `adapter-dry-run` falha fechado.
