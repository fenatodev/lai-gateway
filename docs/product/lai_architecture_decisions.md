# lai architecture decisions

## decisão 1: separar domínio, canal, autonomia e capacidade

O LAI deve manter comandos simples para o usuário, mas internamente não deve tratar tudo como modo.

```text
domínio: assunto da tarefa
canal: por onde o usuário interage
autonomia: quanto o agente pode fazer
capacidade: quais ferramentas podem ser usadas
```

Domínio, canal e skill nunca elevam permissão automaticamente.

## decisão 2: permissões por capacidades

A escala de risco classifica impacto. A autorização real é por capacidade concreta.

Uma autorização precisa declarar:

```text
ação
recurso
alvo
escopo
projeto
validade
consequência
```

Exemplo:

```text
permitido: escrever em sandbox no projeto lai-gateway durante esta tarefa
negado: aplicar no main, apagar arquivos fora da sandbox, usar sudo, publicar, enviar mensagens
```

## decisão 3: permission_engine como passagem obrigatória

Nenhum executor deve produzir efeito sensível sem passar pelo `permission_engine`.

Isso vale para:

```text
harness
terminal
browser
n8n
mcp
webhooks
scripts
plugins
```

Adapters executam contratos. Eles não decidem política.

## decisão 4: ciclo único de ação

Toda ação sensível deve seguir:

```text
pedido -> proposta -> autorização -> execução -> revisão -> conclusão
```

Escrita em sandbox não autoriza apply. Aprovar um workflow não autoriza cada publicação futura.

## decisão 5: identidade explícita

O LAI deve separar:

```text
usuário: pessoa responsável pela decisão
cliente: interface ou app que enviou o pedido
agente: processo lógico que propõe ou executa a ação
serviço: sistema externo ou interno acionado
```

Aprovações devem ser vinculadas ao responsável correto. Cliente, canal ou agente não substituem autorização do usuário.

## decisão 6: estado persistente local

O LAI precisa de fonte de verdade local para:

```text
memória por projeto
aprovações
execuções
runs
artefatos
histórico de ações
estado de automações
preferências do usuário
```

Reinícios não podem perder aprovações pendentes nem duplicar efeitos externos.

## decisão 7: core pequeno e adapters substituíveis

Core:

```text
chat_gateway
mode_router
permission_engine
capability_registry
approval_manager
execution_state
memory_context
skills_registry
tool_layer
policy_store
audit_log
```

Adapters:

```text
models
harness
sandbox
mcp
cli
browser
automations
stt
tts
wake_word
documents
media
storage
```

Plugins:

```text
model_lab
scout
social
career
cybersecurity
frontend
architect
```

## decisão 8: n8n, browser e voz não são core

n8n é motor de automação. Browser é adapter de navegação. Voz é canal/interface. Nenhum desses componentes deve manter política paralela.

## decisão 9: conteúdo externo é não confiável

Documentos, páginas web, código, memória, respostas de ferramentas e saídas de modelos podem conter prompt injection.

Esse conteúdo pode informar a proposta, mas não pode conceder autorização nem alterar policy.
