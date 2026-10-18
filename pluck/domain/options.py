from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

VIDEO = "video"


AUDIO = "audio"


BEST_QUALITY = 0


VIDEO_CONTAINERS = ("mp4", "mkv")


AUDIO_FORMATS = ("mp3", "m4a", "opus")


AUDIO_FORMAT_LABELS = {"mp3": "MP3", "m4a": "M4A", "opus": "Opus"}


COOKIE_BROWSERS = ("firefox", "chrome", "chromium", "brave", "edge", "vivaldi", "opera")


DEFAULT_FILENAME_TEMPLATE = "%(title)s [%(id)s].%(ext)s"


DEFAULT_SUBTITLE_LANGUAGES = "pt.*,en.*"


SUBTITLE_LANGUAGES_PATTERN = re.compile(r"^[\w.*,:-]{1,64}$")


TEMPLATE_FIELD = re.compile(r"%\((?P<expression>[^)]*)\)(?P<format>[-#0+ ]*\d*(?:\.\d+)?[A-Za-z])")


FIELD_WITH_SEPARATOR = re.compile(r"%\([^)]*/")


DIRECTORY_FIELD_FORMAT = re.compile(r"^[-#0+ ]*\d*[sd]$")


SIMPLE_FIELD_EXPRESSION = re.compile(
    r"^(?P<names>[A-Za-z_]\w*(?:,[A-Za-z_]\w*)*)(?:>[^&|]*)?(?:\|(?P<default>[^&|]*))?$"
)


class InvalidFolderError(ValueError):
    pass


def download_directory(folder: str) -> str:
    directory = os.path.expanduser(folder)
    if not os.path.isabs(directory):
        raise InvalidFolderError(f"download folder must be absolute: {folder!r}")
    return directory


def is_inside(folder: str, path: str) -> bool:
    try:
        base = _normalized(download_directory(folder))
    except InvalidFolderError:
        return False
    if not os.path.isabs(path):
        return False
    target = _normalized(path)
    return target != base and os.path.commonpath([base, target]) == base


def _normalized(path: str) -> str:
    return os.sep + os.path.normpath(path).lstrip(os.sep)


def _component_fields(component: str) -> tuple[str, ...] | None:
    if TEMPLATE_FIELD.sub("", component).strip("."):
        return ()
    names: list[str] = []
    for match in TEMPLATE_FIELD.finditer(component):
        simple = SIMPLE_FIELD_EXPRESSION.match(match.group("expression"))
        if (
            simple is None
            or not DIRECTORY_FIELD_FORMAT.match(match.group("format"))
            or (simple.group("default") is not None and not simple.group("default").strip("."))
        ):
            return None
        names.extend(simple.group("names").split(","))
    return tuple(names)


def directory_fields(template: str) -> tuple[str, ...] | None:
    names: list[str] = []
    for component in template.split("/")[:-1]:
        fields = _component_fields(component)
        if fields is None:
            return None
        names.extend(name for name in fields if name not in names)
    return tuple(names)


def safe_filename_template(template: str) -> str:
    candidate = template.strip()
    if not candidate or any(character in candidate for character in "\x00\r\n"):
        return DEFAULT_FILENAME_TEMPLATE
    if candidate.startswith(("/", "~")) or ".." in PurePosixPath(candidate).parts:
        return DEFAULT_FILENAME_TEMPLATE
    if FIELD_WITH_SEPARATOR.search(candidate) or directory_fields(candidate) is None:
        return DEFAULT_FILENAME_TEMPLATE
    return candidate


def names_the_id(template: str) -> bool:
    for match in TEMPLATE_FIELD.finditer(template.replace("%%", "")):
        simple = SIMPLE_FIELD_EXPRESSION.match(match.group("expression"))
        if (
            simple
            and simple.group("names").split(",")[0] == "id"
            and DIRECTORY_FIELD_FORMAT.match(match.group("format"))
        ):
            return True
    return False


def is_safe_filename_template(template: str) -> bool:
    return safe_filename_template(template) == template.strip()


def safe_subtitle_languages(languages: str) -> str:
    return languages if SUBTITLE_LANGUAGES_PATTERN.match(languages) else DEFAULT_SUBTITLE_LANGUAGES


def quality_label(short_side: int) -> str:
    return {4320: "8K", 2160: "4K"}.get(short_side, f"{short_side}p")


@dataclass(frozen=True)
class DownloadOptions:
    mode: str = VIDEO
    quality: int = BEST_QUALITY
    container: str = "mp4"
    audio_format: str = "mp3"

    @property
    def label(self) -> str:
        if self.mode == AUDIO:
            return AUDIO_FORMAT_LABELS[self.audio_format]
        resolution = "Melhor" if self.quality == BEST_QUALITY else quality_label(self.quality)
        return f"{resolution} · {self.container.upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "quality": self.quality,
            "container": self.container,
            "audioFormat": self.audio_format,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DownloadOptions:
        mode = raw.get("mode")
        container = raw.get("container")
        audio_format = raw.get("audioFormat")
        try:
            quality = max(0, int(raw.get("quality") or 0))
        except (TypeError, ValueError):
            quality = BEST_QUALITY
        return cls(
            mode=mode if mode in (VIDEO, AUDIO) else VIDEO,
            quality=quality,
            container=container if container in VIDEO_CONTAINERS else "mp4",
            audio_format=audio_format if audio_format in AUDIO_FORMATS else "mp3",
        )


@dataclass(frozen=True)
class Preferences:
    folder: str
    filename_template: str = DEFAULT_FILENAME_TEMPLATE
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    embed_chapters: bool = True
    subtitles: bool = False
    subtitle_languages: str = DEFAULT_SUBTITLE_LANGUAGES
    cookies_browser: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "folder": self.folder,
            "filenameTemplate": self.filename_template,
            "embedThumbnail": self.embed_thumbnail,
            "embedMetadata": self.embed_metadata,
            "embedChapters": self.embed_chapters,
            "subtitles": self.subtitles,
            "subtitleLanguages": self.subtitle_languages,
            "cookiesBrowser": self.cookies_browser,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Preferences:
        defaults = cls(folder="")

        def text(key: str, fallback: str) -> str:
            value = raw.get(key)
            return value if isinstance(value, str) and value.strip() else fallback

        def flag(key: str, fallback: bool) -> bool:
            value = raw.get(key)
            return value if isinstance(value, bool) else fallback

        return cls(
            folder=text("folder", ""),
            filename_template=safe_filename_template(text("filenameTemplate", defaults.filename_template)),
            embed_thumbnail=flag("embedThumbnail", defaults.embed_thumbnail),
            embed_metadata=flag("embedMetadata", defaults.embed_metadata),
            embed_chapters=flag("embedChapters", defaults.embed_chapters),
            subtitles=flag("subtitles", defaults.subtitles),
            subtitle_languages=safe_subtitle_languages(text("subtitleLanguages", defaults.subtitle_languages)),
            cookies_browser=text("cookiesBrowser", ""),
        )


SAMPLE_FIELDS = {
    "title": "Me at the zoo",
    "id": "jNQXAC9IVRw",
    "uploader": "jawed",
    "channel": "jawed",
    "upload_date": "20050424",
    "ext": "mp4",
    "playlist_index": "01",
    "playlist": "Minha playlist",
    "resolution": "1920x1080",
    "height": "1080",
}


def preview_filename(template: str) -> str:
    chosen = template.strip() or DEFAULT_FILENAME_TEMPLATE
    return re.sub(r"%\((\w+)\)[sd]", lambda match: SAMPLE_FIELDS.get(match.group(1), "NA"), chosen)
