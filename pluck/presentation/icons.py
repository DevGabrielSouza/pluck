from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

HEX_COLOR = re.compile(r"^(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FALLBACK_COLOR = "9CA3AF"
FALLBACK_SIZE = QSize(48, 48)


def split_color(raw: str) -> tuple[str, float]:
    if not HEX_COLOR.match(raw):
        return FALLBACK_COLOR, 1.0
    if len(raw) == 8:
        return raw[2:], int(raw[:2], 16) / 255
    return raw, 1.0


class IconProvider(QQuickImageProvider):
    def __init__(self, directory: Path):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._directory = directory
        self._sources: dict[str, bytes] = {}

    def _source(self, name: str) -> bytes | None:
        if name not in self._sources:
            path = self._directory / f"{name}.svg"
            if not re.fullmatch(r"[a-z0-9-]+", name) or not path.is_file():
                return None
            self._sources[name] = path.read_bytes()
        return self._sources[name]

    def requestImage(self, icon_id: str, size: QSize, requested_size: QSize) -> QImage:
        name, _, raw_color = icon_id.partition("/")
        dimensions = requested_size if requested_size.isValid() and not requested_size.isEmpty() else FALLBACK_SIZE
        image = QImage(dimensions, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        source = self._source(name)
        if source is not None:
            color, opacity = split_color(raw_color)
            renderer = QSvgRenderer(QByteArray(source.replace(b"currentColor", f"#{color}".encode())))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(opacity)
            renderer.render(painter)
            painter.end()
        size.setWidth(dimensions.width())
        size.setHeight(dimensions.height())
        return image
