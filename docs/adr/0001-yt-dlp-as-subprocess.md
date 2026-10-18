# 0001. yt-dlp como processo filho

Status: aceita

## Contexto

O yt-dlp tem uma API Python (`yt_dlp.YoutubeDL`), mas ela não é estável entre versões, não é feita para várias instâncias em threads e roda o download no mesmo processo da interface. Cancelar um download no meio pela API exige cooperação do código do yt-dlp.

## Decisão

Todo uso do yt-dlp é pelo executável, em `QProcess`. A comunicação é por argumentos e por templates de saída próprios (`--progress-template`, `--print`), lidos linha a linha.

## Consequências

- Cancelar é matar o processo. Travamento ou vazamento do yt-dlp não afeta a janela.
- O Pluck usa o yt-dlp que o usuário atualiza pelo sistema, sem fixar versão.
- O contrato com o yt-dlp é a linha de comando e os templates. Mudança de formato quebra a leitura; `tests/test_ytdlp.py` e os testes de integração com o executável real cobrem os pontos usados.
- A configuração do yt-dlp do usuário vale também no Pluck, o que exige isolar o diretório de trabalho (ADR 0003).
