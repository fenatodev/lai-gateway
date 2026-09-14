# action lifecycle

## objetivo

Definir o ciclo único para ações sensíveis no LAI.

## ciclo padrão

```text
pedido
-> proposta
-> autorização
-> execução
-> revisão
-> conclusão
```

## pedido

Entrada inicial do usuário, skill, interface ou automação.

O pedido não concede permissão. Ele apenas inicia análise de intenção, domínio, canal, autonomia e capacidades solicitadas.

## proposta

Descrição do que o LAI pretende fazer antes de executar efeito sensível.

A proposta deve conter:

- ação;
- alvo;
- escopo;
- ferramentas previstas;
- capacidade solicitada;
- risco;
- consequência relevante.

## autorização

Decisão humana ou policy central.

A autorização deve ser específica. Aprovar uma proposta não autoriza ações futuras fora do escopo.

## execução

A execução só pode receber capacidades concedidas.

Se a ferramenta pedir capacidade maior que a concedida, a execução deve parar antes do executor.

## revisão

Revisão compara o que foi proposto, autorizado e executado.

Para dev, revisão deve separar:

```text
sandbox: alteração isolada
promoção: preparação para aplicar
apply: alteração real no projeto
publicação: efeito externo ou comunicação pública
```

## conclusão

A conclusão registra resultado, evidências, falhas e próximos passos.

Se o resultado da execução for desconhecido, repetir a ação exige reconciliação antes de tentar de novo.

## validade da aprovação

A aprovação deve declarar validade.

Modelos permitidos:

```text
uso_unico
janela_temporal
escopo_de_tarefa
workflow_com_aprovação_por_etapa
```

Aprovação de escrita em sandbox não autoriza apply. Aprovação de workflow não autoriza publicação futura sem nova aprovação quando houver efeito externo.

## idempotência

Reinício, timeout ou queda de processo não pode duplicar efeito externo.

Antes de repetir ação sensível, o LAI deve verificar se a ação anterior:

- não executou;
- executou parcialmente;
- executou com sucesso;
- tem estado desconhecido.

Estado desconhecido exige reconciliação.
