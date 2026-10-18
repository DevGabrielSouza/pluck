from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pluck.domain.options import DownloadOptions, Preferences
from pluck.domain.urls import safe_image_url


class Status(StrEnum):
    QUEUED = "queued"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"


LEGACY_STATUSES = {"processing": Status.POSTPROCESSING, "done": Status.COMPLETED, "error": Status.FAILED}


RUNNING = {Status.RESOLVING, Status.DOWNLOADING, Status.POSTPROCESSING}


PENDING = {Status.QUEUED, *RUNNING}


RETRYABLE = {Status.FAILED, Status.CANCELED, Status.INTERRUPTED}


STATUS_GROUPS: dict[str, set[Status]] = {
    "all": set(Status),
    "active": PENDING,
    "completed": {Status.COMPLETED},
    "failed": {Status.FAILED},
}


ENDINGS = frozenset({Status.COMPLETED, Status.FAILED, Status.CANCELED, Status.INTERRUPTED})


TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.QUEUED: frozenset({Status.RESOLVING, Status.FAILED, Status.CANCELED, Status.INTERRUPTED}),
    Status.RESOLVING: frozenset({Status.DOWNLOADING, Status.POSTPROCESSING, *ENDINGS}),
    Status.DOWNLOADING: frozenset({Status.POSTPROCESSING, *ENDINGS}),
    Status.POSTPROCESSING: frozenset({Status.DOWNLOADING, *ENDINGS}),
    Status.COMPLETED: frozenset(),
    Status.FAILED: frozenset({Status.QUEUED}),
    Status.CANCELED: frozenset({Status.QUEUED}),
    Status.INTERRUPTED: frozenset({Status.QUEUED}),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: Status, target: Status):
        super().__init__(f"cannot move a download from {current} to {target}")
        self.current = current
        self.target = target


def can_transition(current: Status, target: Status) -> bool:
    return target in TRANSITIONS[current]


STAGE_LABELS = {
    Status.QUEUED: "Na fila",
    Status.RESOLVING: "Preparando",
    Status.DOWNLOADING: "Baixando",
    Status.POSTPROCESSING: "Processando",
    Status.COMPLETED: "Concluído",
    Status.FAILED: "Falhou",
    Status.CANCELED: "Cancelado",
    Status.INTERRUPTED: "Interrompido",
}


@dataclass
class DownloadJob:
    url: str
    title: str
    options: DownloadOptions
    preferences: Preferences
    channel: str = ""
    thumbnail: str = ""
    duration: float = 0
    expected_sizes: list[int] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: Status = Status.QUEUED
    progress: float | None = 0.0
    stage: str = STAGE_LABELS[Status.QUEUED]
    detail: str = ""
    speed: float = 0.0
    error: str = ""
    error_detail: str = ""
    file_path: str = ""
    created_at: float = field(default_factory=time.time)
    finished_at: float = 0

    @property
    def folder(self) -> str:
        return self.preferences.folder

    def transition(self, target: Status) -> None:
        if not can_transition(self.status, target):
            raise InvalidTransitionError(self.status, target)
        self.status = target
        self.stage = STAGE_LABELS[target]
        self.speed = 0.0
        if target in (Status.QUEUED, Status.RESOLVING):
            self.progress = 0.0 if target == Status.QUEUED else None
            self.detail = ""
            self.error = ""
            self.error_detail = ""
            self.finished_at = 0
        if target == Status.RESOLVING:
            self.file_path = ""
        elif target in ENDINGS:
            self.finished_at = time.time()

    def to_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "channel": self.channel,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "options": self.options.to_dict(),
            "preferences": self.preferences.to_dict(),
            "expectedSizes": list(self.expected_sizes),
            "status": self.status.value,
            "progress": self.progress,
            "detail": self.detail,
            "error": self.error,
            "errorDetail": self.error_detail,
            "filePath": self.file_path,
            "createdAt": self.created_at,
            "finishedAt": self.finished_at,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> DownloadJob | None:
        try:
            raw_status = record.get("status", Status.QUEUED)
            status = LEGACY_STATUSES.get(raw_status) or Status(raw_status)
            job = cls(
                url=str(record["url"]),
                title=str(record.get("title") or record["url"]),
                options=DownloadOptions.from_dict(record.get("options") or {}),
                preferences=Preferences.from_dict(record.get("preferences") or {}),
                channel=str(record.get("channel") or ""),
                thumbnail=safe_image_url(str(record.get("thumbnail") or "")),
                duration=float(record.get("duration") or 0),
                expected_sizes=[int(size) for size in record.get("expectedSizes") or []],
                id=str(record.get("id") or uuid.uuid4().hex),
                status=status,
                progress=record.get("progress") if isinstance(record.get("progress"), (int, float)) else 0.0,
                detail=str(record.get("detail") or ""),
                error=str(record.get("error") or ""),
                error_detail=str(record.get("errorDetail") or ""),
                file_path=str(record.get("filePath") or ""),
                created_at=float(record.get("createdAt") or time.time()),
                finished_at=float(record.get("finishedAt") or 0),
            )
        except (KeyError, TypeError, ValueError):
            return None
        job.stage = STAGE_LABELS[job.status]
        if job.status in PENDING:
            job.transition(Status.INTERRUPTED)
        return job
