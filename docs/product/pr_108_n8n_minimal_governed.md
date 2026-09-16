# PR108: n8n mínimo governado

## Objetivo

PR108 implementa `n8n-local-plan/v1`: uma superfície local e estreita para inspecionar somente o digest de um plano n8n, sob escopo `n8n-local-plan` e capability `n8n.local_plan_digest`.

## Escopo

- registra `n8n` como adapter de plano local governado;
- adiciona CLI `lai-gateway n8n-local-plan`;
- adiciona API protegida `/v1/gateway/n8n-local-plan`;
- adiciona ações mínimas no Workbench para emitir grant e inspecionar plano;
- usa `authorization-recovery/v1` com grant persistido, expiração, revogação, consumo único e antirreplay;
- aceita somente `workflow_sha256`, nunca JSON bruto de workflow.

## Fora de escopo

- instalar, configurar ou iniciar n8n;
- conectar credenciais;
- ler workflows reais de uma instância n8n;
- criar, alterar, ativar ou executar workflow;
- chamar webhook;
- expor webhook público;
- sem webhook real;
- usar rede, shell, browser, MCP, formulários ou serviços externos.

## Decisão arquitetural

n8n continua motor de automação, não core do LAI. O Gateway só adiciona um gate local comprovável para plano/digest. Plano, memória, arquivo ou modelo não concedem autorização. Execução real de workflow permanece bloqueada até existir adapter específico com política, evidência de contenção e aprovação humana explícita por efeito.

## Validação esperada

- `tests/test_n8n_local_plan.py` cobre plano, issue, inspect, replay, mudança de digest, identidade forjada e segredo;
- `tests/test_adapters.py` diferencia plano local governado de execução real n8n;
- `tests/test_ui.py` cobre endpoint e UI;
- `tests/test_product_docs.py` mantém a documentação canônica sem overclaiming;
- `make check` deve passar sem instalar, iniciar ou chamar n8n.
