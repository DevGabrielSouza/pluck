# 0003. Isolar a configuração do yt-dlp da pasta de downloads

Status: aceita

## Contexto

O yt-dlp procura `yt-dlp.conf` na pasta `home` dada por `-P`, ou no diretório de trabalho quando não há `-P`. A versão anterior passava a pasta de downloads como `-P`. Um arquivo `yt-dlp.conf` gravado ali, por um download anterior ou por qualquer outro programa, era carregado no próximo download, e opções como `--exec` executam comandos. O teste `test_real_ytdlp_would_load_it_if_the_folder_were_the_home` reproduz isso com o yt-dlp real.

## Decisão

Todo processo do yt-dlp roda com diretório de trabalho e `-P home:` em `~/.local/share/pluck/yt-dlp-home`, criada com modo 0700. A pasta de destino entra só no `-o`, como caminho absoluto, com `%` escapado.

## Consequências

- Config plantada na pasta de downloads é ignorada; `test_real_ytdlp_ignores_a_config_planted_in_the_download_folder` prova com `yt-dlp -v --simulate`.
- As configs do usuário e do sistema continuam valendo, por decisão (ver `docs/security.md`).
- Arquivos temporários do yt-dlp com caminho relativo vão para a pasta privada, não para o diretório de onde o app foi aberto.

Reverter é voltar ao `-P <pasta>`, o que reabre a falha. Não há motivo para isso.
