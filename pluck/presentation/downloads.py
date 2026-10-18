from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from pluck.application.downloads import DownloadQueue, JobRequest
from pluck.application.ports import DownloadRunner, JsonStore
from pluck.domain.formatting import format_speed
from pluck.domain.jobs import PENDING, RUNNING, DownloadJob, Status
from pluck.domain.options import DownloadOptions
from pluck.presentation.models import DownloadFilterModel, DownloadListModel
from pluck.presentation.settings import Settings

UI_REFRESH_INTERVAL_MS = 150


SAVE_DELAY_MS = 600


def job_request(entry: dict[str, Any]) -> JobRequest:
    url = str(entry.get("url") or "")
    return JobRequest(
        url=url,
        title=str(entry.get("title") or url),
        channel=str(entry.get("channel") or ""),
        thumbnail=str(entry.get("thumbnail") or ""),
        duration=float(entry.get("duration") or 0),
        expected_sizes=tuple(int(size) for size in entry.get("expectedSizes") or [] if size is not None),
    )


class DownloadManager(QObject):
    countsChanged = Signal()
    speedChanged = Signal()
    jobFinished = Signal(str, str, str)

    def __init__(
        self,
        settings: Settings,
        history: JsonStore,
        runner: DownloadRunner,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._model = DownloadListModel(self)
        self._view = DownloadFilterModel(self._model, self)
        self._total_speed = 0.0
        self._refresh_timer = QTimer(self, interval=UI_REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self._flush_progress)
        self._save_timer = QTimer(self, singleShot=True, interval=SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self.save)
        self._retry_timer = QTimer(self, singleShot=True)
        self._retry_timer.timeout.connect(self._schedule)
        self._queue = DownloadQueue(self._model, runner, settings.store, history, self)
        settings.changed.connect(self._schedule)

    def on_counts_changed(self) -> None:
        self.countsChanged.emit()
        self._sync_refresh_timer()

    def on_statuses_settled(self) -> None:
        self.countsChanged.emit()
        self._update_speed()
        self._save_timer.start()
        self._sync_refresh_timer()
        self._arm_retry_timer()

    def on_job_finished(self, job: DownloadJob) -> None:
        self.jobFinished.emit(job.id, job.title, job.status.value)

    @Slot()
    def save(self) -> None:
        self._save_timer.stop()
        if self._queue.save():
            self.countsChanged.emit()

    def shutdown(self) -> None:
        self._save_timer.stop()
        self._refresh_timer.stop()
        self._retry_timer.stop()
        self._queue.shutdown()

    def _get_view(self) -> QObject:
        return self._view

    def _get_total_count(self) -> int:
        return self._queue.total

    def _get_running_count(self) -> int:
        return self._queue.count(RUNNING)

    def _get_queued_count(self) -> int:
        return self._queue.count({Status.QUEUED})

    def _get_pending_count(self) -> int:
        return self._queue.count(PENDING)

    def _get_completed_count(self) -> int:
        return self._queue.count({Status.COMPLETED})

    def _get_failed_count(self) -> int:
        return self._queue.count({Status.FAILED})

    def _get_interrupted_count(self) -> int:
        return self._queue.count({Status.INTERRUPTED})

    def _get_total_speed_text(self) -> str:
        return format_speed(self._total_speed)

    def _get_startup_interrupted(self) -> int:
        return self._queue.interrupted_at_startup

    view = Property(QObject, _get_view, constant=True)
    totalCount = Property(int, _get_total_count, notify=countsChanged)
    runningCount = Property(int, _get_running_count, notify=countsChanged)
    queuedCount = Property(int, _get_queued_count, notify=countsChanged)
    pendingCount = Property(int, _get_pending_count, notify=countsChanged)
    completedCount = Property(int, _get_completed_count, notify=countsChanged)
    failedCount = Property(int, _get_failed_count, notify=countsChanged)
    interruptedCount = Property(int, _get_interrupted_count, notify=countsChanged)
    totalSpeedText = Property(str, _get_total_speed_text, notify=speedChanged)
    startupInterrupted = Property(int, _get_startup_interrupted, constant=True)

    @Slot("QVariantList", "QVariantMap", result=int)
    def enqueue(self, entries: list[dict[str, Any]], options: dict[str, Any]) -> int:
        return self._queue.enqueue([job_request(entry) for entry in entries], DownloadOptions.from_dict(options))

    @Slot(str)
    def cancel(self, job_id: str) -> None:
        self._queue.cancel(job_id)

    @Slot(str)
    def retry(self, job_id: str) -> None:
        self._queue.retry(job_id)

    @Slot()
    def retryInterrupted(self) -> None:
        self._queue.retry_interrupted()

    @Slot()
    def retryFailed(self) -> None:
        self._queue.retry_failed()

    @Slot(str)
    def remove(self, job_id: str) -> None:
        self._queue.remove(job_id)

    @Slot()
    def clearFinished(self) -> None:
        self._queue.clear_finished()

    @Slot(str, result=str)
    def filePath(self, job_id: str) -> str:
        job = self._queue.find(job_id)
        return job.file_path if job else ""

    @Slot()
    def _schedule(self) -> None:
        self._queue.schedule()
        self._sync_refresh_timer()
        self._arm_retry_timer()

    def _arm_retry_timer(self) -> None:
        delay = self._queue.next_retry_delay()
        if delay is None:
            self._retry_timer.stop()
            return
        self._retry_timer.start(max(1, round(delay * 1000)))

    def _flush_progress(self) -> None:
        self._queue.flush_progress()
        self._update_speed()

    def _update_speed(self) -> None:
        total = self._queue.total_speed
        if total != self._total_speed:
            self._total_speed = total
            self.speedChanged.emit()

    def _sync_refresh_timer(self) -> None:
        if not self._queue.has_active_runs:
            self._refresh_timer.stop()
        elif not self._refresh_timer.isActive():
            self._refresh_timer.start()
