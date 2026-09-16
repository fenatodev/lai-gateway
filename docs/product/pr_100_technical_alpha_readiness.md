# PR100 — alpha público técnico / go-no-go

## Escopo

PR100 cria `alpha-readiness/v1`: um verificador local read-only para consolidar o go/no-go técnico do alpha público. Ele cruza documentação canônica, matriz, roadmap, release-check e restrições públicas.

Não cria tag, release, publicação, pacote externo, anúncio, browser, n8n, voz, execução real ampla de tools MCP, social/career automation, OCR/PDF/Office, upload/envio externo ou autorização por conteúdo recuperado.

## Domínio, canal, autonomia e capacidade

- Domínio: prontidão de produto para alpha técnico.
- Canal: CLI, Gateway API protegida e Workbench local.
- Autonomia: verificação read-only; nenhuma mutação de arquivos, rede, tag ou publicação.
- Capacidade: `alpha.go_no_go_check` com decisão `candidate_go` ou `no_go`.

## Mudança funcional

A CLI ganha `lai-gateway alpha-readiness --target <versão> --json`; o Gateway expõe `/v1/gateway/alpha-readiness`; o Workbench ganha um painel de alpha readiness. A saída mostra decisão, fase de release-check, comandos obrigatórios e flags de segurança.

`candidate_go` significa apenas que o candidato técnico está pronto para revisão humana e possível publicação separada. Não equivale a publicar alpha, criar tag, enviar anúncio, habilitar capacidades externas ou declarar produto completo.

## Segurança preservada

- Verificação é read-only, secret-free e não inicia servidor.
- Sem tag, sem release, sem push, sem publicação e sem envio externo.
- Capacidades externas continuam bloqueadas por roadmap próprio.
- Conteúdo de memória, arquivo, ferramenta, modelo ou documento não concede autorização.
- Aprovação humana separada continua obrigatória para publicação pública.

## Evidência

Testes cobrem decisão `candidate_go`, bloqueio por no-go, ausência de publicação/autoridade, CLI/API/UI e documentação canônica.

Gate local: `PYTHON=python3 make check`.
