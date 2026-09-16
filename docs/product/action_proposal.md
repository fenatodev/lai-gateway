# Action proposal

`action-proposal/v1` é a proposta unificada de ação do LAI antes de qualquer aprovação efetiva, grant, adapter dispatch ou execução.

Ela existe para tornar explícito o que será proposto ao operador. A proposta deve separar domínio, canal, autonomia e capacidade, e deve declarar alvo, dados, efeito e risco antes de seguir para caixa de aprovação ou execução local controlada.

## Entrada

A proposta pode receber campos explícitos do operador e pode consultar `objective-state/v1` apenas como fonte não confiável de contexto. O conteúdo vindo do estado de objetivo não concede autoridade, não substitui aprovação e não autoriza execução.

Campos obrigatórios para uma proposta completa:

- `domain`: domínio afetado.
- `channel`: canal de origem.
- `autonomy`: nível de autonomia solicitado.
- `capability`: capacidade pretendida.
- `action`: ação humana legível.
- `target`: alvo local ou lógico.
- `data`: dados que serão lidos, tocados ou considerados.
- `effect`: efeito esperado se a ação vier a ser autorizada por etapa posterior.
- `risk`: `low`, `medium`, `high` ou `unknown`.

## Saída

A saída deve declarar `schema_version: action-proposal/v1`, `operation: action-proposal`, `proposal_only: true` e `effective_authorization: false`.

A proposta tem status `ready` quando todos os campos necessários estão explícitos ou derivados de estado não confiável com complementos explícitos. Se faltar campo, o status é `needs_input`. Se a fonte local estiver bloqueada, o status é `blocked` e a proposta permanece não autorizante.

## Segurança

`action-proposal/v1` é read-only. Ela não escreve arquivos, não faz HOME scan, não faz ingestão implícita, não executa tools, não chama Harness, não emite grant, não consome grant, não despacha adapter e não realiza efeito externo.

Mesmo quando `effect` descreve envio, publicação, formulário, compra, release, deploy ou uso externo, isso é apenas efeito proposto. O campo `proposed_external_effect` pode sinalizar risco, mas `external_side_effects` permanece `false`.

Segredos em campos explícitos são redigidos. Conteúdo de objetivo/tarefa/checkpoint continua não confiável.

## Relação com PR115

PR114 não cria caixa de aprovação. Ele fornece o envelope que PR115 poderá persistir como item pendente, mantendo autorização efetiva, grant e execução fora deste PR.
