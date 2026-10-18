# Pluck

Interface desktop pro [yt-dlp](https://github.com/yt-dlp/yt-dlp). Cola o link, escolhe vídeo ou áudio e a qualidade, e baixa. Aceita playlist e canal, mostra o tamanho estimado antes de baixar e mantém uma fila com histórico.

Feito com PySide6 e QML, testado no Fedora 44 com KDE Plasma no Wayland.

## Requisitos

- Python 3.12+
- PySide6 6.10+ (`sudo dnf install python3-pyside6`)
- yt-dlp 2026.07.04+ e ffmpeg no `PATH` (`sudo dnf install yt-dlp ffmpeg`). Versões anteriores têm falhas de segurança conhecidas e o app avisa na barra de status.
- Node.js, pro yt-dlp resolver os desafios de JavaScript do YouTube

## Instalação

```bash
scripts/install.sh
```

Cria o comando `pluck` em `~/.local/bin`, o atalho no menu e o ícone. Pra remover, `scripts/install.sh --uninstall`.

Sem instalar, dá pra rodar direto da pasta com `python3 -m pluck`.

## Onde ficam os dados

| O quê | Onde |
|---|---|
| Configurações | `~/.config/pluck/settings.json` |
| Histórico da fila | `~/.local/share/pluck/history.json` |
| Pasta de trabalho do yt-dlp | `~/.local/share/pluck/yt-dlp-home/` |

O Pluck chama o executável `yt-dlp`, então o que estiver em `~/.config/yt-dlp/config` também vale aqui. Um `yt-dlp.conf` dentro da pasta de downloads é ignorado de propósito (ver `docs/security.md`).

## Desenvolvimento

```bash
scripts/check.sh
```

Roda ruff, pyright, pytest (inclusive o smoke de renderização da tela), qmllint e pip-audit. Precisa do [uv](https://docs.astral.sh/uv/) para o pyright e o pip-audit; `SKIP_AUDIT=1` pula a consulta de vulnerabilidades quando não há rede. O CI roda o mesmo script.

```bash
python3 tools/screenshot.py video /tmp/video.png
```

O `tools/screenshot.py` renderiza a interface fora da tela com dados de exemplo. Os cenários são `idle`, `video`, `audio`, `playlist`, `error`, `loading`, `settings` e `empty`.

Documentação: [arquitetura](docs/architecture.md), [segurança](docs/security.md), [decisões](docs/adr/) e [relatório da auditoria](docs/audit-report.md).

Os ícones são do [Lucide](https://lucide.dev) (licença ISC).
