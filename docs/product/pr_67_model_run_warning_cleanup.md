# PR 67 — model run warning cleanup

## Objetivo

Remover o `SyntaxWarning` em `lai_gateway/model.py` causado por `return` dentro de
`finally`, sem alterar o contrato público de `model-runs`.

## Escopo

- manter gravação append-only de registros de modelo;
- manter arquivo com permissão `0600`;
- manter payload `record.status == "written"` no caminho feliz;
- adicionar cobertura para impedir regressão do warning.

## Fora de escopo

- mudar formato JSONL;
- mudar coleta de métricas de modelo;
- alterar rotas HTTP;
- iniciar runtime de modelo;
- instalar dependências.
