# PR 85 — Scoped persisted audit log

## Objetivo

Adicionar persistência local e escopada para registros de auditoria de governança do LAI.

Este PR cria apenas um log sanitizado em JSONL. Ele não executa adapters, não amplia autorização e não transforma aprovação em permissão de ferramenta.

## Problema

Até o PR 84, a cadeia de governança era observável, mas efêmera:

- decisão de permissão;
- avaliação de policy;
- registro de autorização;
- proposta de invocação;
- dry-run;
- captura e validação de aprovação;
- autorização efetiva restrita ao escopo interno `adapter-dry-run`.

Faltava um formato persistível para auditoria local.

## Decisão

Criar `persisted-audit-log/v1` com:

- arquivo fixo `governance-audit.jsonl`;
- escrita append-only;
- diretório validado dentro do escopo local do LAI;
- payload reduzido, sem parâmetros brutos;
- ação armazenada apenas como hash;
- endpoint read-only por padrão;
- CLI só grava com `--write` explícito.

## Fora do escopo

- log remoto;
- banco de dados;
- rotação de logs;
- assinatura criptográfica;
- garantia antiforense;
- execução de adapter;
- autorização da capability do adapter;
- armazenamento de prompt, segredo, token ou payload bruto.

## Invariantes

Mesmo quando o registro é gravado:

- `adapter_capability_authorized=false`;
- `dispatch_enabled=false`;
- `adapter_dispatched=false`;
- `adapter_executed=false`;
- `executes_tools=false`;
- `external_side_effects=false`;
- `grants_permission=false`.

## Superfícies

- CLI: `lai_gateway persisted-audit-log`
- Endpoint: `GET /v1/gateway/persisted-audit-log`

O endpoint retorna plano read-only e não grava arquivo.
