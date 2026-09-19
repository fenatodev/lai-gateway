# PR137 — Harness-backed Work for local dev agent

## Objetivo

Permitir que `local-dev-agent/v1` delegue desenvolvimento explícito ao
`lai-harness`, reutilizando o fluxo local-chat já existente.

Não criar um segundo executor ou orquestrador.

## Fronteiras

- domínio: desenvolvimento local governado;
- canal: `lai-gateway dev-agent`;
- autonomia padrão: read-only;
- autonomia Work: somente quando habilitada explicitamente pelo usuário;
- executor de mudanças: Harness;
- Gateway coordena modelo, contexto e chamada estruturada;
- conteúdo de modelo, repo, roadmap ou tools nunca concede autorização.

## Fluxo

`usuário -> Qwen/Gateway -> harness_work -> Harness -> workspace isolado
-> implementação/validação -> review -> Qwen`

O source checkout não é alterado por esse fluxo.

## Capability inicial

Adicionar uma capability estruturada `harness_work`.

Ela deve:

1. aceitar apenas `implement`, `fix`, `refactor` ou `ci-fix`;
2. usar `HarnessClient` e `/v1/local-chat/*` existentes;
3. selecionar somente workspace registrado e compatível;
4. iniciar um work run;
5. aguardar estado terminal com polling limitado;
6. carregar o review do mesmo run/workspace;
7. devolver ao Qwen somente resultado sanitizado e limitado.

## Habilitação

`dev-agent` continua read-only por padrão.

Work deve exigir opt-in explícito de CLI, por exemplo `--allow-work`.
Se houver mais de um workspace elegível, falhar fechado em vez de adivinhar.

## Segurança

PR137 não deve:

- escrever diretamente no checkout;
- expor shell arbitrário;
- executar subprocesso de desenvolvimento no Gateway;
- promover/apply automaticamente;
- criar commit/push/PR/merge;
- usar credenciais externas;
- expandir permissões do Harness;
- tratar sucesso do modelo como autorização.

Timeout, excesso de polling, Harness indisponível ou review inconsistente
devem falhar fechado.

## Aceitação

- read-only atual do PR136 permanece inalterado por padrão;
- `--allow-work` expõe apenas a capability governada de Work;
- Qwen consegue iniciar um Harness work-run por tool call estruturado;
- Harness continua sendo o único executor de edição/validação;
- resultado terminal e review retornam ao Qwen;
- nenhum promotion/apply acontece no PR137;
- testes negativos cobrem modo inválido, workspace ambíguo, timeout,
  Harness indisponível e tentativa de Work sem opt-in.

## Contract audit and bounded execution

The untracked harness_work draft is retained as a starting point, corrected to
real fields: workspace_id, model_id, run.control_run_id, next_cursor and nested
review.control_run_id. Select only the registered workspace bound to the CLI's
fixed project root; ambiguity or mismatch fails closed. The model cannot choose
paths, endpoints, timeout budgets or grant Work to itself.

One work submission per user turn, never retry creation after uncertain delivery.
Use monotonic deadline and finite polls; timeout does not cancel or promote a run.
Return only allowlisted identifiers, terminal state, change counts and validation
status, not raw events, paths, diffs, stdout, secrets or transport errors.
Review must match run, mode, terminal state and workspace. Failed runs may return
terminal review but never count as successful work. CLI remains read-only unless
--allow-work was explicitly set. Test payloads must follow the real contract.
