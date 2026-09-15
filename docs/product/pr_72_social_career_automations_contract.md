# pr 72: social/career automations contract

## objetivo

Registrar o adapter de automações sociais e de carreira como contrato governado antes de qualquer publicação, mensagem, formulário ou candidatura.

## escopo

- adicionar `social_career` ao adapter registry;
- declarar domínio, canais, autonomia e capacidades solicitadas;
- manter `granted_capabilities` vazio;
- manter publicação, envio de mensagens, candidaturas, formulários, credenciais e efeitos externos desabilitados;
- exigir aprovação humana para publicar, enviar mensagem, submeter candidatura, submeter formulário e usar conta autenticada.

## fora de escopo

- sem publicação em LinkedIn, GitHub, Instagram ou qualquer rede;
- sem envio de mensagens;
- sem preenchimento/submissão de formulários;
- sem candidatura a vaga;
- sem uso de credenciais;
- sem chamada para serviço externo.

## aceite

- registry expõe o contrato `social_career`;
- `social_career` não executa tools e não concede permissões;
- testes comprovam que publicação, mensagens, candidatura, formulários e efeitos externos permanecem desligados;
- `make check` passa.
