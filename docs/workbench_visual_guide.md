# LAI Workbench visual guide

Guia visual mínimo e sanitizado para reconhecer o fluxo atual do Workbench. Ele
não é prova de novas capacidades; é uma referência para operador técnico validar
a UI local sem expor segredos.

## Escopo

O Workbench atual é local-first, loopback-only para fluxos de local-chat/work
quando suportados pelo Harness. O guia cobre:

- navegação inicial;
- estado de saúde/readiness;
- conversa normal `@lai` sem criar run dev implícito;
- painel Governance;
- fluxo seguro `local_status`;
- coleta de evidência visual sanitizada.

Ficam fora: browser agent, n8n real, voz operacional, MCP tool execution amplo,
automação social/carreira, publicação externa, leitura arbitrária de arquivos e
qualquer uso de credenciais.

## Mapa visual conceitual

```text
+----------------------------------------------------------------+
| LAI Gateway / Workbench                         health summary |
+----------------------+-------------------------+---------------+
| navigation / project | chat / current task     | governance    |
|                      |                         | status        |
| - current workspace  | @lai direct response    | readiness     |
| - runs/sessions      | no implicit dev run     | capture       |
| - model/status       |                         | validation    |
|                      |                         | authorization |
|                      |                         | dispatcher    |
+----------------------+-------------------------+---------------+
| advanced/debug: collapsed by default; sanitized only            |
+----------------------------------------------------------------+
```

A imagem acima é um mapa de referência, não uma captura real. Capturas reais não
devem conter token, chat id, caminho privado, prompt sensível, conteúdo de usuário
ou payload bruto de ferramenta.

## Fluxo visual esperado

1. Abrir `http://127.0.0.1:8787/`.
2. Ver resumo de saúde com estados claros: ready, warn ou blocked.
3. Usar chat normal para conversa direta. Conversa não cria run no Harness por si
   só.
4. Abrir Governance para inspecionar a cadeia: approval capture, validation,
   effective authorization e dispatcher.
5. Selecionar somente `local_status.status` ou `local_status.echo` quando for
   testar o primeiro adapter local seguro.
6. Confirmar que outras integrações permanecem como contrato, simulação ou
   indisponíveis.

## Fluxo `local_status`

O caminho seguro atual deve mostrar estas propriedades:

- adapter nomeado explicitamente como `local_status`;
- capability restrita a `local_status.status` ou `local_status.echo`;
- execução in-process e local;
- sem shell;
- sem filesystem write;
- sem rede externa;
- sem credenciais;
- sem MCP tool call;
- sem envio de mensagem;
- sem prova de autorização geral.

`local_status.echo` não deve expor texto bruto do operador; deve retornar apenas
metadados/digest quando aplicável.

## Evidência visual sanitizada

Para anexar evidência em PR ou release checklist, capture somente:

- topo da UI com URL loopback, sem query string sensível;
- resumo ready/warn/blocked;
- painel Governance com nomes de etapas, sem payload bruto;
- resultado `local_status` com metadados não sensíveis;
- ausência visível de botões que prometam browser/n8n/MCP/social prontos.

Antes de publicar uma captura, o operador deve redigir:

- tokens e pair tokens;
- chat ids;
- endereços privados não necessários;
- paths pessoais;
- prompts de usuário;
- diffs com conteúdo privado;
- logs brutos.

## Critérios de aceite visual

- A UI aponta para operação local, não serviço hospedado.
- Estados de saúde são distinguíveis sem depender apenas de cor.
- Governance deixa claro que inspeção não é autorização ampla.
- `local_status` aparece como caminho restrito, não como prova geral.
- Debug fica recolhido ou sanitizado.
- Não há promessa visual de browser, n8n, voz, MCP amplo, social ou publicação.
- Qualquer falha de Harness/token/modelo aparece como bloqueio ou alerta, não
  como sucesso presumido.

## Limite

Este guia não implementa UI nova. Ele documenta a superfície atual e define o
padrão mínimo para evidência visual sanitizada até que PRs posteriores ampliem as
capacidades de forma governada.
