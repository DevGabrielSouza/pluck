import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "pluck"
QT = ("PySide6", "shiboken6")
FORBIDDEN = {
    "domain": (*QT, "pluck.application", "pluck.adapters", "pluck.presentation", "pluck.app"),
    "application": (*QT, "pluck.adapters", "pluck.presentation", "pluck.app"),
    "adapters/ytdlp": (*QT, "pluck.presentation", "pluck.app"),
    "adapters": ("pluck.presentation", "pluck.app"),
    "presentation": ("pluck.adapters", "pluck.app"),
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def layer_files() -> list[tuple[str, Path]]:
    return [(layer, path) for layer in FORBIDDEN for path in sorted((PACKAGE / layer).rglob("*.py"))]


@pytest.mark.parametrize(
    ("layer", "path"),
    layer_files(),
    ids=lambda value: value if isinstance(value, str) else str(value.relative_to(PACKAGE)),
)
def test_dependencies_point_inwards(layer, path):
    offending = {
        module
        for module in imported_modules(path)
        if any(module == banned or module.startswith(banned + ".") for banned in FORBIDDEN[layer])
    }
    assert not offending, f"{path.relative_to(PACKAGE)} imports {sorted(offending)}"


def test_every_module_belongs_to_a_layer():
    covered = {path for _layer, path in layer_files()}
    loose = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*.py")
        if path not in covered and path.parent != PACKAGE
    }
    assert not loose, f"modules outside every layer: {sorted(loose)}"
