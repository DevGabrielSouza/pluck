# Segurança

## Escopo e confiança

O Pluck roda como o próprio usuário, no Linux, e chama o `yt-dlp` instalado no sistema. O que entra de fora e não é confiável:

- a URL colada ou lida da área de transferência;
- tudo o que o site devolve: título, canal, descrição, thumbnail, nome de arquivo, extensão, mensagens de erro;
- o conteúdo baixado.

O que é confiável por decisão: o próprio usuário, o executável `yt-dlp` e o `ffmpeg` do `PATH`, e as configurações e plugins do yt-dlp que o usuário ou o sistema mantêm (`~/.config/yt-dlp/config`, `~/.config/yt-dlp/plugins`, `/etc/yt-dlp.conf`, pacotes no `site-packages` e no `PYTHONPATH`). Quem consegue escrever nesses lugares já controla a conta.

O modelo de ameaças completo, com os achados da auditoria de 18/10/2026 e os riscos restantes, está em `docs/threat-model.md`.

## Defesas

| ameaça | defesa | onde |
|---|---|---|
| Config do yt-dlp plantada na pasta de downloads (`yt-dlp.conf` com `--exec`) executa código | todo processo roda com diretório de trabalho e `-P home:` numa pasta privada 0700; a pasta de destino entra só pelo `-o` absoluto | `adapters/process.py`, `adapters/ytdlp/commands.py`, ADR 0003 |
| Título com HTML (`<img src=...>`) faz a tela buscar recurso remoto ou imitar a interface | `AppText` usa `Text.PlainText` por padrão; o aviso de link copiado deixou de montar HTML | `qml/Pluck/AppText.qml`, `Composer.qml` |
| Modelo de nome de arquivo sai da pasta de destino (`/`, `~`, `..`) | modelo inseguro volta ao padrão ao carregar, ao montar o comando e na prévia; a tela avisa | `domain/options.py`, `application/settings.py` |
| Campo do site que vira `..` usado como pasta no modelo (`%(uploader)s/…`) | `--replace-in-metadata` troca por `_` valor sem letra nem dígito nesses campos, e a sanitização fica fixa (`--no-restrict-filenames --no-windows-filenames`); campo de pasta com formatação, barra dentro de `%()` ou padrão só de pontos torna o modelo inseguro | `domain/options.py`, `adapters/ytdlp/commands.py` |
| Modelo sem `%(id)s` faz arquivo do usuário com o mesmo nome contar como baixado e passar pelo pós-processamento | aviso nas Configurações | `qml/Pluck/SettingsPage.qml` |
| Metadado do site com quebra de linha forja linha de controle (`vcodec`) | marcadores com token aleatório por execução; caminho de arquivo fora da pasta do job é descartado | `adapters/ytdlp/commands.py`, `adapters/download_runner.py` |
| Cancelar ou fechar o app deixa ffmpeg ou outro filho do yt-dlp rodando | cada execução em sessão própria; cancelar, matar e recolher usam o grupo de processos; o encerramento cancela também a análise | `adapters/process.py`, `adapters/download_runner.py`, `adapters/media_probe.py`, `app.py` |
| Entrada relativa no `PATH` escolhe um executável do diretório atual | só entradas absolutas do `PATH` | `adapters/process.py` |
| Thumbnail com esquema local (`file://`, `image://`, `qrc:`) no histórico ou nos metadados | só http e https chegam ao QML | `domain/urls.py`, `domain/jobs.py`, `presentation/media_view.py` |
| `%` no caminho da pasta vira campo de template | `%` é escapado como `%%` antes do `-o` | `adapters/ytdlp/commands.py` |
| Pasta de destino relativa ou inválida | rejeitada nas configurações; um job com pasta inválida vai para `failed` com mensagem de erro | `application/settings.py`, `domain/options.py`, `application/downloads.py` |
| URL vira opção do yt-dlp ou usa esquema local (`file://`) | só http e https com host, sem espaço ou caractere de controle, até 4096 caracteres, sempre depois de `--`; URL que o `urlparse` recusa é tratada como inválida | `domain/urls.py`, `adapters/ytdlp/commands.py` |
| Argumentos injetados via idiomas de legenda ou navegador de cookies | idiomas passam por regex fechada; navegador precisa estar na lista conhecida | `domain/options.py`, `adapters/ytdlp/commands.py` |
| Abrir arquivo baixado executa um `.desktop` ou script | "Abrir" só abre extensões de mídia conhecidas; o resto é mostrado na pasta | `presentation/desktop.py`, `domain/media.py` |
| Notificação interpreta markup ou opção | `notify-send` recebe `--` e o corpo com HTML escapado | `adapters/desktop_shell.py` |
| URL assinada, token ou cookie em log e na tela de erro | detalhe de erro passa por `redact`, que mascara parâmetros sensíveis | `adapters/ytdlp/errors.py` |
| Linha gigante sem quebra no stdout esgota memória | linha parcial acima de 64 KB é descartada; stderr guarda só as últimas 30 linhas | `adapters/ytdlp/output.py`, `adapters/ytdlp/errors.py` |
| Histórico adulterado altera estado ao abrir | registro é normalizado; estados pendentes viram `interrupted`; id repetido ganha um novo; modelo de nome inseguro é neutralizado | `domain/jobs.py`, `domain/options.py` |
| Outro usuário fala com o socket de instância única ou ocupa o nome antes | socket e lock em `XDG_RUNTIME_DIR` (0700), fora do `/tmp` compartilhado; `QLocalServer` com `UserAccessOption` | `adapters/instance.py` |
| yt-dlp com vulnerabilidade conhecida | a barra de status avisa abaixo de 2026.07.04; `pip-audit` roda no CI | `domain/versions.py`, `scripts/check.sh` |
| Action do CI trocada por versão maliciosa na mesma tag | actions fixadas por SHA; o checkout não guarda o token | `.github/workflows/ci.yml` |

## Versão mínima do yt-dlp

A versão 2026.07.04 é a primeira sem nenhum aviso publicado no banco do `pip-audit` em outubro de 2026. Os que importam para o Pluck:

- CVE-2024-38519 e CVE-2026-50023: o site consegue gravar arquivo com extensão arbitrária, inclusive atalhos `.desktop`, na pasta de destino. O Pluck não abre esses arquivos, mas o gerenciador de arquivos pode.
- CVE-2026-50019, CVE-2026-50574, CVE-2026-26331, CVE-2026-55404 e GHSA-69qj-pvh9-c5wg: dependem de `curl` ou `aria2c` como downloader externo, `--netrc-cmd`, `--write-link` ou `--exec`. O Pluck não passa nenhuma dessas opções, mas a config do usuário pode.

O aviso não bloqueia o uso. Quem instala pelo `dnf` recebe a versão do Fedora.

## Cookies

Com "Cookies do navegador" ligado, o Pluck passa `--cookies-from-browser <navegador>` e o yt-dlp lê o banco de cookies localmente. O Pluck não lê, copia nem grava cookies. Os cookies só vão para o site da URL, pela regra de domínio do yt-dlp; vazamentos em redirecionamento já corrigidos dependem da versão mínima acima.

## Área de transferência

Quando a janela ganha foco, o Pluck lê o texto da área de transferência e, se parecer um link, oferece analisar. Nada é enviado antes do clique. Um link dispensado não volta a ser oferecido.

## Fora do escopo

- Windows e macOS: caminhos, abertura de arquivo e notificação são de Linux.
- Sandbox do yt-dlp ou do ffmpeg: os dois rodam com as permissões do usuário.
- Conteúdo malicioso dentro do arquivo de mídia: é responsabilidade do player.

## Como reportar

Ainda não há contato de segurança definido. Ver "Riscos restantes" em `docs/audit-report.md` e em `docs/threat-model.md`.
