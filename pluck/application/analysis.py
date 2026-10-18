from __future__ import annotations

from typing import Protocol

from pluck.application.ports import Failure, MediaProbe, Probe, ProbeResult
from pluck.application.settings import SettingsStore
from pluck.domain.media import nested_playlist_url
from pluck.domain.urls import looks_like_url, normalize_url

INVALID_URL_MESSAGE = "Isso não parece um link válido."


class AnalysisListener(Protocol):
    def on_analysis_started(self) -> None: ...

    def on_analysis_finished(self, result: ProbeResult) -> None: ...


class MediaAnalysis:
    def __init__(self, probe: MediaProbe, settings: SettingsStore, listener: AnalysisListener):
        self._probe = probe
        self._settings = settings
        self._listener = listener
        self._running: Probe | None = None
        self.url = ""
        self.include_playlist = False

    def start(self, text: str, include_playlist: bool) -> Failure | None:
        self.cancel()
        self.url = normalize_url(text)
        if not looks_like_url(self.url):
            return Failure(INVALID_URL_MESSAGE, text.strip())
        self.include_playlist = include_playlist
        self._run(self.url)
        return None

    def cancel(self) -> bool:
        running, self._running = self._running, None
        if running is None:
            return False
        running.cancel()
        return True

    def clear(self) -> None:
        self.cancel()
        self.url = ""

    def _run(self, url: str) -> None:
        probe = self._probe.prepare(
            url,
            self.include_playlist,
            self._settings.cookies_browser,
            lambda result: self._on_done(probe, result),
        )
        self._running = probe
        self._listener.on_analysis_started()
        probe.start()

    def _on_done(self, probe: Probe, result: ProbeResult) -> None:
        if probe is not self._running:
            return
        self._running = None
        if not isinstance(result, Failure) and (nested := nested_playlist_url(result)) is not None:
            self.include_playlist = True
            self._run(nested)
            return
        self._listener.on_analysis_finished(result)
