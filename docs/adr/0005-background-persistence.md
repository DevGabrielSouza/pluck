# 0005. Gravação em segundo plano, parse da análise na thread da interface

Status: aceita

## Contexto

A regra é não bloquear a thread da interface com rede, disco ou processo. Medido nesta máquina (Fedora 44, NVMe, Python 3.14):

- gravar o histórico com `fsync` levou 10 ms ou mais por gravação, e acontece a cada mudança de estado de qualquer job;
- o parse e a transformação do JSON de análise levou cerca de 4 ms para um arquivo de 640 KB.

## Decisão

- Histórico e configurações são gravados por um `BackgroundWriter`: um `ThreadPoolExecutor` com um único worker, que preserva a ordem. Cada gravação recebe uma cópia dos dados, então a thread da interface pode continuar mudando o original.
- O parse do JSON da análise fica na thread da interface. A análise é limitada a 1000 itens de playlist (`PLAYLIST_LIMIT`), o que mantém o JSON na mesma ordem de grandeza medida.
- O processo do yt-dlp já é assíncrono por `QProcess`.

## Consequências

- A gravação atômica (`mkstemp`, `fsync`, `os.replace`, `fsync` da pasta) não pesa na interface.
- No encerramento, `AppServices.shutdown` grava o estado final e espera o worker terminar. Gravação depois do `close` acontece de forma síncrona, para não se perder.
- Se a análise passar a aceitar playlists maiores, o parse deve ir para uma thread.
