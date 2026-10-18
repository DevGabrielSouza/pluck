from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from pluck.domain.options import (
    AUDIO,
    BEST_QUALITY,
    COOKIE_BROWSERS,
    VIDEO,
    DownloadOptions,
    Preferences,
    directory_fields,
    download_directory,
    safe_filename_template,
    safe_subtitle_languages,
)

PROGRESS_FIELDS = (
    "progress.status",
    "progress.downloaded_bytes",
    "progress.total_bytes",
    "progress.total_bytes_estimate",
    "progress.speed",
    "progress.eta",
    "progress.fragment_index",
    "progress.fragment_count",
    "info.format_id",
    "info.vcodec",
    "info.acodec",
)


PLAYLIST_LIMIT = 1000


NAMELESS_VALUE = r"^[\W_]*$"


PREDICTABLE_SANITIZING = ["--no-restrict-filenames", "--no-windows-filenames"]


@dataclass(frozen=True)
class OutputMarkers:
    token: str

    @classmethod
    def generate(cls) -> OutputMarkers:
        return cls(secrets.token_hex(8))

    @property
    def progress(self) -> str:
        return f"PLUCK_PROGRESS_{self.token} "

    @property
    def postprocess(self) -> str:
        return f"PLUCK_POST_{self.token} "

    @property
    def file(self) -> str:
        return f"PLUCK_FILE_{self.token} "

    def arguments(self) -> list[str]:
        progress = "download:" + self.progress + "|".join(f"%({name})s" for name in PROGRESS_FIELDS)
        postprocess = "postprocess:" + self.postprocess + "%(progress.status)s|%(progress.postprocessor)s"
        moved = f"after_move:{self.file}%(filepath)s"
        return ["--progress-template", progress, "--progress-template", postprocess, "--print", moved]


def cookie_args(browser: str) -> list[str]:
    return ["--cookies-from-browser", browser] if browser in COOKIE_BROWSERS else []


def format_args(options: DownloadOptions) -> list[str]:
    if options.mode == AUDIO:
        selector = "ba[ext=m4a]/ba/b" if options.audio_format == "m4a" else "ba/b"
        return ["-f", selector, "-x", "--audio-format", options.audio_format, "--audio-quality", "0"]
    sort_keys = []
    if options.quality != BEST_QUALITY:
        sort_keys.append(f"res:{options.quality}")
    if options.container == "mp4":
        sort_keys.append("ext:mp4:m4a")
    args = ["-f", "bv*+ba/b"]
    if sort_keys:
        args += ["-S", ",".join(sort_keys)]
    return [*args, "--merge-output-format", options.container, "--remux-video", options.container]


def home_args(home: str) -> list[str]:
    return ["-P", f"home:{home}"]


def output_template(folder: str, filename_template: str) -> str:
    escaped = download_directory(folder).replace("%", "%%")
    return os.path.join(escaped, safe_filename_template(filename_template))


def metadata_guard_args(filename_template: str) -> list[str]:
    fields = directory_fields(safe_filename_template(filename_template)) or ()
    if not fields:
        return []
    return [*PREDICTABLE_SANITIZING, "--replace-in-metadata", ",".join(fields), NAMELESS_VALUE, "_"]


def build_download_command(
    executable: str, url: str, options: DownloadOptions, preferences: Preferences, home: str, markers: OutputMarkers
) -> list[str]:
    command = [
        executable,
        "--newline",
        "--quiet",
        "--progress",
        "--no-colors",
        "--no-playlist",
        "--no-mtime",
        "--trim-filenames",
        "180",
        *markers.arguments(),
        *home_args(home),
        "-o",
        output_template(preferences.folder, preferences.filename_template),
        *metadata_guard_args(preferences.filename_template),
    ]
    command += format_args(options)
    if preferences.embed_metadata:
        command.append("--embed-metadata")
    if preferences.embed_thumbnail:
        command.append("--embed-thumbnail")
    if options.mode == VIDEO:
        if preferences.embed_chapters:
            command.append("--embed-chapters")
        if preferences.subtitles:
            command += ["--write-subs", "--sub-langs", safe_subtitle_languages(preferences.subtitle_languages)]
            command.append("--embed-subs")
    command += cookie_args(preferences.cookies_browser)
    return [*command, "--", url]


def build_analyze_command(
    executable: str, url: str, include_playlist: bool, cookies_browser: str, home: str
) -> list[str]:
    command = [executable, "-J", "--flat-playlist", "--no-colors", "--playlist-end", str(PLAYLIST_LIMIT)]
    command += home_args(home)
    if not include_playlist:
        command.append("--no-playlist")
    command += cookie_args(cookies_browser)
    return [*command, "--", url]
