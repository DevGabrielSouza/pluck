from __future__ import annotations

import re

MINIMUM_VERSION = (2026, 7, 4)
MINIMUM_VERSION_TEXT = "2026.07.04"
VERSION_PATTERN = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})")


def parse_version(text: str) -> tuple[int, int, int] | None:
    match = VERSION_PATTERN.match(text.strip())
    if match is None:
        return None
    year, month, day = (int(group) for group in match.groups())
    return year, month, day


def is_outdated(text: str) -> bool:
    version = parse_version(text)
    return version is not None and version < MINIMUM_VERSION
