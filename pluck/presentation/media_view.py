from __future__ import annotations

from typing import Any

from pluck.domain.formatting import format_bytes, format_duration, format_upload_date, format_views
from pluck.domain.media import available_qualities, entry_thumbnail, entry_url, output_size, pick_default_quality
from pluck.domain.options import (
    AUDIO,
    AUDIO_FORMAT_LABELS,
    AUDIO_FORMATS,
    BEST_QUALITY,
    VIDEO,
    DownloadOptions,
    quality_label,
)
from pluck.domain.urls import is_inside_playlist, safe_image_url

GENERIC_QUALITIES = (BEST_QUALITY, 2160, 1440, 1080, 720, 480, 360)


def approximate(size: int) -> str:
    return f"≈ {format_bytes(size)}" if size else ""


def quality_choice(value: int, size: int) -> dict[str, Any]:
    return {
        "value": value,
        "label": "Melhor" if value == BEST_QUALITY else quality_label(value),
        "size": size,
        "sizeText": approximate(size),
    }


def audio_choice(audio_format: str, size: int) -> dict[str, Any]:
    return {
        "value": audio_format,
        "label": AUDIO_FORMAT_LABELS[audio_format],
        "size": size,
        "sizeText": approximate(size),
    }


def playlist_entry(entry: dict[str, Any], channel: str) -> dict[str, Any]:
    return {
        "url": entry_url(entry),
        "title": entry.get("title") or entry_url(entry),
        "channel": entry.get("channel") or entry.get("uploader") or channel,
        "duration": entry.get("duration") or 0,
        "durationText": format_duration(entry.get("duration")),
        "thumbnail": safe_image_url(entry_thumbnail(entry)),
    }


def describe_playlist(data: dict[str, Any], base: dict[str, Any], preferred_quality: int) -> dict[str, Any]:
    entries = [playlist_entry(entry, base["channel"]) for entry in data.get("entries") or [] if entry_url(entry)]
    qualities = [quality_choice(value, 0) for value in GENERIC_QUALITIES]
    return base | {
        "thumbnail": entries[0]["thumbnail"] if entries else "",
        "entries": entries,
        "totalCount": data.get("playlist_count") or len(entries),
        "qualities": qualities,
        "defaultQuality": pick_default_quality(list(GENERIC_QUALITIES), preferred_quality),
        "audioFormats": [audio_choice(audio_format, 0) for audio_format in AUDIO_FORMATS],
        "hasVideo": True,
    }


def video_quality_choice(formats: list[dict[str, Any]], duration: float | None, value: int) -> dict[str, Any]:
    size_mkv = output_size(formats, duration, DownloadOptions(VIDEO, value, "mkv"))
    return quality_choice(value, output_size(formats, duration, DownloadOptions(VIDEO, value, "mp4"))) | {
        "sizeMkv": size_mkv,
        "sizeMkvText": approximate(size_mkv),
    }


def describe_video(
    data: dict[str, Any], base: dict[str, Any], source_url: str, preferred_quality: int
) -> dict[str, Any]:
    duration = data.get("duration")
    formats = data.get("formats") or []
    quality_values = available_qualities(formats)
    return base | {
        "thumbnail": safe_image_url(str(data.get("thumbnail") or "")),
        "duration": duration or 0,
        "durationText": format_duration(duration),
        "viewsText": format_views(data.get("view_count")),
        "dateText": format_upload_date(data.get("upload_date")),
        "isLive": bool(data.get("is_live")),
        "partOfPlaylist": is_inside_playlist(source_url),
        "qualities": [video_quality_choice(formats, duration, value) for value in quality_values],
        "defaultQuality": pick_default_quality(quality_values, preferred_quality),
        "audioFormats": [
            audio_choice(
                audio_format, output_size(formats, duration, DownloadOptions(AUDIO, audio_format=audio_format))
            )
            for audio_format in AUDIO_FORMATS
        ],
        "hasVideo": len(quality_values) > 1 or not formats,
        "entries": [],
        "totalCount": 1,
    }


def describe_media(data: dict[str, Any], source_url: str, preferred_quality: int) -> dict[str, Any]:
    is_playlist = data.get("_type") == "playlist"
    base = {
        "kind": "playlist" if is_playlist else "video",
        "url": data.get("webpage_url") or source_url,
        "title": data.get("title") or source_url,
        "channel": data.get("channel") or data.get("uploader") or "",
        "extractor": data.get("extractor_key") or "",
    }
    if is_playlist:
        return describe_playlist(data, base, preferred_quality)
    return describe_video(data, base, source_url, preferred_quality)
