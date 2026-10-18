from __future__ import annotations

import random
import time
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from typing import Protocol

from pluck.application.history import beyond_limit, decode_history, encode_history
from pluck.application.ports import DownloadRun, DownloadRunner, Failure, JobList, JsonStore, RunOutcome
from pluck.application.settings import SettingsStore
from pluck.domain.formatting import format_bytes
from pluck.domain.jobs import PENDING, RETRYABLE, RUNNING, DownloadJob, Status
from pluck.domain.options import DownloadOptions, InvalidFolderError
from pluck.domain.progress import ProgressSnapshot, ProgressTracker, ProgressUpdate
from pluck.domain.retry import MAX_AUTOMATIC_RETRIES, retry_delay
from pluck.domain.urls import is_downloadable_url, safe_image_url

INVALID_FOLDER_MESSAGE = "A pasta de destino é inválida. Escolha outra em Configurações."


CANCELING_STAGE = "Cancelando"


@dataclass(frozen=True)
class JobRequest:
    url: str
    title: str
    channel: str = ""
    thumbnail: str = ""
    duration: float = 0
    expected_sizes: tuple[int, ...] = ()


class QueueListener(Protocol):
    def on_counts_changed(self) -> None: ...

    def on_statuses_settled(self) -> None: ...

    def on_job_finished(self, job: DownloadJob) -> None: ...


@dataclass
class ActiveRun:
    handle: DownloadRun
    tracker: ProgressTracker
    url: str
    cancel_requested: bool = False


def retry_stage(attempt: int) -> str:
    return f"Nova tentativa ({attempt} de {MAX_AUTOMATIC_RETRIES})"


class DownloadQueue:
    def __init__(
        self,
        jobs: JobList,
        runner: DownloadRunner,
        settings: SettingsStore,
        history: JsonStore,
        listener: QueueListener,
        clock: Callable[[], float] = time.monotonic,
        jitter: Callable[[], float] = lambda: random.uniform(-1.0, 1.0),
    ):
        self._jobs = jobs
        self._runner = runner
        self._settings = settings
        self._history = history
        self._listener = listener
        self._clock = clock
        self._jitter = jitter
        self._runs: dict[str, ActiveRun] = {}
        self._dirty_ids: set[str] = set()
        self._automatic_retries: dict[str, int] = {}
        self._retry_at: dict[str, float] = {}
        self._closing = False
        loaded = decode_history(history.read())
        self.interrupted_at_startup = sum(1 for job in loaded if job.status == Status.INTERRUPTED)
        jobs.reset_with(loaded)

    @property
    def has_active_runs(self) -> bool:
        return bool(self._runs)

    @property
    def total(self) -> int:
        return len(self._jobs.jobs)

    @property
    def total_speed(self) -> float:
        return sum(job.speed for job in self._jobs.jobs if job.status == Status.DOWNLOADING)

    def count(self, statuses: Collection[Status]) -> int:
        return sum(1 for job in self._jobs.jobs if job.status in statuses)

    def find(self, job_id: str) -> DownloadJob | None:
        return next((job for job in self._jobs.jobs if job.id == job_id), None)

    def next_retry_delay(self) -> float | None:
        now = self._clock()
        upcoming = [moment - now for moment in self._retry_at.values() if moment > now]
        return min(upcoming) if upcoming else None

    def enqueue(self, requests: Sequence[JobRequest], options: DownloadOptions) -> int:
        pending = {(job.url, job.options) for job in self._jobs.jobs if job.status in PENDING}
        now = time.time()
        jobs = []
        for position, request in enumerate(requests):
            if not is_downloadable_url(request.url) or (request.url, options) in pending:
                continue
            pending.add((request.url, options))
            jobs.append(
                DownloadJob(
                    url=request.url,
                    title=request.title,
                    channel=request.channel,
                    thumbnail=safe_image_url(request.thumbnail),
                    duration=request.duration,
                    expected_sizes=list(request.expected_sizes),
                    options=options,
                    preferences=self._settings.preferences(),
                    created_at=now + position * 1e-6,
                )
            )
        self._jobs.prepend(jobs)
        self._after_status_change()
        return len(jobs)

    def cancel(self, job_id: str) -> None:
        job = self.find(job_id)
        if job is None:
            return
        if job.status == Status.QUEUED:
            self._forget(job_id)
            self._mark(job, Status.CANCELED)
            self._after_status_change()
            return
        run = self._runs.get(job_id)
        if run is None or run.cancel_requested:
            return
        run.cancel_requested = True
        self._dirty_ids.discard(job_id)
        job.stage = CANCELING_STAGE
        job.speed = 0.0
        self._jobs.refresh(job)
        self._listener.on_counts_changed()
        run.handle.interrupt()

    def retry(self, job_id: str) -> None:
        job = self.find(job_id)
        if job is None or job.status not in RETRYABLE:
            return
        self._requeue(job)
        self._after_status_change()

    def retry_interrupted(self) -> None:
        self._retry_all({Status.INTERRUPTED})

    def retry_failed(self) -> None:
        self._retry_all({Status.FAILED})

    def remove(self, job_id: str) -> None:
        job = self.find(job_id)
        if job is None or job.status in RUNNING:
            return
        self._forget(job_id)
        self._jobs.remove(job)
        self._after_status_change()

    def clear_finished(self) -> None:
        for job in [job for job in self._jobs.jobs if job.status == Status.COMPLETED]:
            self._forget(job.id)
            self._jobs.remove(job)
        self._after_status_change()

    def save(self) -> int:
        trimmed = beyond_limit(self._jobs.jobs)
        for job in trimmed:
            self._forget(job.id)
            self._jobs.remove(job)
        self._history.write(encode_history(self._jobs.jobs))
        return len(trimmed)

    def shutdown(self) -> None:
        self._closing = True
        self.save()
        for run in list(self._runs.values()):
            run.handle.kill()

    def schedule(self) -> None:
        if self._closing:
            return
        now = self._clock()
        queued = sorted(
            (job for job in self._jobs.jobs if job.status == Status.QUEUED),
            key=lambda job: job.created_at,
        )
        for job in queued:
            if len(self._runs) >= self._settings.max_concurrent:
                break
            busy_urls = {run.url for run in self._runs.values()}
            if job.status != Status.QUEUED or job.url in busy_urls or self._retry_at.get(job.id, now) > now:
                continue
            self._start(job)

    def flush_progress(self) -> None:
        for job_id in self._dirty_ids:
            job = self.find(job_id)
            if job is not None:
                self._jobs.refresh(job)
        self._dirty_ids.clear()

    def on_progress(self, job_id: str, update: ProgressUpdate) -> None:
        if (active := self._active(job_id)) is None:
            return
        job, run = active
        if job.status == Status.POSTPROCESSING and update.status != "downloading":
            return
        if job.status != Status.DOWNLOADING:
            self._mark(job, Status.DOWNLOADING)
            self._listener.on_counts_changed()
        self._apply(job, run.tracker.on_download(update))

    def on_postprocess(self, job_id: str, label: str) -> None:
        if (active := self._active(job_id)) is None:
            return
        job, run = active
        if job.status != Status.POSTPROCESSING:
            self._mark(job, Status.POSTPROCESSING)
            self._listener.on_counts_changed()
        self._apply(job, run.tracker.on_postprocess(label))

    def on_file(self, job_id: str, path: str) -> None:
        if not self._closing and job_id in self._runs and (job := self.find(job_id)) is not None:
            job.file_path = path

    def on_exit(self, job_id: str, outcome: RunOutcome) -> None:
        if self._closing or (run := self._runs.pop(job_id, None)) is None:
            return
        self._dirty_ids.discard(job_id)
        job = self.find(job_id)
        if job is None:
            self.schedule()
            return
        finished = self._settle(job, run, outcome)
        self._jobs.refresh(job)
        self._after_status_change()
        if finished:
            self._listener.on_job_finished(job)

    def _start(self, job: DownloadJob) -> None:
        try:
            handle = self._runner.prepare(job, self)
        except InvalidFolderError as error:
            self._reject_invalid_folder(job, str(error))
            return
        self._retry_at.pop(job.id, None)
        self._runs[job.id] = ActiveRun(handle, ProgressTracker(job.options.mode, job.expected_sizes), job.url)
        self._mark(job, Status.RESOLVING)
        self._listener.on_counts_changed()
        handle.start()

    def _reject_invalid_folder(self, job: DownloadJob, detail: str) -> None:
        self._forget(job.id)
        self._fail(job, Failure(INVALID_FOLDER_MESSAGE, detail))
        self._listener.on_statuses_settled()
        self._listener.on_job_finished(job)

    def _settle(self, job: DownloadJob, run: ActiveRun, outcome: RunOutcome) -> bool:
        completed = outcome.failure is None and (outcome.file_reported or not run.cancel_requested)
        if run.cancel_requested and not completed:
            self._forget(job.id)
            self._mark(job, Status.CANCELED)
            job.detail = ""
            return True
        if outcome.failure is None:
            self._forget(job.id)
            job.progress = 1.0
            self._mark(job, Status.COMPLETED)
            job.detail = format_bytes(outcome.file_size)
            return True
        self._fail(job, outcome.failure)
        return not self._schedule_automatic_retry(job, outcome.failure)

    def _fail(self, job: DownloadJob, failure: Failure) -> None:
        job.error = failure.message
        job.error_detail = failure.detail
        self._mark(job, Status.FAILED)
        job.detail = ""

    def _schedule_automatic_retry(self, job: DownloadJob, failure: Failure) -> bool:
        attempt = self._automatic_retries.get(job.id, 0) + 1
        if not failure.transient or attempt > MAX_AUTOMATIC_RETRIES:
            self._automatic_retries.pop(job.id, None)
            return False
        self._automatic_retries[job.id] = attempt
        self._retry_at[job.id] = self._clock() + retry_delay(attempt, failure.rate_limited, self._jitter())
        job.transition(Status.QUEUED)
        job.stage = retry_stage(attempt)
        job.detail = failure.message
        return True

    def _active(self, job_id: str) -> tuple[DownloadJob, ActiveRun] | None:
        if self._closing or (run := self._runs.get(job_id)) is None or run.cancel_requested:
            return None
        if (job := self.find(job_id)) is None:
            return None
        return job, run

    def _apply(self, job: DownloadJob, snapshot: ProgressSnapshot) -> None:
        job.progress = snapshot.fraction
        job.stage = snapshot.stage
        job.detail = snapshot.detail
        job.speed = snapshot.speed if job.status == Status.DOWNLOADING else 0.0
        self._dirty_ids.add(job.id)

    def _retry_all(self, statuses: Collection[Status]) -> None:
        for job in self._jobs.jobs:
            if job.status in statuses:
                self._requeue(job)
        self._after_status_change()

    def _requeue(self, job: DownloadJob) -> None:
        self._forget(job.id)
        job.transition(Status.QUEUED)
        job.preferences = self._settings.preferences(job.folder)
        self._jobs.refresh(job)

    def _forget(self, job_id: str) -> None:
        self._automatic_retries.pop(job_id, None)
        self._retry_at.pop(job_id, None)

    def _mark(self, job: DownloadJob, status: Status) -> None:
        job.transition(status)
        self._jobs.refresh(job)

    def _after_status_change(self) -> None:
        self._listener.on_statuses_settled()
        self.schedule()
