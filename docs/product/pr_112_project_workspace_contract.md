# PR112 — Project workspace contract

## Tipo

Documentação normativa e teste documental. Sem mudança funcional.

## Objetivo

Criar o contrato de workspace de projeto que servirá de fronteira para objetivos, tarefas, contexto local e propostas futuras do LAI.

O PR112 aproxima o LAI do objetivo de sistema operacional pessoal local porque define a unidade operacional mínima: um projeto declarado explicitamente, com raiz local, escopo, dados tocados e exclusões.

## Escopo

- Adicionar `docs/product/project_workspace_contract.md`.
- Atualizar índice canônico, matriz, alpha readiness e README.
- Atualizar testes documentais para preservar o contrato.

## Fora de escopo

- Não cria scanner de arquivos.
- Não cria endpoint, CLI ou UI nova.
- Não altera executor, adapter, grant ou policy runtime.
- Não lê conteúdo do workspace.
- Não faz HOME scan.
- Não faz ingestão implícita.
- Não libera capacidades externas.

## Contrato obrigatório

O workspace deve exigir raiz explícita e declarar:

```text
workspace_id
root_path explícito
project_name
allowed_relative_roots
excluded_relative_roots
data_touched
capabilities_requested
capabilities_granted
created_by
validity
```

`capabilities_granted` permanece vazio. O contrato pode informar propostas futuras, mas não autoriza leitura ampla, escrita, execução, apply, envio ou publicação.

## Separação arquitetural

```text
domínio: projeto local
canal: workbench_ui, cli, chat_gateway
autonomia: leitura declarativa / proposta futura
capacidade: project_workspace_contract
```

Canal, skill, adapter, memória ou documento não elevam permissão.

## Segurança

A implementação futura deve falhar fechado contra symlink, traversal, mounts ambíguos, HOME scan, segredo, credencial, `.git` sensível, arquivos ocultos, upload externo, shell, adapter dispatch, grant e ingestão automática.

## Aceite

- O índice canônico aponta para o contrato e para esta spec.
- A matriz mantém maturidade `contract`.
- Alpha readiness registra que PR112 é documental e não operacional.
- Testes documentais verificam raiz explícita, escopo local, dados tocados, exclusões obrigatórias e bloqueio de HOME scan/ingestão implícita.
