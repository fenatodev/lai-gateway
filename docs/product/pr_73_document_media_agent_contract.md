# pr 73: document/media agent contract

## objetivo

Registrar o document/media agent como contrato governado antes de qualquer ingestão real de arquivos, OCR, transcrição, upload externo ou processamento destrutivo.

## escopo

- adicionar document_media ao adapter registry;
- declarar domínio, canais, autonomia e capacidades solicitadas;
- manter granted_capabilities vazio;
- manter ingestão, OCR, transcrição, upload externo e processamento destrutivo desabilitados;
- limitar escopo de filesystem ao repo ou sandbox explícita;
- exigir aprovação humana para paths externos, OCR, transcrição, upload, escrita e processamento destrutivo.

## fora de escopo

- sem OCR pesado;
- sem transcrição real;
- sem leitura de mídia externa;
- sem upload externo;
- sem escrita em arquivos do usuário fora do repo/sandbox;
- sem conversão destrutiva ou sobrescrita de mídia/documentos.

## aceite

- registry expõe o contrato document_media;
- document_media não executa tools e não concede permissões;
- testes comprovam que OCR, transcrição, upload externo e processamento destrutivo permanecem desligados;
- make check passa.
