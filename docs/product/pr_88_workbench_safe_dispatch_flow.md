# PR 88 — Workbench safe dispatch flow

## Objetivo

Conectar o painel Governança do LAI Workbench ao fluxo mínimo:

1. Capturar intenção de aprovação.
2. Validar a cadeia de autorização.
3. Calcular autorização efetiva escopada.
4. Inspecionar dispatcher.
5. Executar somente o adapter local seguro `local_status`.

O PR prova o caminho humano-visible de approve → validate → dispatch sem liberar adapters sensíveis.

## Escopo

Incluído:

- UI para `authorization-capture-stub`.
- UI para `authorization-validation-gate`.
- UI para `effective-authorization`.
- UI para `adapter-dispatcher`.
- Botão explícito para `dispatch-local-status`.
- Restrição client-side para `local_status.status` e `local_status.echo`.
- Confirmação humana antes do dispatch local.
## Fora de escopo

- Browser real.
- n8n real.
- MCP tool call real.
- Voz, microfone ou wake word.
- Ingestão de documentos ou mídia.
- Shell/subprocess.
- Rede externa.
- Credenciais.
- Leitura/escrita de arquivos pelo adapter.

## Invariantes

- A UI não transforma domínio, canal ou texto em permissão.
- O botão de dispatch exige `local_status` explicitamente selecionado.
- `local_status.echo` não devolve texto bruto; apenas digest/metadados.
- Qualquer adapter diferente permanece bloqueado pelo dispatcher/backend.
- O painel mantém botões read-only separados do botão de dispatch.
## Validação esperada

- `node --check lai_gateway/static/app.js`
- Testes de UI do Gateway.
- Testes do dispatcher e do adapter registry.
- `PYTHON=python3 make check`
- `git diff --check`

## Risco principal

O risco é a UI sugerir que qualquer adapter pode ser executado. Por isso o dispatch seguro é nomeado explicitamente como `local_status`, enquanto os demais botões continuam como inspeção da cadeia de governança.
