# PR 83 — authorization validation gate

## Objetivo

Criar um gate determinístico para validar uma captura explícita de aprovação
sem transformar essa validação em autorização efetiva.

## Contexto

O PR 82 introduziu um stub de captura. Isso registra intenção explícita, mas
não prova que a cadeia inteira continua consistente. O PR 83 adiciona uma
camada separada para conferir a captura contra decision, policy, authorization
record, proposal, dry-run e audit log.

## Contrato

A nova superfície `authorization-validation-gate` deve:

- aceitar apenas metadados públicos e bounded;
- reutilizar a cadeia existente de capture stub e dry-run;
- falhar fechado quando a ação, adapter ou capability forem bloqueados;
- validar somente capturas explícitas ligadas a dry-run simulado;
- manter `effective_authorization=false` mesmo quando validado;
- manter `dispatch_enabled=false` e `adapter_dispatched=false`;
- não persistir autorização nem log.

## Fora de escopo

- execução real de adapter;
- autorização efetiva;
- persistência de autorização;
- UI de aprovação;
- credenciais;
- rede externa;
- qualquer elevação por canal, skill, adapter ou texto de aprovação.

## Superfícies

- `lai_gateway.authorization_validation`
- CLI `lai-gateway authorization-validation-gate`
- endpoint `GET /v1/gateway/authorization-validation-gate`
- testes em `tests/test_authorization_validation.py`
