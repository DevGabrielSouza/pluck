#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python="${PYTHON:-python3}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

run() {
    echo "==> $*"
    "$@"
}

audit_requirements() {
    "$python" - <<'PY'
import importlib.metadata
import shutil
import subprocess

print(f"PySide6=={importlib.metadata.version('PySide6')}")
executable = shutil.which("yt-dlp")
if executable:
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    print(f"yt-dlp=={version}")
PY
}

run ruff check .
run ruff format --check .
run uvx --quiet pyright --pythonpath "$(command -v "$python")"
run "$python" -m pytest -q
run "$python" tools/lint_qml.py

if [[ "${SKIP_AUDIT:-}" != "1" ]]; then
    requirements="$(mktemp)"
    trap 'rm -f "$requirements"' EXIT
    audit_requirements >"$requirements"
    echo "==> pip-audit ($(paste -sd' ' "$requirements"))"
    uvx --quiet pip-audit --requirement "$requirements" --no-deps --disable-pip --progress-spinner off
fi
