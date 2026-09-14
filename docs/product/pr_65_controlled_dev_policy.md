# PR 65 — dev controlado

## objetivo

Expor o contrato mínimo de desenvolvimento controlado do LAI sem criar novo executor.

## escopo

- Documentar os caminhos oficiais de dev: conversa, plano read-only, trabalho em sandbox e promoção revisada.
- Criar uma policy read-only consultável pelo Gateway.
- Explicitar que work modes não passam pela rota genérica `/v1/harness/runs`.
- Explicitar que promoção exige revisão, workspace, run id e hash de patch.

## fora de escopo

- Não executar dev agent novo.
- Não alterar harness.
- Não aplicar patch automaticamente.
- Não fazer merge/push/publicação a partir da policy.
- Não integrar browser, n8n ou voice.

## contrato

O Gateway só pode expor planejamento read-only via `/v1/harness/runs`. Trabalho controlado usa a superfície local-chat/workbench e depende do Harness para sandbox, revisão e promoção. A policy é informativa e não concede permissões.
