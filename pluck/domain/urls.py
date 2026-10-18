from __future__ import annotations

import re
from urllib.parse import ParseResult, parse_qs, urlparse

MAX_URL_LENGTH = 4096


def normalize_url(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    candidate = stripped.split()[0]
    if "://" not in candidate and re.match(r"^[\w-]+(\.[\w-]+)+(/|$|\?)", candidate):
        candidate = "https://" + candidate
    return candidate


def parse_url(url: str) -> ParseResult | None:
    try:
        return urlparse(url)
    except ValueError:
        return None


def looks_like_url(text: str) -> bool:
    url = normalize_url(text)
    parsed = parse_url(url)
    return parsed is not None and is_downloadable_url(url) and "." in parsed.netloc


def is_inside_playlist(url: str) -> bool:
    parsed = parse_url(url)
    if parsed is None:
        return False
    query = parse_qs(parsed.query)
    return "list" in query and ("v" in query or "youtu.be" in parsed.netloc)


def is_downloadable_url(url: str) -> bool:
    if not url or len(url) > MAX_URL_LENGTH or any(character.isspace() or ord(character) < 32 for character in url):
        return False
    parsed = parse_url(url)
    return parsed is not None and parsed.scheme in ("http", "https") and bool(parsed.hostname)


def safe_image_url(url: str) -> str:
    return url if is_downloadable_url(url) else ""
