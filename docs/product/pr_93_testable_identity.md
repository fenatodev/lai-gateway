# PR 93 — Testable principal identity

## Objetivo

Adicionar um vínculo testável de identidade para usuário, cliente, agente e serviço nos caminhos de governança do LAI Gateway.

Este PR não cria login, sessão persistente, credencial nova, autorização efetiva non-dry-run ou capability externa. Identidade verificada é pré-condição de avaliação; não é permissão.

## Dimensões LAI

- Domínio: governança local de autorização.
- Canal: CLI local e HTTP Gateway loopback/private-token.
- Autonomia: leitura/avaliação, sem execução adicional.
- Capacidade: identity binding, sem elevação de adapter, skill, canal ou conteúdo.

## Entrega

- Novo objeto `principal-identity/v1` com `user_id`, `client_id`, `agent_id`, `service_id`, `identity_source` e `identity_binding_id`.
- Origem confiável explícita: local CLI, gateway loopback, private-token ou fixture de teste.
- Rejeição de fonte não confiável, claims falsos e drift de binding esperado.
- Propagação mínima para permission decision, policy evaluation e authorization record.
## Gate de saída

- Testes provam binding estável ao principal.
- Testes provam que identidade declarada/falsificada por input não substitui a origem confiável.
- Testes provam que troca de cliente ou serviço causa drift/bloqueio quando há binding esperado.
- Saídas CLI/API não imprimem tokens, credenciais nem segredos.
- Governança continua fail-closed se a identidade não for verificada.

## Fora de escopo

- Autenticação humana completa.
- Persistência de identidade.
- Aprovação durável por mensagem.
- Browser, n8n, voz, MCP tool execution amplo, social/carreira ou documentos.
- Mudanças no Harness.
