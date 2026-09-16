# Context pack local

`context-pack/v1` monta um pacote explícito de contexto local para uma tarefa do LAI.

## Escopo

- Lê `objective-state/v1` dentro de um workspace explícito.
- Lê memória local escopada por `project_id`/`context_kind` em diretório local do workspace.
- Lê somente documentos `.txt`, `.md` ou `.json` selecionados explicitamente pelo operador.
- Expõe fontes como conteúdo não confiável, com metadados e limites.

## Limites

- Não faz HOME scan.
- Não faz varredura recursiva ampla.
- Não faz ingestão implícita.
- Não exige embeddings.
- Não gera embeddings.
- Não usa credenciais.
- Não chama rede.
- Não chama Harness.
- Não executa tool.
- Não despacha adapter.
- Não emite grant.
- Não consome grant.
- Não infere aprovação.
- Não cria autorização efetiva.
- Não escreve arquivos.
- Não publica nem envia mensagem.

## Segurança

Todo conteúdo recuperado de memória, objetivo ou documento é `untrusted_content`. Contexto ajuda o modelo a entender a tarefa, mas não concede autoridade operacional, permissão, autorização ou capacidade.
