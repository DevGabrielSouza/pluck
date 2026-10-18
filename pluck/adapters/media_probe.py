from __future__ import annotations

import json
import signal
from collections.abc import Callable

from PySide6.QtCore import QObject, QProcess

from pluck.adapters.process import YtDlpRuntime, read_text, signal_group
from pluck.adapters.ytdlp.commands import build_analyze_command
from pluck.adapters.ytdlp.errors import analysis_failure, launch_failure
from pluck.application.ports import ProbeResult

INVALID_OUTPUT_EXCERPT = 500


def probe_result(stdout: str, stderr: str, exit_code: int) -> ProbeResult:
    if exit_code != 0 or not stdout.strip():
        return analysis_failure(stderr, exit_code)
    try:
        data = json.loads(stdout)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return analysis_failure(stderr or stdout[:INVALID_OUTPUT_EXCERPT], exit_code)
    return data


class ProbeProcess:
    def __init__(self, process: QProcess, on_done: Callable[[ProbeResult], None], executable: str):
        self._process = process
        self._on_done = on_done
        self._executable = executable
        self._pid = 0
        process.started.connect(self._on_started)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)

    def start(self) -> None:
        self._process.start()

    def _on_started(self) -> None:
        self._pid = self._process.processId()

    def cancel(self) -> None:
        self._process.finished.disconnect()
        self._process.errorOccurred.disconnect()
        signal_group(self._pid or self._process.processId(), signal.SIGKILL)
        self._process.kill()
        self._process.deleteLater()

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        stdout = read_text(self._process.readAllStandardOutput())
        stderr = read_text(self._process.readAllStandardError())
        if exit_code != 0:
            signal_group(self._pid, signal.SIGKILL)
        self._process.deleteLater()
        self._on_done(probe_result(stdout, stderr, exit_code))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._process.deleteLater()
            self._on_done(launch_failure(self._executable, error.name))


class YtDlpMediaProbe(QObject):
    def __init__(self, runtime: YtDlpRuntime, parent: QObject | None = None):
        super().__init__(parent)
        self._runtime = runtime

    def prepare(
        self, url: str, include_playlist: bool, cookies_browser: str, on_done: Callable[[ProbeResult], None]
    ) -> ProbeProcess:
        runtime = self._runtime
        command = build_analyze_command(runtime.executable, url, include_playlist, cookies_browser, str(runtime.home))
        return ProbeProcess(runtime.process(command, self), on_done, runtime.executable)
