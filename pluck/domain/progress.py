from __future__ import annotations

from dataclasses import dataclass

from pluck.domain.formatting import format_bytes, format_duration, format_speed
from pluck.domain.media import MISSING, has_codec, video_share
from pluck.domain.options import AUDIO


@dataclass(frozen=True)
class ProgressUpdate:
    status: str
    downloaded_bytes: int | None
    total_bytes: int | None
    speed: float | None
    eta: int | None
    fragment_index: int | None
    fragment_count: int | None
    format_id: str
    vcodec: str
    acodec: str

    @property
    def video_only(self) -> bool:
        return has_codec(self.vcodec) and self.acodec == "none"

    @property
    def audio_only(self) -> bool:
        return self.vcodec == "none"

    @property
    def auxiliary(self) -> bool:
        return self.format_id in MISSING and not has_codec(self.vcodec) and not has_codec(self.acodec)

    @property
    def fraction(self) -> float | None:
        if self.status == "finished":
            return 1.0
        if self.total_bytes and self.downloaded_bytes is not None:
            return min(self.downloaded_bytes / self.total_bytes, 1.0)
        if self.fragment_count and self.fragment_index is not None:
            return min(self.fragment_index / self.fragment_count, 1.0)
        return None


def describe_transfer(update: ProgressUpdate, eta: int | None = None) -> str:
    parts = []
    if update.downloaded_bytes is not None:
        done = format_bytes(update.downloaded_bytes) or "0 B"
        total = format_bytes(update.total_bytes)
        parts.append(f"{done} de {total}" if total else done)
    if update.status == "downloading" and update.speed:
        parts.append(format_speed(update.speed))
        if eta is not None:
            parts.append(f"faltam {format_duration(eta)}")
    return " · ".join(parts)


@dataclass(frozen=True)
class ProgressSnapshot:
    fraction: float | None
    stage: str
    detail: str
    speed: float


class ProgressTracker:
    def __init__(self, mode: str, expected_sizes: list[int]):
        self._mode = mode
        self._expected_sizes = list(expected_sizes)
        self._video_share = video_share(expected_sizes)
        self._weights: dict[str, float] = {}
        self._seen_video_stream = False
        self._seen_audio_stream = False
        self._shown: float | None = None

    def _weight_for(self, update: ProgressUpdate) -> float:
        if self._mode == AUDIO:
            return 1.0
        if update.video_only:
            self._seen_video_stream = True
            return self._video_share
        if update.audio_only and self._seen_video_stream:
            return 1.0 - self._video_share
        return 1.0

    def _stage_label(self, update: ProgressUpdate) -> str:
        if update.auxiliary:
            return "Baixando legendas"
        if self._mode == AUDIO or update.audio_only:
            return "Baixando áudio"
        if update.video_only:
            return "Baixando vídeo"
        return "Baixando"

    def _remaining_after(self, update: ProgressUpdate) -> int:
        if self._mode == AUDIO or not update.video_only or self._seen_audio_stream or len(self._expected_sizes) != 2:
            return 0
        return max(self._expected_sizes[1], 0)

    def _eta(self, update: ProgressUpdate) -> int | None:
        if update.eta is None or not update.speed or update.speed <= 0:
            return None
        return update.eta + round(self._remaining_after(update) / update.speed)

    def _settle(self, fraction: float | None) -> float | None:
        if fraction is not None:
            self._shown = fraction if self._shown is None else max(self._shown, fraction)
        return self._shown

    def _overall(self, update: ProgressUpdate) -> float | None:
        if update.auxiliary:
            return None
        if update.audio_only:
            self._seen_audio_stream = True
        if update.format_id not in self._weights:
            self._weights[update.format_id] = self._weight_for(update)
        stream_ids = list(self._weights)
        position = stream_ids.index(update.format_id)
        base = 0.0 if self._mode == AUDIO else sum(self._weights[i] for i in stream_ids[:position])
        fraction = update.fraction
        return None if fraction is None else min(base + self._weights[update.format_id] * fraction, 1.0)

    def on_download(self, update: ProgressUpdate) -> ProgressSnapshot:
        overall = self._settle(self._overall(update))
        speed = (update.speed or 0.0) if update.status == "downloading" else 0.0
        return ProgressSnapshot(overall, self._stage_label(update), describe_transfer(update, self._eta(update)), speed)

    def on_postprocess(self, label: str) -> ProgressSnapshot:
        return ProgressSnapshot(self._shown, label, "", 0.0)
