from __future__ import annotations

import os
from typing import Any

from pluck.application.ports import JsonStore
from pluck.domain.options import (
    AUDIO,
    AUDIO_FORMATS,
    COOKIE_BROWSERS,
    DEFAULT_FILENAME_TEMPLATE,
    DEFAULT_SUBTITLE_LANGUAGES,
    VIDEO,
    VIDEO_CONTAINERS,
    Preferences,
    safe_filename_template,
)

MAX_CONCURRENT_LIMIT = 6


ALLOWED_VALUES = {
    "defaultMode": (VIDEO, AUDIO),
    "defaultContainer": VIDEO_CONTAINERS,
    "defaultAudioFormat": AUDIO_FORMATS,
    "cookiesBrowser": ("", *COOKIE_BROWSERS),
}


def default_values(folder: str) -> dict[str, Any]:
    return {
        "folder": folder,
        "filenameTemplate": DEFAULT_FILENAME_TEMPLATE,
        "maxConcurrent": 3,
        "defaultMode": VIDEO,
        "defaultQuality": 1080,
        "defaultContainer": "mp4",
        "defaultAudioFormat": "mp3",
        "embedThumbnail": True,
        "embedMetadata": True,
        "embedChapters": True,
        "subtitles": False,
        "cookiesBrowser": "",
        "notifyOnFinish": True,
    }


def sanitize(key: str, value: Any, defaults: dict[str, Any]) -> Any:
    default = defaults[key]
    if type(value) is not type(default):
        return default
    if key in ALLOWED_VALUES and value not in ALLOWED_VALUES[key]:
        return default
    if key == "maxConcurrent":
        return min(max(value, 1), MAX_CONCURRENT_LIMIT)
    if key == "defaultQuality":
        return max(value, 0)
    if key == "folder" and not os.path.isabs(os.path.expanduser(value.strip())):
        return default
    return value


class SettingsStore:
    def __init__(self, file: JsonStore, default_folder: str):
        self._file = file
        self._defaults = default_values(default_folder)
        self._values = dict(self._defaults)
        self._load()

    def _load(self) -> None:
        stored = self._file.read()
        if not isinstance(stored, dict):
            return
        for key in self._defaults:
            if key in stored:
                self._values[key] = sanitize(key, stored[key], self._defaults)

    def has(self, key: str) -> bool:
        return key in self._defaults

    def default(self, key: str) -> Any:
        return self._defaults[key]

    def value(self, key: str) -> Any:
        return self._values[key]

    def update(self, key: str, value: Any) -> bool:
        cleaned = sanitize(key, value, self._defaults)
        if self._values[key] == cleaned:
            return False
        self._values[key] = cleaned
        return True

    def save(self) -> None:
        self._file.write(dict(self._values))

    @property
    def max_concurrent(self) -> int:
        return self._values["maxConcurrent"]

    @property
    def default_quality(self) -> int:
        return self._values["defaultQuality"]

    @property
    def cookies_browser(self) -> str:
        return self._values["cookiesBrowser"]

    @property
    def notify_on_finish(self) -> bool:
        return self._values["notifyOnFinish"]

    def preferences(self, folder: str | None = None) -> Preferences:
        return Preferences(
            folder=folder or self._values["folder"],
            filename_template=safe_filename_template(self._values["filenameTemplate"]),
            embed_thumbnail=self._values["embedThumbnail"],
            embed_metadata=self._values["embedMetadata"],
            embed_chapters=self._values["embedChapters"],
            subtitles=self._values["subtitles"],
            subtitle_languages=DEFAULT_SUBTITLE_LANGUAGES,
            cookies_browser=self._values["cookiesBrowser"],
        )
