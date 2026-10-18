from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)

from pluck.domain.formatting import format_duration
from pluck.domain.jobs import STATUS_GROUPS, DownloadJob
from pluck.domain.options import AUDIO

ROLE_GETTERS: dict[str, Callable[[DownloadJob], Any]] = {
    "jobId": lambda job: job.id,
    "title": lambda job: job.title,
    "channel": lambda job: job.channel,
    "thumbnail": lambda job: job.thumbnail,
    "url": lambda job: job.url,
    "durationText": lambda job: format_duration(job.duration) if job.duration else "",
    "formatLabel": lambda job: job.options.label,
    "isAudio": lambda job: job.options.mode == AUDIO,
    "status": lambda job: job.status.value,
    "progress": lambda job: -1.0 if job.progress is None else job.progress,
    "stage": lambda job: job.stage,
    "detail": lambda job: job.detail,
    "errorText": lambda job: job.error,
    "errorDetail": lambda job: job.error_detail,
    "filePath": lambda job: job.file_path,
    "folder": lambda job: job.folder,
}


ROLE_NAMES = list(ROLE_GETTERS)


FIRST_ROLE = Qt.ItemDataRole.UserRole.value + 1


class DownloadListModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._jobs: list[DownloadJob] = []

    @property
    def jobs(self) -> list[DownloadJob]:
        return self._jobs

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._jobs)

    def roleNames(self) -> dict[int, QByteArray]:
        return {FIRST_ROLE + offset: QByteArray(name.encode()) for offset, name in enumerate(ROLE_NAMES)}

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._jobs):
            return None
        offset = role - FIRST_ROLE
        if not 0 <= offset < len(ROLE_NAMES):
            return None
        return ROLE_GETTERS[ROLE_NAMES[offset]](self._jobs[index.row()])

    def job_at(self, row: int) -> DownloadJob:
        return self._jobs[row]

    def reset_with(self, jobs: list[DownloadJob]) -> None:
        self.beginResetModel()
        self._jobs = list(jobs)
        self.endResetModel()

    def prepend(self, jobs: list[DownloadJob]) -> None:
        if not jobs:
            return
        self.beginInsertRows(QModelIndex(), 0, len(jobs) - 1)
        self._jobs[0:0] = jobs
        self.endInsertRows()

    def refresh(self, job: DownloadJob) -> None:
        row = self._jobs.index(job)
        index = self.index(row)
        self.dataChanged.emit(index, index)

    def remove(self, job: DownloadJob) -> None:
        row = self._jobs.index(job)
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._jobs[row]
        self.endRemoveRows()


class DownloadFilterModel(QSortFilterProxyModel):
    groupChanged = Signal()

    def __init__(self, source: DownloadListModel, parent: QObject | None = None):
        super().__init__(parent)
        self._group = "all"
        self.setSourceModel(source)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex) -> bool:
        source = self.sourceModel()
        assert isinstance(source, DownloadListModel)
        return source.job_at(source_row).status in STATUS_GROUPS[self._group]

    def _get_group(self) -> str:
        return self._group

    def _set_group(self, group: str) -> None:
        if group == self._group or group not in STATUS_GROUPS:
            return
        self.beginFilterChange()
        self._group = group
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        self.groupChanged.emit()

    group = Property(str, _get_group, _set_group, notify=groupChanged)
