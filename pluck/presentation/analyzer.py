from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from pluck.application.analysis import MediaAnalysis
from pluck.application.ports import Failure, MediaProbe, ProbeResult
from pluck.domain.media import stage_sizes
from pluck.domain.options import DownloadOptions
from pluck.presentation.media_view import describe_media
from pluck.presentation.settings import Settings

IDLE = "idle"
LOADING = "loading"
READY = "ready"
FAILED = "error"


class Analyzer(QObject):
    stateChanged = Signal()

    def __init__(self, settings: Settings, probe: MediaProbe, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._analysis = MediaAnalysis(probe, settings.store, self)
        self._state = IDLE
        self._result: dict[str, Any] = {}
        self._raw: dict[str, Any] = {}
        self._error = ""
        self._error_detail = ""

    def _get_state(self) -> str:
        return self._state

    def _get_url(self) -> str:
        return self._analysis.url

    def _get_result(self) -> dict[str, Any]:
        return self._result

    def _get_error(self) -> str:
        return self._error

    def _get_error_detail(self) -> str:
        return self._error_detail

    state = Property(str, _get_state, notify=stateChanged)
    url = Property(str, _get_url, notify=stateChanged)
    result = Property(dict, _get_result, notify=stateChanged)
    errorText = Property(str, _get_error, notify=stateChanged)
    errorDetail = Property(str, _get_error_detail, notify=stateChanged)

    def _set_state(self, state: str) -> None:
        self._state = state
        self.stateChanged.emit()

    @Slot(str)
    @Slot(str, bool)
    def analyze(self, text: str, include_playlist: bool = False) -> None:
        self.cancel()
        self._result = {}
        self._raw = {}
        if (failure := self._analysis.start(text, include_playlist)) is not None:
            self._show_failure(failure)

    @Slot()
    def retry(self) -> None:
        self.analyze(self._analysis.url, self._analysis.include_playlist)

    @Slot()
    def cancel(self) -> None:
        self._analysis.cancel()
        if self._state == LOADING:
            self._set_state(IDLE)

    @Slot()
    def clear(self) -> None:
        self._analysis.clear()
        self._result = {}
        self._raw = {}
        self._error = ""
        self._error_detail = ""
        self._set_state(IDLE)

    def on_analysis_started(self) -> None:
        self._error = ""
        self._error_detail = ""
        self._set_state(LOADING)

    def on_analysis_finished(self, result: ProbeResult) -> None:
        if isinstance(result, Failure):
            self._show_failure(result)
            return
        self._raw = result
        self._result = describe_media(result, self._analysis.url, self._settings.store.default_quality)
        self._set_state(READY)

    def _show_failure(self, failure: Failure) -> None:
        self._error = failure.message
        self._error_detail = failure.detail
        self._set_state(FAILED)

    @Slot(str, int, str, str, result="QVariantList")
    def expectedSizes(self, mode: str, quality: int, container: str, audio_format: str) -> list[int]:
        if not self._raw or self._raw.get("_type") == "playlist":
            return []
        options = DownloadOptions.from_dict(
            {"mode": mode, "quality": quality, "container": container, "audioFormat": audio_format}
        )
        return stage_sizes(self._raw.get("formats") or [], self._raw.get("duration"), options)
