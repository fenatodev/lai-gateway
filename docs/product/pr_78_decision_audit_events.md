# PR 78 — Decision audit events

## Objetivo

Criar um envelope inicial de eventos de auditoria para a cadeia de decisão do LAI.

Este PR transforma os artefatos já existentes em uma timeline auditável:

- `AdapterInvocationProposal`
- `AuthorizationRecord`
- `PolicyEvaluation`
- `PermissionDecision`

## Escopo

Incluído:

- módulo `audit_events`
- CLI `lai-gateway audit-events`
- endpoint `GET /v1/gateway/audit-events`
- eventos derivados, ordenados e serializáveis
- renderização textual segura
- redaction herdada da proposta de invocação
- testes de endpoint, CLI, segredo e não execução

Fora de escopo:

- persistir eventos reais
- gravar arquivo de auditoria
- assinar eventos
- emitir evento para serviço externo
- executar adapter
- conceder capability
- capturar aprovação humana real

## Invariante de segurança

Um evento de auditoria não é autorização.

Eventos podem registrar que uma decisão exigiria aprovação, mas não podem transformar essa decisão em permissão efetiva.

## Resultado esperado

A resposta deve expor uma timeline mínima com eventos de decisão, política, autorização e proposta.
Todos os eventos devem marcar:

- `persisted: false`
- `effective_authorization: false`
- `dispatch_enabled: false`
- `executes_tools: false`
- `grants_permission: false`

## Risco controlado

O principal risco seria tratar o log como fonte de autoridade. Este PR evita isso mantendo o log read-only, derivado e não persistido.
