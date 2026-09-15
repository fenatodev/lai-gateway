# pr 70: voice mvp contract

## objetivo

Registrar o voice adapter como contrato governado antes de qualquer captura de áudio, wake word, STT/TTS ou execução de comando por voz.

## escopo

- adicionar voice ao adapter registry;
- declarar domínio, canais, autonomia e capacidades solicitadas;
- manter granted_capabilities vazio;
- manter captura de áudio, wake word, credenciais e efeitos externos desabilitados;
- exigir aprovação humana para microfone, listener contínuo, transcript externo e execução de ação.

## fora de escopo

- sem captura real de microfone;
- sem wake word;
- sem STT/TTS real;
- sem integração Android, Telegram ou desktop;
- sem execução de ações por voz;
- sem envio de áudio/transcrição para serviços externos.

## aceite

- registry expõe o contrato voice;
- voice não executa tools e não concede permissões;
- testes comprovam que áudio, wake word e efeitos externos permanecem desligados;
- make check passa.
