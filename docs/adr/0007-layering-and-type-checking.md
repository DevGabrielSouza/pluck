# 0007. Camadas com regra verificada e pyright

Status: substituída pela ADR 0008 na parte de camadas; a decisão sobre o pyright continua valendo.

## Contexto

`ytdlp.py`, `downloads.py` e `progress.py` misturavam regra de negócio, montagem de comando e objetos Qt. Testar uma regra exigia Qt e processo.

## Decisão

- Quatro camadas: `domain` (puro), `ytdlp` (puro, depende de `domain`), `services` (Qt) e `app` (composição). `tests/test_architecture.py` falha se um import quebrar a direção.
- Checagem de tipos com pyright em modo `standard`. O mypy não enxerga os stubs do PySide6, que não trazem `py.typed`.

## Consequências

- As regras são testadas sem `QCoreApplication`.
- O pyright precisa apontar para o Python que tem o PySide6 (`--pythonpath`), o que o `scripts/check.sh` faz.
