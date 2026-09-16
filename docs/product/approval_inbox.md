# Approval inbox

`approval-inbox/v1` é a caixa local de aprovações pendentes do LAI.

Ela existe para registrar, de forma sanitizada, propostas que já passaram por `action-proposal/v1` e ainda precisam de decisão humana posterior.

## Contrato

- Entrada canônica: `action-proposal/v1`.
- Saída canônica: registros pendentes em `.lai/approval-inbox.jsonl` dentro de `workspace_root` explícita.
- Cada registro preserva domínio, canal, autonomia, capacidade, alvo, dados tocados, efeito esperado e risco.
- Registros são dados não confiáveis; não concedem autoridade.
- `show` é read-only; `enqueue` escreve apenas o registro sanitizado no arquivo local explícito.

## Limites

- Não aprova.
- Não nega.
- Não cria autorização efetiva.
- Não emite grant.
- Não consome grant.
- Não despacha adapter.
- Não chama Harness.
- Não executa tools.
- Não usa credenciais.
- Não envia mensagem.
- Não publica.
- Não realiza efeito externo.
- Não faz HOME scan.
- Não faz ingestão implícita.

## Segurança

Conteúdo com formato de segredo é rejeitado antes de persistência ou retorno. O inbox é uma fila de revisão, não uma permissão.
