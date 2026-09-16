# PR 91 — public quickstart and install diagnostics

## Objetivo

Entregar um quickstart público mínimo para operador técnico instalar e validar o
LAI Gateway localmente a partir do código-fonte, sem declarar o alpha como
produto completo.

Este PR implementa o gate PR91 do roadmap canônico pós-PR90.

## Escopo

Incluído:

- guia público `docs/quickstart.md`;
- link do README para o quickstart;
- link do índice canônico de produto para o quickstart;
- critérios documentais que protegem o escopo do quickstart;
- testes documentais para garantir pré-requisitos, diagnósticos e limites.

Fora de escopo:

- instalador one-click;
- publicação PyPI;
- release GitHub;
- mudança de versionamento;
- alteração funcional do Gateway;
- alteração no Harness;
- browser, n8n, voz, MCP real, social/career ou documentos reais.

## Invariantes

- Quickstart é documentação operacional, não concessão de capacidade.
- Instalação pública atual é source-first e local-first.
- O fluxo não imprime segredos nem orienta copiar tokens para o navegador.
- Harness e Gateway continuam separados.
- Loopback é o caminho padrão.
- `local_status` continua sendo adapter seguro restrito, não prova de autorização geral.
- Capacidades externas continuam bloqueadas até os gates posteriores.

## Gate de saída

- O usuário técnico consegue identificar pré-requisitos.
- O usuário técnico consegue instalar wrappers locais.
- O usuário técnico consegue rodar diagnóstico sem expor segredo.
- O usuário técnico consegue iniciar Gateway UI em loopback.
- Falhas comuns apontam para próximo diagnóstico correto.
- O README não promete instalação universal nem funcionalidades externas prontas.

## Validação esperada

- `python3 -m unittest tests.test_product_docs -v`
- `PYTHON=python3 make check`
- `git diff --check`
