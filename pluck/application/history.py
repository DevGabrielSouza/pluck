from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from pluck.domain.jobs import PENDING, DownloadJob

HISTORY_VERSION = 2


HISTORY_LIMIT = 500


def decode_history(payload: Any) -> list[DownloadJob]:
    records = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return []
    jobs = [job for job in map(DownloadJob.from_record, records) if job is not None]
    seen: set[str] = set()
    for job in jobs:
        if job.id in seen:
            job.id = uuid.uuid4().hex
        seen.add(job.id)
    return jobs


def encode_history(jobs: Sequence[DownloadJob]) -> dict[str, Any]:
    return {"version": HISTORY_VERSION, "jobs": [job.to_record() for job in jobs]}


def beyond_limit(jobs: Sequence[DownloadJob], limit: int = HISTORY_LIMIT) -> list[DownloadJob]:
    excess = len(jobs) - limit
    if excess <= 0:
        return []
    return [job for job in reversed(jobs) if job.status not in PENDING][:excess]
