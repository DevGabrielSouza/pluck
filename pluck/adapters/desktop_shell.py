from __future__ import annotations

import html
import re
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QUrl

from pluck import APP_NAME
from pluck.adapters.process import find_executable, read_text

VERSION_PATTERN = re.compile(r"(\d[\w.\-]*)")


TOOL_ARGUMENTS = {"yt-dlp": ["--version"], "ffmpeg": ["-hide_banner", "-version"]}


def parse_tool_version(tool: str, output: str) -> str:
    lines = output.strip().splitlines()
    first_line = lines[0] if lines else ""
    if tool == "ffmpeg":
        first_line = first_line.removeprefix("ffmpeg version ").split(" ")[0]
    match = VERSION_PATTERN.search(first_line)
    return match.group(1) if match else ""


def send_notification(icon_path: Path, title: str, body: str) -> None:
    arguments = ["-a", APP_NAME, "-i", str(icon_path), "--", title, html.escape(body, quote=False)]
    QProcess.startDetached(find_executable("notify-send"), arguments)


class QtDesktopShell(QObject):
    def __init__(
        self, ytdlp_executable: str = "yt-dlp", ffmpeg_executable: str = "ffmpeg", parent: QObject | None = None
    ):
        super().__init__(parent)
        self._executables = {"yt-dlp": ytdlp_executable, "ffmpeg": ffmpeg_executable}

    def probe_tools(self, on_version: Callable[[str, str], None]) -> None:
        for tool, arguments in TOOL_ARGUMENTS.items():
            self._probe(tool, arguments, on_version)

    def _probe(self, tool: str, arguments: list[str], on_version: Callable[[str, str], None]) -> None:
        process = QProcess(self)

        def finished(exit_code: int, _status: QProcess.ExitStatus) -> None:
            output = read_text(process.readAllStandardOutput())
            process.deleteLater()
            on_version(tool, parse_tool_version(tool, output) if exit_code == 0 else "")

        def failed(error: QProcess.ProcessError) -> None:
            if error == QProcess.ProcessError.FailedToStart:
                process.deleteLater()
                on_version(tool, "")

        process.finished.connect(finished)
        process.errorOccurred.connect(failed)
        process.start(self._executables[tool], arguments)

    def show_item(self, path: str) -> bool:
        encoded = bytes(QUrl.toPercentEncoding(path, b"/").data()).decode()
        started, _pid = QProcess.startDetached(
            find_executable("gdbus"),
            [
                "call",
                "--session",
                "--dest",
                "org.freedesktop.FileManager1",
                "--object-path",
                "/org/freedesktop/FileManager1",
                "--method",
                "org.freedesktop.FileManager1.ShowItems",
                f"['file://{encoded}']",
                "",
            ],
        )
        return started
