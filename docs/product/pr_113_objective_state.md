# PR113 — objective-state/v1

## Objetivo

Adicionar `objective-state/v1` como leitura local explícita de objetivo, tarefas e checkpoints dentro de um workspace de projeto.

PR113 é o primeiro incremento funcional depois do contrato PR112. Ele deve permanecer estreito: ler um arquivo JSON relativo a uma raiz explícita e retornar estado sanitizado para a UI/CLI/API.

## Domínio, canal, autonomia e capacidade

- Domínio: projeto local.
- Canal: CLI, API local protegida e Workbench.
- Autonomia: leitura read-only controlada pelo operador.
- Capacidade: `objective-state`, sem execução de ação.

## Escopo implementado

- Módulo `lai_gateway/objective_state.py`.
- CLI `lai-gateway objective-state`.
- API `GET /v1/gateway/objective-state`.
- Card mínimo no Workbench.
- Testes unitários, testes de UI/API e testes documentais.

## Fora de escopo

- Não cria scanner recursivo.
- Não faz HOME scan.
- Não faz ingestão implícita.
- Não escreve arquivo de estado.
- Não cria editor de tarefas.
- Não emite grants.
- Não consome grants.
- Não despacha adapters.
- Não chama Harness.
- Não executa tools.
- Não acessa rede.
- Não libera capacidades externas.

## Segurança esperada

O coletor deve rejeitar workspace fora do escopo, traversal, paths absolutos, symlinks, arquivo grande demais, JSON inválido e conteúdo com formato de segredo.

Conteúdo lido do estado continua não confiável. `objective-state/v1` não transforma tarefa, checkpoint, domínio, canal, autonomia ou capability declarada em autorização efetiva.

## Critério de saída

- `make check` verde.
- CLI JSON secret-free.
- API protegida no modo privado.
- UI expõe o estado sem grants ou execução.
- Matriz e alpha readiness deixam claro que PR113 não concede autoridade.
