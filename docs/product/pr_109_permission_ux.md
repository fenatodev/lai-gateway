# PR109: UX de permissões

## Objetivo

PR109 implementa `permission-ux/v1`: uma visão read-only da cadeia de permissão para deixar explícita a diferença entre intenção, identidade, decisão, registro, aprovação/captura, autorização efetiva, grant single-use e execução.

## Escopo

- adiciona CLI `lai-gateway permission-ux`;
- adiciona API protegida `/v1/gateway/permission-ux`;
- adiciona painel no Workbench para visualizar o fluxo de permissões;
- reutiliza os payloads existentes de decisão, autorização, validação, autorização efetiva e dispatcher;
- mostra estágio, status, autoridade e resumo sem expor tokens ou parâmetros sensíveis.

## Fora de escopo

- emitir grant;
- consumir grant;
- revogar grant;
- ler ou escrever store de grants;
- despachar adapter;
- executar tool;
- ampliar capability;
- aceitar texto de aprovação como autoridade;
- habilitar browser autenticado, n8n real, MCP amplo, voz, social/carreira ou publicação.

## Decisão arquitetural

UX de permissão não é autorização. O painel apenas explica a cadeia. A autorização efetiva continua restrita aos escopos já implementados; grants continuam no `authorization-recovery/v1`; execução continua nos endpoints específicos com testes negativos próprios.

## Validação esperada

- `tests/test_permission_ux.py` cobre fluxo completo, decisão bloqueada, CLI/render secret-free e ausência de efeitos;
- `tests/test_ui.py` cobre endpoint e marcações do Workbench;
- `tests/test_product_docs.py` mantém a documentação canônica sem overclaiming;
- `make check` deve passar sem emitir grant, consumir grant ou despachar adapter.
