# LAI implementation matrix

## status

Matriz de estado pós-PR88. Use este arquivo para distinguir promessa de produto, contrato e implementação real.

## legenda

```text
implemented: funcional e testado
experimental: funcional com escopo estreito
contract: declarado, mas execução real bloqueada ou ausente
planned: previsto no roadmap
blocked: depende de etapa anterior
deferred: adiado intencionalmente
```

## matriz

| área | estado | evidência atual | próximo marco |
| --- | --- | --- | --- |
| arquitetura core | implemented | decisões, contratos e docs PR61 | manter como base normativa |
| conversation-first | implemented | chat comum sem run no harness | melhorar UX e modelo local |
| Workbench 3 modos | experimental | Observar, Trabalhar e Aplicar existem na UI | guia visual e fluxo alpha |
| dev assistido | experimental | local-chat, sandbox, review e promotion via Harness | documentação pública e install |
| permission decision | implemented | decisão estável por capability | vincular a roadmap em novos PRs |
| policy evaluator | implemented | policy falha fechado e redige entradas sensíveis | ampliar granularidade por capability |
| authorization record | implemented | envelope não efetivo | persistir apenas quando escopo permitir |
| audit events | implemented | eventos derivados sem persistência | conectar a audit log local quando necessário |
| persisted audit log | experimental | JSONL local append-only sanitizado | consultar e rotacionar logs |
| adapter dry-run | implemented | simulação sem dispatch | usar como pré-gate de adapters reais |
| authorization capture | implemented | captura intenção sem autorização efetiva | adicionar validade/expiração formal |
| authorization validation | implemented | valida cadeia sem executar | aplicar a capacidades externas futuras |
| effective authorization | experimental | efetiva apenas para escopo `adapter-dry-run` | separar escopos por ação real |
| adapter dispatcher | experimental | interface e dispatch local allowlisted | bloquear regressões de adapters sensíveis |
| local_status adapter | experimental | primeiro handler real in-process | manter como smoke path seguro |
| model local | experimental | status, probes, task/eval locais quando runtime existe | primeira execução guiada |
| memory_context | planned | definido como core, ainda sem store consolidado | store local por projeto |
| document/media | contract | adapter declarado sem processamento real | document_text_local seguro |
| browser | contract | adapter declarado sem navegação real | browser_public read-only |
| n8n | contract | adapter declarado sem workflow real | discovery/dry-run local |
| voice | contract | adapter/canal declarado sem captura real | push-to-talk local |
| MCP execution | contract | metadata e policy-check sem tool execution | execução governada allowlisted |
| Telegram inbound | planned | outbound/status já existe; inbound sensível ausente | conversa/status sem run sensível |
| social/career | contract | drafts/automação declarados sem side effects | drafts locais sem envio |
| instalação pública | planned | install local existe, mas quickstart público incompleto | alpha install guide |
| release GitHub | planned | CI verde e docs, sem release alpha consolidada | tag 0.2.0-alpha |

## regra de atualização

Toda mudança funcional pós-PR89 deve atualizar esta matriz quando alterar o estado de uma área.
