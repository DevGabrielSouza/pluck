# 0004. Máquina de estados explícita para o download

Status: aceita, com a tabela de estados substituída pela ADR 0009

## Contexto

O estado do job era atribuído direto em vários pontos do `DownloadManager`. Não havia como saber quais mudanças eram válidas, e cada caminho zerava ou não o progresso, o erro e o horário de término por conta própria.

## Decisão

`pluck/domain/jobs.py` define `TRANSITIONS`, a tabela de estados permitidos, e `DownloadJob.transition()`, o único jeito de mudar o estado. A transição cuida dos efeitos colaterais: zera velocidade, limpa erro e progresso ao voltar para `queued`, marca o término nos estados finais.

## Consequências

- Transição inválida levanta `InvalidTransitionError` em vez de deixar o job num estado incoerente.
- `tests/test_jobs.py` verifica a tabela inteira, par a par.
- O histórico carregado passa pela mesma regra: estados pendentes viram `interrupted`.
