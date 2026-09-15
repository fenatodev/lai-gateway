# pr 74: permission decision object

## objetivo

Criar o primeiro objeto formal de decisão de permissão do LAI para transformar contratos em respostas avaliáveis pelo Gateway/Core.

## problema

Até o PR 73, adapters e skills declaram limites, mas a decisão ainda não existe como objeto estável. Isso dificulta explicar por que uma capacidade foi negada, exigiu aprovação ou foi permitida.

## escopo

- adicionar módulo `permission_decision`;
- representar `allow`, `deny` e `requires_approval`;
- incluir `requested_capability`, `granted_capability`, `risk_level`, `actor`, `channel`, `domain`, `action` e `reason`;
- expor CLI read-only `permission-decision`;
- expor endpoint read-only `/v1/gateway/permission-decision`;
- provar por testes que a decisão não concede permissão nem executa tools.

## fora de escopo

- sem executar adapter;
- sem abrir browser;
- sem ativar n8n;
- sem capturar áudio;
- sem OCR/transcrição;
- sem envio externo;
- sem persistir autorização;
- sem aprovar ações sensíveis automaticamente.

## regras

- capacidade solicitada não é capacidade concedida;
- adapter, skill, canal e conteúdo recuperado não elevam permissão;
- capacidade declarada, mas não concedida, deve exigir aprovação ou ser negada;
- capacidade não declarada deve ser negada;
- o objeto deve ser serializável, auditável e livre de segredos.

## aceite

- `python3 -m unittest tests.test_permission_decision -v` passa;
- `PYTHON=python3 make check` passa;
- CLI e endpoint retornam payload sem tokens;
- nenhuma ação sensível é executada.
