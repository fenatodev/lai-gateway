# PR 81 — Workbench dry-run visibility

## Objetivo

Expor o `adapter-dry-run` no painel Governança do LAI Workbench.

O objetivo é tornar visível o primeiro dry-run governado criado no PR 80 sem transformar a UI em superfície de execução real.

## Escopo

Incluído:

- botão `Dry-run` no painel Governança;
- saída dedicada `dry-run-output`;
- carregamento do dry-run dentro de `Atualizar cadeia`;
- resumo visual que diferencia dry-run simulado de dispatch real;
- testes de HTML/JS para garantir presença da superfície.

Fora de escopo:

- executar adapter real;
- capturar aprovação humana;
- persistir autorização;
- gravar log de auditoria real;
- criar botão de dispatch;
- usar credenciais, rede externa ou filesystem externo.
