# LAI project workspace contract

Contrato normativo para declarar um workspace de projeto antes de estado, objetivos, contexto, propostas ou execução local controlada.

## Status

PR112 é documentação de contrato. Ele não implementa scanner, executor, adapter, grant, policy runtime, UI nova ou persistência operacional.

## Objetivo

Definir como o LAI deve reconhecer um projeto local sem transformar arquivos do usuário em autorização, memória confiável ou capacidade operacional implícita.

O workspace é uma fronteira explícita de contexto. Ele informa o que pode ser considerado na conversa e em propostas futuras; não autoriza leitura ampla, escrita, execução, apply, publicação ou envio externo.

## Quatro eixos

```text
domínio: projeto local do usuário
canal: workbench_ui, cli ou chat_gateway
autonomia: leitura declarativa e proposta futura
capacidade: project_workspace_contract
```

Nenhum canal, skill ou adapter pode ampliar esse contrato. Conteúdo encontrado no workspace continua dado não confiável.

## Campos mínimos

Um workspace válido deve declarar:

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

`capabilities_granted` deve permanecer vazio neste contrato. Qualquer capacidade posterior passa pela policy central e por autorização própria.

## Raiz explícita

A raiz do workspace deve ser escolhida pelo operador ou por configuração local explícita. O LAI não deve inferir `HOME`, varrer diretórios pessoais, buscar repositórios automaticamente ou tratar diretório atual como autorização ampla.

A raiz deve ser local, canônica e verificável. Symlinks, traversal, mounts ambíguos e caminhos fora do escopo declarado devem falhar fechado em implementações futuras.

## Dados tocados

O contrato permite apenas metadados declarativos sobre a fronteira do projeto:

```text
nome do projeto
raiz declarada
subpastas permitidas
subpastas excluídas
tipos de dados esperados
estado do contrato
```

Leitura de conteúdo, indexação, embeddings, OCR, PDF, Office, mídia, segredos, `.git` sensível e arquivos ocultos ficam fora do contrato até capability própria.

## Exclusões obrigatórias

Implementações futuras devem bloquear:

```text
HOME scan
varredura recursiva ampla
ingestão implícita
autodetecção com efeito operacional
leitura de segredos
uso de credenciais
upload externo
execução de shell
execução de adapter
emissão ou consumo de grant
```

## Relação com objetivo e contexto

PR113 pode usar este contrato como fronteira para `objective-state/v1`. PR117 pode usar este contrato para context pack explícito. Nenhum deles deve transformar workspace declarado em confiança implícita ou autorização.

## Gate de saída PR112

- Contrato versionado e linkado no índice canônico.
- Matriz declara maturidade `contract` e disponibilidade apenas documental.
- Alpha readiness registra ausência de mudança funcional.
- Testes documentais garantem raiz explícita, escopo local, dados tocados, exclusões e ausência de HOME scan ou ingestão implícita.

## Fora de escopo

- Criar ou validar workspace em runtime.
- Persistir estado de objetivo/tarefa.
- Ler conteúdo de arquivos.
- Criar grants.
- Despachar adapters.
- Executar shell.
- Sincronizar com serviços externos.
- Habilitar browser autenticado, n8n real, MCP amplo, voz, publicação ou mensagens.
