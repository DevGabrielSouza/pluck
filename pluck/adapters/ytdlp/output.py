from __future__ import annotations

import math

from pluck.adapters.ytdlp.commands import PROGRESS_FIELDS, OutputMarkers
from pluck.domain.media import MISSING
from pluck.domain.progress import ProgressUpdate

POSTPROCESSOR_LABELS = {
    "Merger": "Juntando vídeo e áudio",
    "ExtractAudio": "Convertendo áudio",
    "VideoRemuxer": "Ajustando o container",
    "VideoConvertor": "Convertendo vídeo",
    "EmbedThumbnail": "Embutindo capa",
    "Metadata": "Gravando metadados",
    "EmbedSubtitle": "Embutindo legendas",
    "SubtitlesConvertor": "Convertendo legendas",
    "ThumbnailsConvertor": "Convertendo capa",
    "MoveFiles": "Finalizando",
}


def _number(text: str) -> float | None:
    if text in MISSING:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _integer(text: str) -> int | None:
    value = _number(text)
    return None if value is None else int(value)


def parse_progress_line(line: str, markers: OutputMarkers) -> ProgressUpdate | None:
    if not line.startswith(markers.progress):
        return None
    parts = line[len(markers.progress) :].rstrip("\r\n").split("|")
    if len(parts) != len(PROGRESS_FIELDS):
        return None
    status, downloaded, total, estimate, speed, eta, fragment_index, fragment_count, format_id, vcodec, acodec = parts
    return ProgressUpdate(
        status=status,
        downloaded_bytes=_integer(downloaded),
        total_bytes=_integer(total) or _integer(estimate),
        speed=_number(speed),
        eta=_integer(eta),
        fragment_index=_integer(fragment_index),
        fragment_count=_integer(fragment_count),
        format_id=format_id,
        vcodec=vcodec,
        acodec=acodec,
    )


def parse_postprocess_line(line: str, markers: OutputMarkers) -> tuple[str, str] | None:
    if not line.startswith(markers.postprocess):
        return None
    status, _, name = line[len(markers.postprocess) :].rstrip("\r\n").partition("|")
    return status, postprocessor_label(name)


def parse_file_line(line: str, markers: OutputMarkers) -> str | None:
    if not line.startswith(markers.file):
        return None
    path = line[len(markers.file) :].rstrip("\r\n")
    return path or None


def postprocessor_label(name: str) -> str:
    if name.startswith("Fixup"):
        return "Corrigindo o arquivo"
    return POSTPROCESSOR_LABELS.get(name, "Processando")


MAX_PENDING_LINE = 65536


def split_lines(pending: str, chunk: str) -> tuple[list[str], str]:
    *lines, rest = (pending + chunk).split("\n")
    return lines, "" if len(rest) > MAX_PENDING_LINE else rest
