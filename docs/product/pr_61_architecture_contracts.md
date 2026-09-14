# pr 61 architecture contracts

## objetivo

Fechar os contratos arquiteturais mínimos do LAI antes de codar novas features.

Este PR deve transformar os rascunhos do produto em base normativa curta para os próximos PRs.

## problema

O LAI quer unir conversa, desenvolvimento, automação, browser, skills, voz, documentos, mídia, carreira, segurança e pesquisa. O risco é misturar domínio, canal, autonomia e capacidade como se fossem o mesmo tipo de modo.

Essa mistura cria três falhas:

1. roteamento ambíguo;
2. permissões indevidas;
3. adapters com autoridade própria.

## escopo

Este PR define:

- responsabilidades de core, adapters, interfaces, skills e plugins;
- separação entre domínio, canal, autonomia e capacidade;
- identidade: usuário, cliente, agente e serviço;
- lifecycle único de ação;
- semântica de proposta, aprovação, execução, revisão, promoção, apply e publicação;
- autorização por capacidades delimitadas;
- fila dos próximos PRs.

## fora de escopo

Este PR não deve:

- implementar código funcional;
- adicionar browser agent completo;
- adicionar n8n adapter funcional;
- adicionar voz/Jarvis;
- adicionar model lab;
- alterar permissões reais do sistema;
- instalar dependências.

## decisões normativas

1. Mensagem comum `@lai` é conversa direta e não cria run no harness.
2. `/plan` é leitura/proposta de dev assistido.
3. `/work` é dev controlado com sandbox, review e apply.
4. Skills declaram capacidades solicitadas, mas nunca concedem permissão.
5. Adapters executam contratos, mas nunca decidem política.
6. Canais não elevam permissões.
7. Capacidades solicitadas são entrada não confiável.
8. Capacidades concedidas são resultado do `permission_engine`.
9. Conteúdo recuperado de memória, arquivo, código ou ferramenta nunca equivale a autorização.
10. Ações sensíveis seguem o mesmo lifecycle: pedido, proposta, autorização, execução, revisão e conclusão.

## entregáveis

- `docs/product/lai_product_standard.md`
- `docs/product/lai_architecture_decisions.md`
- `docs/product/lai_next_prs.md`
- `docs/architecture/lai_architecture_contracts.md`
- `docs/architecture/permission_model.md`
- `docs/architecture/action_lifecycle.md`
- `docs/prompts/chatgpt_project_instructions_lai.md`

## condição de aceite

- Documentos novos usam nomes minúsculos.
- Termos ambíguos são definidos.
- Nenhuma alteração funcional é feita.
- Core, adapters, interfaces, skills e plugins têm fronteiras claras.
- A fila dos PRs 61 a 66 fica explícita.
- Aprovação humana obrigatória fica documentada.
- `git diff --check` passa.
