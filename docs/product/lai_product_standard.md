# lai product standard

## status

Documento normativo do produto LAI para orientar os PRs imediatos.

## objetivo

O LAI deve ser um sistema operacional pessoal de IA local, open-source-first e modular.

Ele deve servir como interface única para conversa, desenvolvimento, automação, carreira, conteúdo, segurança, documentos, mídia, voz e ferramentas externas.

O LAI não deve recriar motores maduros do zero. Ele deve orquestrar ferramentas especializadas e manter controle de contexto, memória, permissões, aprovações, skills, execução e experiência do usuário.

## não objetivos

O LAI não deve:

- depender de SaaS pago como requisito central;
- virar um monólito de automação;
- dar autonomia total sem aprovação humana;
- tratar browser, n8n, voz ou social como core;
- permitir que canal, skill, adapter ou domínio elevem permissão;
- considerar memória recuperada como autorização.

## princípio central

O LAI deve separar quatro dimensões internas:

```text
domínio: assunto da tarefa
canal: interface usada pelo usuário
autonomia: quanto o agente pode fazer
capacidade: ferramenta ou recurso autorizado
```

Trocar de domínio, canal ou skill nunca deve elevar permissões automaticamente.

## domínios

```text
dev
arquitetura
frontend
social
carreira
cybersecurity
documentos
mídia
automação
pesquisa
rotina_pessoal
```

## canais

```text
vscode
workbench_ui
web_ui
telegram
voice_layer
cli
```

Canais apresentam entrada, saída e aprovação. Eles não mantêm core paralelo e não concedem permissões.

## autonomias

```text
conversa
leitura
proposta
execução_em_sandbox
execução_local_controlada
apply
publicação_ou_envio_externo
```

Autonomia define até onde o agente pode ir em uma tarefa. Ela não define sozinha quais ferramentas podem ser usadas.

## capacidades

```text
filesystem_read
filesystem_write_sandbox
filesystem_apply
shell_readonly
shell_exec
sudo
network
browser_public
browser_authenticated
credentials_use
webhook_trigger
n8n_workflow
publish_content
send_message
submit_form
delete_data
external_private_data_send
```

Capacidades solicitadas por skills, adapters ou prompts são entrada não confiável. Capacidades concedidas são resultado da policy central.

## core

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

O core decide política, contexto, roteamento, estado, aprovação e auditoria.

## adapters

```text
models
harness
sandbox
mcp
cli
browser
automations
storage
stt
tts
wake_word
documents
media
```

Adapters executam contratos definidos pelo core. Eles não concedem permissão e não decidem política.

## interfaces

```text
vscode
workbench_ui
web_ui
telegram
voice_layer
```

Interfaces apresentam conversa, propostas, resultados e aprovações. Nenhuma interface deve manter autorização própria.

## plugins e skills

Skills são procedimentos pequenos, composáveis e versionados. Plugins acrescentam capacidades opcionais.

Skills iniciais:

```text
/grill
/architect
/spec
/frontend
/dev
/security
/scout
```

Próxima leva:

```text
/browser
/automation
/social
/career
/voice
/document
/media
/model-lab
```

## roteamento esperado

```text
@lai oi
-> conversa direta

@lai explique docker
-> conversa direta

@lai /health
-> status do gateway/modelo

@lai /workbench
-> abre workbench

@lai /plan <pedido>
-> dev assistido read-only

@lai /work <pedido>
-> agente dev controlado

@lai /browser <pedido>
-> browser agent com aprovação
```

Mensagens comuns não devem iniciar harness, shell, browser ou automações.

## lifecycle único de ação

Toda ação sensível deve seguir:

```text
pedido
-> proposta
-> autorização
-> execução
-> revisão
-> conclusão
```

Escrita em sandbox não autoriza apply. Aprovar um workflow não autoriza publicações futuras.

## permissões

A escala de risco classifica impacto, mas não concede autorização:

```text
risco_0: conversa e raciocínio sem ferramenta
risco_1: leitura local segura
risco_2: escrita em sandbox
risco_3: execução local sem sudo
risco_4: instalação, sudo, rede sensível, credenciais ou browser logado
risco_5: publicação, mensagens, candidaturas, formulários, compras ou ações irreversíveis
```

A autorização real deve conter:

```text
ação
recurso
alvo
projeto
escopo
validade
consequência
```

Riscos 4 e 5 exigem aprovação humana obrigatória. Risco 3 pode exigir aprovação conforme alvo e consequência.

## ações com aprovação humana obrigatória

```text
apply da sandbox para projeto real
instalar ou remover software
usar sudo
alterar configuração de sistema, rede ou permissões
acessar ou usar credenciais
usar browser autenticado
publicar conteúdo
enviar mensagens
submeter candidatura ou formulário
confirmar compra
excluir dados fora da sandbox
enviar dados privados para serviço externo
ativar ou alterar automação com efeito sensível
ampliar permissão de ferramenta, plugin ou workflow
```

## persistência local

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

## ferramentas candidatas

```text
llm_runtime: llama.cpp, ollama
modelos: ministral, qwen_coder, deepseek, kimi, glm, mistral
mcp: model context protocol
browser: browser-harness, browser-use, playwright
workflow: n8n self-hosted, node-red, scripts python
coding_agent: aider, openhands, continue, cline
voz: whisper.cpp, piper, openwakeword, home assistant assist
media: ffmpeg, imagemagick, comfyui ou stable diffusion local
```

A lista é candidata, não decisão final. Cada motor deve ser avaliado por licença, hardware, segurança, substituibilidade e integração com permissões.
