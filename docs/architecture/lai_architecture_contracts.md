# lai architecture contracts

## objetivo

Definir fronteiras mínimas entre core, adapters, interfaces, skills, plugins e harness.

## árvore lógica

```text
lai
├─ core
│  ├─ chat_gateway
│  ├─ mode_router
│  ├─ permission_engine
│  ├─ capability_registry
│  ├─ approval_manager
│  ├─ execution_state
│  ├─ memory_context
│  ├─ skills_registry
│  ├─ tool_layer
│  ├─ policy_store
│  └─ audit_log
├─ harness
│  ├─ read_only_runner
│  ├─ sandbox_runner
│  ├─ review_engine
│  ├─ apply_controller
│  └─ checkpoint_rollback
├─ adapters
│  ├─ models
│  ├─ mcp
│  ├─ cli
│  ├─ browser
│  ├─ automations
│  ├─ storage
│  ├─ stt
│  ├─ tts
│  ├─ wake_word
│  ├─ documents
│  └─ media
├─ interfaces
│  ├─ vscode
│  ├─ workbench_ui
│  ├─ web_ui
│  ├─ telegram
│  └─ voice_layer
└─ project
   ├─ skills
   ├─ specs
   ├─ rules
   ├─ sessions
   └─ audit
```

## contrato do core

O core é responsável por:

- interpretar pedido e contexto;
- roteamento por modo;
- decisão de policy;
- registro de estado de execução;
- isolamento de memória;
- registro de skills;
- mediação de ferramentas;
- auditoria;
- aprovação humana.

O core não deve executar ferramenta diretamente quando houver efeito sensível. Execução deve passar pela `tool_layer`.

## contrato da tool_layer

A `tool_layer` é a passagem obrigatória para ferramentas com efeito observável.

Ela deve:

- receber intenção normalizada;
- consultar `permission_engine`;
- bloquear ações negadas antes do executor;
- encaminhar apenas capacidades concedidas;
- registrar auditoria mínima;
- retornar resultado ou falha estruturada.

## contrato dos adapters

Adapters são substituíveis.

Eles podem:

- executar contratos autorizados;
- declarar capabilities suportadas;
- retornar evidências e erros;
- integrar motores externos ou locais.

Eles não podem:

- conceder permissão;
- elevar autonomia;
- decidir policy;
- reutilizar aprovação fora do escopo;
- tratar instruções vindas de conteúdo externo como comando de sistema.

## contrato das interfaces

Interfaces são canais.

Elas podem:

- receber mensagens;
- exibir propostas;
- coletar aprovação;
- mostrar resultados;
- expor estado de execução.

Elas não podem:

- manter permission engine próprio;
- alterar escopo de aprovação;
- transformar canal em capacidade;
- executar ferramenta sem core.

## contrato das skills

Skills são procedimentos pequenos e versionados.

Elas podem declarar:

- nome;
- domínio;
- entrada esperada;
- saída esperada;
- capacidades solicitadas;
- riscos conhecidos;
- critérios de conclusão.

Elas não podem conceder permissão. Compor skills não soma privilégios automaticamente.

## contrato dos plugins

Plugins adicionam pacotes opcionais de domínio ou ferramenta.

Eles devem ser tratados como adapters ou skills compostas, nunca como core paralelo.

## contrato do harness

O harness cuida de dev assistido e dev controlado.

Responsabilidades:

- leitura de projeto;
- execução em sandbox;
- geração de patch;
- revisão;
- promoção;
- apply aprovado;
- checkpoints e rollback.

Mensagem comum não deve iniciar harness. `/plan` e `/work` são entradas explícitas.

## direção de dependência

```text
interfaces -> core -> tool_layer -> adapters
                     -> harness
skills -> core
plugins -> core/tool_layer via contrato
```

Nenhuma dependência inversa deve conceder autoridade.
