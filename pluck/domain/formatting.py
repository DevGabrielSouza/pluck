from __future__ import annotations

import math
import os
from datetime import date

BYTE_UNITS = ("B", "KB", "MB", "GB", "TB")


def _decimal(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_bytes(value: float | None) -> str:
    if value is None or not math.isfinite(value) or value <= 0:
        return ""
    size = float(value)
    unit_index = 0
    while size >= 1024 and unit_index < len(BYTE_UNITS) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{_decimal(size, 0 if size >= 100 else 1)} {BYTE_UNITS[unit_index]}"


def format_speed(bytes_per_second: float | None) -> str:
    text = format_bytes(bytes_per_second)
    return f"{text}/s" if text else ""


def format_duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return ""
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_count(value: int | None) -> str:
    if value is None or value < 0:
        return ""
    for threshold, suffix in ((1_000_000_000, "bi"), (1_000_000, "mi"), (1_000, "mil")):
        if value >= threshold:
            scaled = value / threshold
            return f"{_decimal(scaled, 0 if scaled >= 100 else 1)} {suffix}".replace(",0 ", " ")
    return str(value)


def format_views(value: int | None) -> str:
    if value is None:
        return ""
    if value == 1:
        return "1 visualização"
    return f"{format_count(value)} visualizações"


def format_upload_date(raw: str | None) -> str:
    if not raw or len(raw) != 8 or not raw.isdigit():
        return ""
    try:
        parsed = date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
    except ValueError:
        return ""
    return parsed.strftime("%d/%m/%Y")


def short_path(path: str) -> str:
    home = os.path.expanduser("~")
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home) :]
    return path
