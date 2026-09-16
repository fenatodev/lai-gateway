# PR96 — local model chat, health and fallback

## Escopo

PR96 torna a primeira conversa local explícita e testável. A conversa comum entra pelo Gateway, tenta somente o runtime local configurado e retorna indisponibilidade clara quando o modelo não está pronto.

Não cria fallback em nuvem, não cria run no Harness, sem iniciar runs, sem executar tools, não instala runtime, não baixa modelo, não inicia servidor e não amplia autorização.

## Domínio, canal, autonomia e capacidade

- domínio: conversa local com modelo.
- canal: Gateway loopback/API local, CLI e Workbench.
- autonomia: resposta local direta quando o runtime está pronto; fallback informativo quando não está.
- capacidade: uma rodada de conversa local bounded, sem tools e sem efeitos externos.

## Mudança funcional

`model-chat` passa a declarar `local-model-first`, health do runtime e fallback explícito. Quando o runtime local está ausente, bloqueado ou inalcançável, a resposta informa o motivo sem tentar nuvem, Harness, tools ou elevação de permissão.

O Gateway preserva `/v1/gateway/chat` como conversa direta. O Workbench expõe um campo de primeira conversa local separado dos runs assistidos. A CLI ganha `model-chat` para teste manual controlado.

## Segurança preservada

- prompt do usuário não é ecoado em JSON, renderização ou registros;
- URL pública ou credencial em URL é bloqueada antes de rede;
- endpoint permitido continua `http://` local/privado com porta explícita;
- sem cloud fallback, sem harness fallback e sem permission elevation;
- sem execução de tools, browser, n8n, MCP tool execution, social/career ou documentos.

## Evidência

Testes novos e atualizados cobrem conversa local, fallback explícito, endpoint HTTP, CLI, UI, ausência de echo de prompt e limites documentais.

Gate local: `PYTHON=python3 make check`.
