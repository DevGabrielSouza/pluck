from __future__ import annotations

MAX_AUTOMATIC_RETRIES = 3


RETRY_BASE_SECONDS = 5.0


RATE_LIMIT_BASE_SECONDS = 60.0


RETRY_FACTOR = 3.0


RETRY_JITTER = 0.2


def retry_delay(attempt: int, rate_limited: bool, jitter: float) -> float:
    base = RATE_LIMIT_BASE_SECONDS if rate_limited else RETRY_BASE_SECONDS
    spread = 1 + RETRY_JITTER * max(-1.0, min(jitter, 1.0))
    return base * RETRY_FACTOR ** max(attempt - 1, 0) * spread
