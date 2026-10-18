from __future__ import annotations

import contextlib
import os
import signal
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QByteArray, QObject, QProcess, QProcessEnvironment

ISOLATION_FLAGS = (
    QProcess.UnixProcessFlag.CreateNewSession
    | QProcess.UnixProcessFlag.ResetSignalHandlers
    | QProcess.UnixProcessFlag.CloseFileDescriptors
)


FALLBACK_DIRECTORY = "/usr/bin"


def find_executable(name: str, search_path: str | None = None) -> str:
    if os.sep in name:
        return name
    entries = (os.environ.get("PATH", "") if search_path is None else search_path).split(os.pathsep)
    trusted = [entry for entry in entries if os.path.isabs(entry)]
    for entry in trusted:
        candidate = os.path.join(entry, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return os.path.join(trusted[0] if trusted else FALLBACK_DIRECTORY, name)


def signal_group(pid: int, sig: signal.Signals) -> None:
    if pid <= 0:
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, sig)


@dataclass(frozen=True)
class YtDlpRuntime:
    executable: str
    home: Path

    @classmethod
    def prepare(cls, executable: str, home: Path) -> YtDlpRuntime:
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        return cls(find_executable(executable), home)

    def process(self, command: list[str], parent: QObject) -> QProcess:
        process = QProcess(parent)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUNBUFFERED", "1")
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(self.home))
        process.setUnixProcessParameters(ISOLATION_FLAGS)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        return process


def read_text(data: QByteArray) -> str:
    return bytes(data.data()).decode("utf-8", "replace")
