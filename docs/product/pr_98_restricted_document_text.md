# PR98 — document_text_local restrito

## Escopo

PR98 cria `document-text-local/v1`: extração de texto local apenas para arquivos textuais explícitos em workspace permitido. O objetivo é disponibilizar uma leitura limitada para `.txt`, `.md` e `.json`, sem varredura ampla e sem interpretar conteúdo como comando.

Não cria ingestão completa de documentos, OCR, PDF, DOCX, planilhas, imagens, mídia, embeddings, resumo automático, escrita em arquivos, upload externo, browser, n8n, MCP tool execution ou autorização por conteúdo recuperado.

## Domínio, canal, autonomia e capacidade

- Domínio: texto local restrito.
- Canal: CLI, Gateway API protegida e Workbench local.
- Autonomia: somente inspeção explícita de um caminho relativo dentro do workspace informado.
- Capacidade: `document.extract_text_local` para extensões permitidas, tamanho limitado e saída truncada.

## Mudança funcional

`document-text-local` recebe `workspace_root` e `relative_path`. O caminho resolvido precisa permanecer dentro do workspace, não pode atravessar symlink e precisa apontar para arquivo regular permitido. A extração lê UTF-8 com substituição segura, retorna metadados, digest e prévia limitada.

O Gateway expõe `/v1/gateway/document-text-local`; a CLI ganha `lai-gateway document-text-local`. A UI adiciona painel de documento local restrito, separado de memória e conversa.

## Segurança preservada

- Conteúdo de documento é não confiável e nunca concede autoridade, aprovação, capability ou permissão.
- Sem HOME scan, sem glob, sem busca recursiva, sem rede, sem shell, sem tools, sem servidor, sem download, sem modelo, sem browser, sem n8n, sem MCP tool execution, sem social/career e sem writes.
- Sem PDF, sem OCR, sem Office, sem DOCX, sem planilhas, sem imagens, sem binários e sem transcrição; todos ficam bloqueados.
- Path traversal, path absoluto fora do workspace e symlink são bloqueados antes da leitura.

## Evidência

Testes cobrem caminho permitido, extensão bloqueada, traversal, symlink, arquivo grande, conteúdo não confiável, CLI, API/UI e documentação canônica.

Gate local: `PYTHON=python3 make check`.
