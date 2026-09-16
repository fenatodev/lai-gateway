# PR104 — Onboarding/UX com próximos passos sanitizados

## Objetivo

Reduzir fricção inicial no Workbench sem ampliar autoridade operacional. O PR104
introduz uma superfície de onboarding read-only que mostra próximos passos para
Harness, token, modelo local e documento restrito.

## Contrato

- Domínio: onboarding operacional local.
- Canal: Workbench e endpoint local do Gateway.
- Autonomia: diagnóstico read-only.
- Capacidade: `onboarding-next-steps/v1`.
- Executor: Gateway local em processo, sem shell e sem tools.
- Dados tocados: estado sanitizado de diagnóstico; nenhum segredo é exibido.
- Efeito externo: nenhum.

## Aceitação

- Workbench mostra próximos passos para Harness/token/modelo/documento.
- Falhas de Harness, token, modelo e documento aparecem sem token, path privado,
  prompt, conteúdo de documento ou bearer.
- Onboarding não inicia servidor, não instala dependências, não executa shell,
  não chama browser, não ativa n8n e não executa MCP tool.
- Conteúdo recuperado continua sem autoridade e sem permissão.
