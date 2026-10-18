from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pluck.domain.jobs import DownloadJob
from pluck.domain.progress import ProgressUpdate


@dataclass(frozen=True)
class Failure:
    message: str
    detail: str
    transient: bool = False
    rate_limited: bool = False


class JsonStore(Protocol):
    def read(self) -> Any: ...

    def write(self, payload: Any) -> None: ...


class JobList(Protocol):
    @property
    def jobs(self) -> Sequence[DownloadJob]: ...

    def reset_with(self, jobs: list[DownloadJob]) -> None: ...

    def prepend(self, jobs: list[DownloadJob]) -> None: ...

    def refresh(self, job: DownloadJob) -> None: ...

    def remove(self, job: DownloadJob) -> None: ...


@dataclass(frozen=True)
class RunOutcome:
    failure: Failure | None = None
    launched: bool = True
    file_size: int = 0
    file_reported: bool = False


class RunListener(Protocol):
    def on_progress(self, job_id: str, update: ProgressUpdate) -> None: ...

    def on_postprocess(self, job_id: str, label: str) -> None: ...

    def on_file(self, job_id: str, path: str) -> None: ...

    def on_exit(self, job_id: str, outcome: RunOutcome) -> None: ...


class DownloadRun(Protocol):
    def start(self) -> None: ...

    def interrupt(self) -> None: ...

    def kill(self) -> None: ...


class DownloadRunner(Protocol):
    def prepare(self, job: DownloadJob, listener: RunListener) -> DownloadRun: ...


ProbeResult = dict[str, Any] | Failure


class Probe(Protocol):
    def start(self) -> None: ...

    def cancel(self) -> None: ...


class MediaProbe(Protocol):
    def prepare(
        self, url: str, include_playlist: bool, cookies_browser: str, on_done: Callable[[ProbeResult], None]
    ) -> Probe: ...


class DesktopShell(Protocol):
    def probe_tools(self, on_version: Callable[[str, str], None]) -> None: ...

    def show_item(self, path: str) -> bool: ...
