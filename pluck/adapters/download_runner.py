from __future__ import annotations

import logging
import os
import signal

from PySide6.QtCore import QObject, QProcess, QTimer

from pluck.adapters.process import YtDlpRuntime, read_text, signal_group
from pluck.adapters.ytdlp.commands import OutputMarkers, build_download_command
from pluck.adapters.ytdlp.errors import StderrTail, download_failure, launch_failure
from pluck.adapters.ytdlp.output import parse_file_line, parse_postprocess_line, parse_progress_line, split_lines
from pluck.application.ports import RunListener, RunOutcome
from pluck.domain.jobs import DownloadJob
from pluck.domain.options import is_inside

CANCEL_GRACE_MS = 3000


SHUTDOWN_WAIT_MS = 1000


logger = logging.getLogger(__name__)


def file_size(path: str) -> int:
    try:
        return os.path.getsize(path) if path else 0
    except OSError:
        return 0


class ProcessRun:
    def __init__(
        self,
        job_id: str,
        folder: str,
        process: QProcess,
        listener: RunListener,
        executable: str,
        markers: OutputMarkers,
    ):
        self._job_id = job_id
        self._folder = folder
        self._process = process
        self._listener = listener
        self._executable = executable
        self._markers = markers
        self._pending = ""
        self._tail = StderrTail()
        self._file_path = ""
        self._pid = 0
        self._stopping = False
        self._finished = False
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.started.connect(self._on_started)
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)

    def start(self) -> None:
        self._process.start()

    def interrupt(self) -> None:
        if self._finished:
            return
        self._stopping = True
        signal_group(self._group(), signal.SIGINT)
        QTimer.singleShot(CANCEL_GRACE_MS, self._force_kill)

    def kill(self) -> None:
        if self._finished:
            return
        self._stopping = True
        signal_group(self._group(), signal.SIGKILL)
        self._process.kill()
        self._process.waitForFinished(SHUTDOWN_WAIT_MS)

    def _force_kill(self) -> None:
        if not self._finished:
            signal_group(self._group(), signal.SIGKILL)
            self._process.kill()

    def _on_started(self) -> None:
        self._pid = self._process.processId()

    def _group(self) -> int:
        return self._pid or self._process.processId()

    def _read_output(self) -> None:
        lines, self._pending = split_lines(self._pending, read_text(self._process.readAllStandardOutput()))
        for line in lines:
            self._dispatch(line)

    def _dispatch(self, line: str) -> None:
        markers = self._markers
        if (update := parse_progress_line(line, markers)) is not None:
            self._listener.on_progress(self._job_id, update)
        elif (postprocess := parse_postprocess_line(line, markers)) is not None:
            self._listener.on_postprocess(self._job_id, postprocess[1])
        elif (path := parse_file_line(line, markers)) is not None:
            self._accept_file(path)
        else:
            self._tail.add(line)

    def _accept_file(self, path: str) -> None:
        if not is_inside(self._folder, path):
            logger.warning("ignoring a reported file outside the download folder: %r", path)
            return
        self._file_path = path
        self._listener.on_file(self._job_id, path)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._finished:
            return
        self._read_output()
        if self._pending.strip():
            self._dispatch(self._pending.strip())
        self._pending = ""
        succeeded = exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0
        if not succeeded or self._stopping:
            signal_group(self._pid, signal.SIGKILL)
        if succeeded:
            self._finish(RunOutcome(file_size=file_size(self._file_path), file_reported=bool(self._file_path)))
        else:
            crashed = exit_status == QProcess.ExitStatus.CrashExit and not self._stopping
            self._finish(RunOutcome(failure=download_failure(self._tail, exit_code, crashed)))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart and not self._finished:
            self._finish(RunOutcome(failure=launch_failure(self._executable, error.name), launched=False))

    def _finish(self, outcome: RunOutcome) -> None:
        self._finished = True
        self._process.deleteLater()
        self._listener.on_exit(self._job_id, outcome)


class QtDownloadRunner(QObject):
    def __init__(self, runtime: YtDlpRuntime, parent: QObject | None = None):
        super().__init__(parent)
        self._runtime = runtime

    def prepare(self, job: DownloadJob, listener: RunListener) -> ProcessRun:
        runtime = self._runtime
        markers = OutputMarkers.generate()
        command = build_download_command(
            runtime.executable, job.url, job.options, job.preferences, str(runtime.home), markers
        )
        process = runtime.process(command, self)
        return ProcessRun(job.id, job.folder, process, listener, runtime.executable, markers)
