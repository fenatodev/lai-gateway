# LAI Gateway release checklist

Checklist público e source-only para candidatos do `lai-gateway`. Este documento
complementa `docs/RELEASE.md`: ele organiza a verificação humana e operacional,
mas não publica tags, releases, pacotes, mensagens ou artefatos externos.

## Escopo atual

O candidato atual é source-first. O artefato identificável é o par:

- versão declarada em `lai_gateway.__version__` e `pyproject.toml`;
- commit exato integrado em `main` por PR com CI verde.

Não há promessa de PyPI, binário, instalador one-click, hosted service ou cloud
runtime. Publicar qualquer release externa continua sendo decisão manual separada.

## Pré-condições

- Branch candidata integrada por pull request normal.
- `main` local sincronizado com `origin/main`.
- Árvore limpa.
- Harness compatível disponível localmente quando o milestone gate for usado.
- Nenhum token, chat id, path privado ou credencial nas evidências.

## Comandos obrigatórios

Execute a partir do checkout `lai-gateway` limpo:

```bash
git checkout main
git fetch origin main
git pull --ff-only origin main
git status --short
python3 -m lai_gateway --version
python3 - <<'PY'
import tomllib
from lai_gateway import __version__
project = tomllib.load(open('pyproject.toml', 'rb'))['project']['version']
assert __version__ == project, (__version__, project)
print(__version__)
PY
PYTHON=python3 make check
python3 -m lai_gateway release-check --target 0.1.36 --json
python3 -m lai_gateway alpha-readiness --target 0.1.36 --json
```

Para compatibilidade Gateway/Harness local:

```bash
make milestone-gate   HARNESS_REPO=/path/to/workspace/lai-harness-checkout   TARGET_GATEWAY=0.1.36   MIN_HARNESS=0.4.6
```

O `milestone-gate` é uma verificação local. Ele não substitui CI, revisão humana
ou decisão explícita de publicação.

## Evidência mínima

Registre no PR ou na nota de release interna:

- commit SHA de `main`;
- versão `0.1.36` ou versão alvo declarada;
- CI do PR e, quando aplicável, CI em tag;
- resultado de `PYTHON=python3 make check`;
- resultado de `release-check --json`, sem copiar segredos;
- resultado de `alpha-readiness --json`, sem copiar segredos;
- resultado de `milestone-gate` quando Harness estiver disponível;
- link para `docs/quickstart.md`;
- link para `docs/workbench_visual_guide.md`.

## No-go

Não avançar se houver:

- versão divergente entre pacote e `pyproject.toml`;
- árvore suja;
- CI vermelha ou pendente;
- `make check` falhando;
- `release-check` fora de `phase=ready_to_tag` quando a intenção for tag;
- `alpha-readiness` fora de `decision=candidate_go` quando a intenção for declarar candidato técnico;
- evidência contendo token, chat id, path privado ou conteúdo de usuário;
- README, quickstart ou guia visual prometendo capacidades externas prontas.

## Capacidades não incluídas

Este checklist não libera browser autenticado, n8n activation, execução real de
tools MCP, envio de mensagens por agente, publicação externa, voz operacional,
automação social/carreira, processamento amplo de documentos ou uso de
credenciais. Esses caminhos dependem dos gates posteriores do roadmap.

## Relação com `docs/RELEASE.md`

`docs/RELEASE.md` mantém a governança estável de release. Este checklist é o
roteiro operacional de verificação do candidato técnico atual. Em conflito,
prevalecem a política de release, o roadmap canônico, a matriz de implementação e
os critérios de alpha readiness.
