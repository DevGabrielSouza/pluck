from __future__ import annotations

import os

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from pluck import __version__
from pluck.application.ports import DesktopShell
from pluck.domain.formatting import format_bytes, short_path
from pluck.domain.media import is_playable_file
from pluck.domain.urls import looks_like_url, normalize_url
from pluck.domain.versions import MINIMUM_VERSION_TEXT, is_outdated


class Desktop(QObject):
    toolsChanged = Signal()

    def __init__(self, shell: DesktopShell, parent: QObject | None = None):
        super().__init__(parent)
        self._shell = shell
        self._tools = {"yt-dlp": "", "ffmpeg": ""}
        self._checked: set[str] = set()

    def check_tools(self) -> None:
        self._shell.probe_tools(self._on_tool_version)

    def _on_tool_version(self, tool: str, version: str) -> None:
        self._tools[tool] = version
        self._checked.add(tool)
        self.toolsChanged.emit()

    def _get_ytdlp_version(self) -> str:
        return self._tools["yt-dlp"]

    def _get_ffmpeg_version(self) -> str:
        return self._tools["ffmpeg"]

    def _get_ytdlp_outdated(self) -> bool:
        return is_outdated(self._tools["yt-dlp"])

    def _get_tools_checked(self) -> bool:
        return self._checked == set(self._tools)

    def _get_app_version(self) -> str:
        return __version__

    ytdlpVersion = Property(str, _get_ytdlp_version, notify=toolsChanged)
    ffmpegVersion = Property(str, _get_ffmpeg_version, notify=toolsChanged)
    toolsChecked = Property(bool, _get_tools_checked, notify=toolsChanged)
    ytdlpOutdated = Property(bool, _get_ytdlp_outdated, notify=toolsChanged)
    minimumYtdlpVersion = Property(str, lambda _self: MINIMUM_VERSION_TEXT, constant=True)
    appVersion = Property(str, _get_app_version, constant=True)

    @Slot(result=str)
    def clipboardText(self) -> str:
        return QGuiApplication.clipboard().text().strip()

    @Slot(str)
    def copyText(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    @Slot(str, result=bool)
    def looksLikeUrl(self, text: str) -> bool:
        return looks_like_url(text)

    @Slot(str, result=str)
    def normalizeUrl(self, text: str) -> str:
        return normalize_url(text)

    @Slot(str, result=str)
    def shortPath(self, path: str) -> str:
        return short_path(path)

    @Slot(float, result=str)
    def formatBytes(self, value: float) -> str:
        return format_bytes(value)

    @Slot(str, result=bool)
    def pathExists(self, path: str) -> bool:
        return bool(path) and os.path.exists(path)

    @Slot(str, result=str)
    def localPath(self, url: str) -> str:
        return QUrl(url).toLocalFile() or url

    @Slot(str, result=str)
    def fileUrl(self, path: str) -> str:
        return QUrl.fromLocalFile(os.path.expanduser(path)).toString()

    @Slot(str)
    def openFolder(self, path: str) -> None:
        target = os.path.expanduser(path)
        if not target:
            return
        os.makedirs(target, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    @Slot(str, result=bool)
    def openFile(self, path: str) -> bool:
        if not path or not os.path.isfile(path):
            return False
        if is_playable_file(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.showInFolder(path)
        return True

    @Slot(str)
    def showInFolder(self, path: str) -> None:
        if not path or not os.path.exists(path):
            if path and os.path.isdir(os.path.dirname(path)):
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            return
        if not self._shell.show_item(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
