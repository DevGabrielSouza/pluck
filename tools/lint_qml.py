import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML_DIR = ROOT / "pluck" / "qml"
RUNTIME_SINGLETONS = {"AppSettings", "Analyzer", "Downloads", "Desktop"}
RUNTIME_MODULE = "Pluck.Core"
QMLLINT_CANDIDATES = (
    "pyside6-qmllint",
    "qmllint",
    "qmllint6",
    "/usr/lib64/qt6/bin/qmllint",
    "/usr/lib/qt6/bin/qmllint",
)


def find_qmllint() -> str:
    configured = os.environ.get("QMLLINT")
    if configured:
        return configured
    for candidate in QMLLINT_CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    sys.exit("qmllint not found; set QMLLINT to its path")


def is_runtime_noise(path: Path, warning: dict) -> bool:
    if warning["id"] == "import" and RUNTIME_MODULE in warning["message"]:
        return True
    if warning["id"] == "unqualified":
        line = path.read_text(encoding="utf-8").splitlines()[warning["line"] - 1]
        name = line[warning["column"] - 1 :].split(".")[0].split("(")[0].strip()
        return name in RUNTIME_SINGLETONS
    return False


def main() -> int:
    files = [QML_DIR / "Main.qml", *sorted((QML_DIR / "Pluck").glob("*.qml"))]
    result = subprocess.run(
        [find_qmllint(), "--json", "-", "-I", str(QML_DIR), *map(str, files)],
        capture_output=True,
        text=True,
        check=False,
    )
    data = json.loads(result.stdout)
    problems = []
    for entry in data["files"]:
        path = Path(entry["filename"])
        for warning in entry["warnings"]:
            if warning["type"] in ("warning", "critical") and not is_runtime_noise(path, warning):
                location = f"{path.relative_to(ROOT)}:{warning.get('line', 0)}:{warning.get('column', 0)}"
                problems.append(f"{location}: {warning['message']} [{warning['id']}]")
    for problem in problems:
        print(problem)
    print(f"qmllint: {len(problems)} problem(s) in {len(files)} files")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
