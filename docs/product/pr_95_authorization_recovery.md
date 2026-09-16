# PR95 — authorization persistence and restart recovery

## Escopo

PR95 implementa persistência local, expiração, revogação, consumo único e recovery para a cadeia estreita `local-status-read`.

Não amplia browser, n8n, voz, MCP tool execution, social/career, documentos, rede, shell, credenciais ou publicação.

## Domínio, canal, autonomia e capacidade

- domínio: governança local de autorização.
- canal: CLI, API local e Workbench loopback.
- autonomia: execução local restrita com autorização persistida de uso único.
- capacidade: somente `local_status.status` via `local-status-read`.

## Mudança funcional

Novo contrato `authorization-recovery/v1` em `lai_gateway/authorization_recovery.py`.

A cadeia agora suporta:

- emitir grant local de autorização (`issue`);
- recuperar/checkar grant após reinício (`check`/`recover`);
- revogar grant antes do uso (`revoke`);
- consumir grant exatamente uma vez antes do dispatch (`consume`);
- bloquear replay, expiração, revogação, falsificação de identidade e troca de alvo/ação.

## Integração com executor

`adapter-dispatcher/v3` exige grant persistido e consumido para despachar `local_status.status` com `local-status-read`.

Sem grant válido, o dispatcher bloqueia antes do handler. O consumo ocorre antes da execução; se o processo falhar depois do consumo, o resultado desconhecido e não há retry automático.

## Segurança preservada

- conteúdo recuperado, canal, skill, adapter ou aprovação textual não concedem permissão;
- ação e parâmetros crus não são persistidos;
- logs são JSONL locais, append-only e confinados ao escopo do repo;
- o handler `local_status.status` continua sem rede, shell, credenciais, tools ou efeito externo;
- existe escrita local de estado de autorização, mas não escrita pelo handler do adapter.

## Evidência

Testes novos e atualizados cobrem emissão, recovery, expiração, revogação, consumo único, replay, endpoint, CLI, sigilo e dispatch com grant.

Gate local: `PYTHON=python3 make check`.
