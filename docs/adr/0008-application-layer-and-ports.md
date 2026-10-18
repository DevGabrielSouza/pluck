# 0008. Camada de aplicação e portas nas fronteiras externas

Status: aceita. Substitui a parte de camadas da ADR 0007; a checagem com pyright continua valendo.

## Contexto

Depois da ADR 0007, `domain` e `ytdlp` eram puros, mas `services/` acumulava três papéis:

- objeto Qt exposto ao QML (propriedades, slots, sinais);
- caso de uso (fila, agendamento, cancelamento, análise de link, poda do histórico);
- adapter (QProcess, SIGINT, leitura de stdout e stderr, arquivo JSON, `gdbus`, `notify-send`).

O `DownloadManager` tinha 387 linhas com tudo isso junto. Qualquer regra da fila só era testável com processo real e event loop, e a ordem de eventos (cancelar no meio, falha ao iniciar, pasta inválida liberando a vaga) dependia de tempo.

Havia duplicação entre `Analyzer` e `DownloadManager`: a escolha da linha que representa o erro no stderr, a mensagem de yt-dlp ausente, a cauda de 30 linhas e a decodificação da saída do processo. `describe_media`, com 73 linhas, estava em `domain`, mas monta o dicionário da tela com rótulos em português e o prefixo "≈". O `Desktop` disparava processos de dentro da apresentação.

O teste de caracterização do cancelamento da análise achou um bug latente: `Analyzer.cancel()` matava o processo sem desligar os sinais. Se o `Analyzer` fosse destruído antes de o processo terminar, o `finished` chamava um objeto já liberado e o Python caía com segfault. Foi reproduzido isolado e corrigido desligando os sinais antes do `kill()`.

## Decisão

1. Cinco pacotes: `domain`, `application`, `adapters` (com `adapters/ytdlp`), `presentation` e `app.py`. As dependências apontam para dentro, conforme a tabela de `docs/architecture.md`, e `tests/test_architecture.py` verifica a tabela e que nenhum módulo fica fora de camada.
2. Porta só onde há fronteira de verdade, pelo critério: ela fala com algo fora do processo Python (processo filho, disco, D-Bus), ou é preciso inverter a dependência para a aplicação não importar Qt. Ficaram cinco: `DownloadRunner`, `MediaProbe`, `DesktopShell`, `JsonStore` e `JobList`. `SettingsStore`, `DownloadQueue`, `MediaAnalysis`, `Settings`, os list models e o `IconProvider` são classes concretas, sem interface.
3. As portas de processo separam montar de iniciar (`prepare` e depois `start`). O `QProcess` pode emitir `FailedToStart` de dentro do `start()`, então o caso de uso registra a execução e muda o estado do job antes de iniciar, como o código anterior fazia.
4. O comportamento observável foi preservado. Os testes de caracterização (`tests/test_characterization.py` e o snapshot `tests/fixtures/described_media.json`) foram escritos e passaram contra o código anterior, antes de qualquer extração, e continuam passando.
5. Diferenças conscientes, todas fora do caminho normal:
   - o detalhe de erro da análise passa a descartar linhas em branco e espaços nas pontas de cada linha do stderr, como o detalhe do download já fazia;
   - uma saída de `yt-dlp -J` que é JSON válido mas não é objeto vira erro de análise, em vez de exceção sem tratamento no slot;
   - cada item do `enqueue` vira `JobRequest` antes do filtro de URL, então um item com `expectedSizes` não numérico levanta erro mesmo com URL inválida (o QML não monta item assim);
   - depois de gravar, `countsChanged` só é emitido quando algum job foi podado.

## Alternativas descartadas

- DDD com agregados, repositórios e eventos de domínio: o domínio tem um estado de job e um conjunto de opções. Isso acrescentaria cerimônia sem nenhuma regra nova.
- Porta para `Settings`, área de transferência e `QDesktopServices`: são API de tela do Qt, com uma implementação só, e já são testados como estão.
- Fila dona da lista, avisando a tela depois de cada mutação: quebra o contrato do `QAbstractListModel`, que exige `beginRemoveRows` antes da remoção (o proxy de filtro lê a linha que vai sair). Por isso a fila altera os jobs pela porta `JobList`, que o próprio list model cumpre.
- Tirar de `domain` os textos em português do job (`stage`, `detail`): eles são gravados no `history.json`, então a mudança pede migração do arquivo. Fica para outra decisão.

## Consequências

- A camada de aplicação é testada sem Qt e sem processo (`tests/test_application.py`), inclusive cancelamento que vence o código de saída, falha ao iniciar depois de cancelar, pasta inválida liberando a vaga na mesma passada e eventos que chegam depois do encerramento.
- O QML não mudou: nomes registrados, propriedades e slots continuam os mesmos.
- Os construtores mudaram: `Settings(JsonStore)`, `Analyzer(Settings, MediaProbe)`, `DownloadManager(Settings, JsonStore, DownloadRunner)` e `Desktop(DesktopShell)`. Quem escolhe os adapters é o `app.py`; os testes usam as fábricas do `tests/conftest.py`, e o `tools/screenshot.py` usa um probe com fixture em vez de mexer em atributo privado.
- O custo é mais arquivos e um salto a mais para seguir o fluxo de um download (fila, porta, runner).
