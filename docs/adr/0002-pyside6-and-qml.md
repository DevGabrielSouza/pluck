# 0002. PySide6 com QML

Status: aceita

## Contexto

O alvo é Fedora com KDE Plasma no Wayland. A interface precisa de lista com progresso animado, thumbnails, tema escuro próprio e janela sem decoração do sistema. A lógica (fila, processo, parse) é Python.

## Decisão

PySide6 com Qt Quick. Python expõe objetos `QObject` como singletons do módulo `Pluck.Core`; o QML só lê propriedades e chama slots.

## Consequências

- Integração nativa com Wayland e KDE, sem navegador embutido.
- A fronteira Python e QML é dinâmica: o qmllint não enxerga os singletons registrados em runtime. `tools/lint_qml.py` filtra só esses avisos e o smoke de renderização (`tests/test_qml_smoke.py`) pega erro de binding que o lint não vê.
- Os stubs do PySide6 têm divergências com o runtime (por exemplo `qmlRegisterSingletonInstance`), por isso a checagem de tipos não substitui o teste de renderização.
