from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Property, QObject, QStandardPaths, QTimer, Signal, Slot

from pluck.application.ports import JsonStore
from pluck.application.settings import SettingsStore
from pluck.domain.options import (
    Preferences,
    is_safe_filename_template,
    names_the_id,
    preview_filename,
    safe_filename_template,
)

SAVE_DELAY_MS = 400


def default_folder() -> str:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    return location or os.path.expanduser("~/Downloads")


def _stored(key: str, kind: type, notify: Signal) -> Property:
    return Property(
        kind,
        lambda self: self.value(key),
        lambda self, value: self.update(key, value),
        notify=notify,
    )


class Settings(QObject):
    changed = Signal()

    def __init__(self, file: JsonStore, parent: QObject | None = None):
        super().__init__(parent)
        self._store = SettingsStore(file, default_folder())
        self._save_timer = QTimer(self, singleShot=True, interval=SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.save)

    @property
    def store(self) -> SettingsStore:
        return self._store

    def update(self, key: str, value: Any) -> None:
        if self._store.update(key, value):
            self.changed.emit()
            self._save_timer.start()

    @Slot()
    def save(self) -> None:
        self._save_timer.stop()
        self._store.save()

    def value(self, key: str) -> Any:
        return self._store.value(key)

    def preferences(self, folder: str | None = None) -> Preferences:
        return self._store.preferences(folder)

    @Slot(str)
    def resetValue(self, key: str) -> None:
        if self._store.has(key):
            self.update(key, self._store.default(key))

    @Slot(str, result=str)
    def previewFilename(self, template: str) -> str:
        return preview_filename(safe_filename_template(template))

    @Slot(str, result=bool)
    def isFilenameTemplateSafe(self, template: str) -> bool:
        return is_safe_filename_template(template)

    @Slot(str, result=bool)
    def namesTheId(self, template: str) -> bool:
        return names_the_id(template)

    folder = _stored("folder", str, changed)
    filenameTemplate = _stored("filenameTemplate", str, changed)
    maxConcurrent = _stored("maxConcurrent", int, changed)
    defaultMode = _stored("defaultMode", str, changed)
    defaultQuality = _stored("defaultQuality", int, changed)
    defaultContainer = _stored("defaultContainer", str, changed)
    defaultAudioFormat = _stored("defaultAudioFormat", str, changed)
    embedThumbnail = _stored("embedThumbnail", bool, changed)
    embedMetadata = _stored("embedMetadata", bool, changed)
    embedChapters = _stored("embedChapters", bool, changed)
    subtitles = _stored("subtitles", bool, changed)
    cookiesBrowser = _stored("cookiesBrowser", str, changed)
    notifyOnFinish = _stored("notifyOnFinish", bool, changed)
