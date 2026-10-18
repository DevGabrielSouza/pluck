from __future__ import annotations

from pathlib import Path
from typing import Any

from pluck.domain.options import (
    AUDIO,
    BEST_QUALITY,
    DownloadOptions,
)

PLAYABLE_EXTENSIONS = frozenset(
    {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".3gp", ".ts", ".mp3", ".m4a", ".opus", ".ogg", ".oga"}
    | {".wav", ".flac", ".aac", ".weba"}
)


def is_playable_file(path: str) -> bool:
    return Path(path).suffix.lower() in PLAYABLE_EXTENSIONS


STANDARD_SIDES = (4320, 2160, 1440, 1080, 720, 480, 360, 240, 144)


MP3_V0_KBPS = 245


VIDEO_SHARE_WITHOUT_SIZES = 0.9


MISSING = {"NA", "None", ""}


def has_codec(codec: str) -> bool:
    return codec not in MISSING and codec != "none"


def short_side(fmt: dict[str, Any]) -> int | None:
    width, height = fmt.get("width"), fmt.get("height")
    side = min(width, height) if width and height else height
    if not side:
        return None
    for standard in STANDARD_SIDES:
        if standard * 0.92 <= side <= standard * 1.08:
            return standard
    return int(side)


def _is_video(fmt: dict[str, Any]) -> bool:
    return has_codec(str(fmt.get("vcodec") or "NA")) and short_side(fmt) is not None


def _is_audio_only(fmt: dict[str, Any]) -> bool:
    return fmt.get("vcodec") == "none" and has_codec(str(fmt.get("acodec") or "NA"))


def _has_audio(fmt: dict[str, Any]) -> bool:
    return has_codec(str(fmt.get("acodec") or "NA"))


def _bitrate(fmt: dict[str, Any]) -> float:
    return float(fmt.get("tbr") or fmt.get("abr") or fmt.get("vbr") or 0)


def format_size(fmt: dict[str, Any], duration: float | None) -> int:
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return int(size)
    bitrate = _bitrate(fmt)
    if bitrate and duration:
        return int(bitrate * 125 * duration)
    return 0


def pick_video_format(formats: list[dict[str, Any]], quality: int, container: str) -> dict[str, Any] | None:
    videos = [fmt for fmt in formats if _is_video(fmt)]
    if not videos:
        return None
    within_limit = [fmt for fmt in videos if quality == BEST_QUALITY or (short_side(fmt) or 0) <= quality]
    if within_limit:
        target_side = max(short_side(fmt) or 0 for fmt in within_limit)
    else:
        target_side = min(short_side(fmt) or 0 for fmt in videos)
        within_limit = videos
    tier = [fmt for fmt in within_limit if short_side(fmt) == target_side]
    if container == "mp4":
        tier = [fmt for fmt in tier if fmt.get("ext") == "mp4"] or tier
    return max(tier, key=_bitrate)


def pick_audio_format(formats: list[dict[str, Any]], prefer_m4a: bool) -> dict[str, Any] | None:
    audios = [fmt for fmt in formats if _is_audio_only(fmt)]
    if not audios:
        return None
    if prefer_m4a:
        audios = [fmt for fmt in audios if fmt.get("ext") == "m4a"] or audios
    return max(audios, key=_bitrate)


def stage_sizes(formats: list[dict[str, Any]], duration: float | None, options: DownloadOptions) -> list[int]:
    if options.mode == AUDIO:
        audio = pick_audio_format(formats, prefer_m4a=options.audio_format == "m4a")
        if audio is None:
            fallback = max((fmt for fmt in formats if _has_audio(fmt)), key=_bitrate, default=None)
            return [format_size(fallback, duration)] if fallback else []
        return [format_size(audio, duration)]
    video = pick_video_format(formats, options.quality, options.container)
    if video is None:
        return []
    if _has_audio(video):
        return [format_size(video, duration)]
    audio = pick_audio_format(formats, prefer_m4a=options.container == "mp4")
    return [format_size(video, duration), format_size(audio, duration) if audio else 0]


def output_size(formats: list[dict[str, Any]], duration: float | None, options: DownloadOptions) -> int:
    sizes = stage_sizes(formats, duration, options)
    if options.mode == AUDIO and options.audio_format == "mp3" and duration:
        return int(MP3_V0_KBPS * 125 * duration)
    return sum(sizes) if sizes and all(sizes) else 0


def video_share(sizes: list[int]) -> float:
    if len(sizes) == 2 and sizes[0] > 0 and sizes[1] > 0:
        return sizes[0] / (sizes[0] + sizes[1])
    return VIDEO_SHARE_WITHOUT_SIZES


def available_qualities(formats: list[dict[str, Any]]) -> list[int]:
    sides = sorted({side for fmt in formats if _is_video(fmt) and (side := short_side(fmt)) is not None}, reverse=True)
    return [BEST_QUALITY, *[side for side in sides if side >= 144][:7]]


def pick_default_quality(qualities: list[int], preferred: int) -> int:
    if preferred == BEST_QUALITY or preferred in qualities:
        return preferred
    lower = [quality for quality in qualities if quality != BEST_QUALITY and quality <= preferred]
    return max(lower) if lower else BEST_QUALITY


def entry_thumbnail(entry: dict[str, Any]) -> str:
    if entry.get("ie_key") == "Youtube" and entry.get("id"):
        return f"https://i.ytimg.com/vi/{entry['id']}/mqdefault.jpg"
    thumbnails = entry.get("thumbnails") or []
    if thumbnails:
        return str(thumbnails[-1].get("url") or "")
    return str(entry.get("thumbnail") or "")


def entry_url(entry: dict[str, Any]) -> str:
    url = entry.get("url") or entry.get("webpage_url") or ""
    if not url.startswith("http") and entry.get("ie_key") == "Youtube" and entry.get("id"):
        return f"https://www.youtube.com/watch?v={entry['id']}"
    return url


def nested_playlist_url(data: dict[str, Any]) -> str | None:
    entries = data.get("entries") or []
    if data.get("_type") == "playlist" and entries and all(e.get("ie_key") == "YoutubeTab" for e in entries):
        return entry_url(entries[0]) or None
    return None
