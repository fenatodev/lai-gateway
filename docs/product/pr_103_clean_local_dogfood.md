# PR103 — dogfood local limpo

## Objetivo

Adicionar validação reproduzível de dogfood local para o alpha técnico pós-PR102, sem ampliar capacidade funcional.

## Dimensões LAI

- Domínio: operação local de produto.
- Canal: CLI/script local e documentação.
- Autonomia: diagnóstico governado e efêmero.
- Capacidade: validação de stack local, Workbench, modelo local ausente/presente e documentos restritos.

## Entrega

- `scripts/local-clean-dogfood.sh` executa um loop local limitado.
- `docs/local_clean_dogfood.md` documenta uso e limites.
- O índice canônico aponta para a checklist e esta spec histórica.

## Gates

- Script deve rodar sem instalar dependências ou usar credenciais.
- O alvo padrão deve seguir a versão declarada do pacote, sem fixar release anterior.
- Deve validar `release-check` e `alpha-readiness`.
- Deve exercitar fallback de modelo ausente e fixture local em loopback para modelo presente.
- Deve validar `document-text-local/v1` e `document-workbench/v1` sem PDF/OCR/Office.
- Deve preservar saída sem tokens, chat id, paths privados, browser, n8n, MCP tool execution ou publicação.

## Fora de escopo

Sem mudança funcional de Gateway, sem tag, sem release, sem publicação, sem browser, sem n8n, sem MCP tool execution real, sem voz, sem automação externa, sem credenciais e sem processamento amplo de documentos.
