from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QEventLoop  # noqa: E402
from PySide6.QtGui import QFont, QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402

from pluck.adapters.desktop_shell import QtDesktopShell  # noqa: E402
from pluck.adapters.download_runner import QtDownloadRunner  # noqa: E402
from pluck.adapters.process import YtDlpRuntime  # noqa: E402
from pluck.adapters.storage import BackgroundWriter, JsonFile  # noqa: E402
from pluck.app import QML_DIR, AppServices, build_engine, configure_application  # noqa: E402
from pluck.application.ports import Failure, ProbeResult  # noqa: E402
from pluck.domain.jobs import STATUS_GROUPS, DownloadJob, Status  # noqa: E402
from pluck.domain.options import AUDIO, VIDEO, DownloadOptions, Preferences  # noqa: E402
from pluck.presentation.analyzer import Analyzer  # noqa: E402
from pluck.presentation.desktop import Desktop  # noqa: E402
from pluck.presentation.downloads import DownloadManager  # noqa: E402
from pluck.presentation.settings import Settings  # noqa: E402

FIXTURES = PROJECT_ROOT / "tests" / "fixtures"
SCENARIOS = ("idle", "video", "audio", "playlist", "error", "loading", "settings", "empty")
SCENARIO_URLS = {
    "video": "https://www.youtube.com/watch?v=fOT0BUpITw8&list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",
    "audio": "https://www.youtube.com/watch?v=fOT0BUpITw8&list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",
    "playlist": "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI",
    "error": "https://www.youtube.com/watch?v=abc",
    "loading": "https://www.youtube.com/watch?v=abc",
}


def scenario_result(scenario: str) -> ProbeResult | None:
    if scenario in ("video", "audio"):
        return json.loads((FIXTURES / "modern_video.json").read_text())
    if scenario == "playlist":
        return json.loads((FIXTURES / "playlist.json").read_text())
    if scenario == "error":
        return Failure(
            "O YouTube pediu login pra liberar o vídeo. Ative os cookies do navegador em Configurações.",
            "[youtube] abc: Sign in to confirm you’re not a bot.",
        )
    return None


class FixtureProbe:
    def __init__(self, result: ProbeResult | None):
        self._result = result
        self._on_done: Callable[[ProbeResult], None] | None = None

    def prepare(
        self, url: str, include_playlist: bool, cookies_browser: str, on_done: Callable[[ProbeResult], None]
    ) -> FixtureProbe:
        self._on_done = on_done
        return self

    def start(self) -> None:
        if self._result is not None and self._on_done is not None:
            self._on_done(self._result)

    def cancel(self) -> None:
        pass


def sample_jobs(folder: str) -> list[DownloadJob]:
    playlist = json.loads((FIXTURES / "playlist.json").read_text())["entries"]

    def job(index: int, status: Status, options: DownloadOptions, **fields) -> DownloadJob:
        entry = playlist[index]
        return DownloadJob(
            url=entry["url"],
            title=entry["title"],
            channel=entry.get("channel") or "",
            thumbnail=f"https://i.ytimg.com/vi/{entry['id']}/mqdefault.jpg",
            duration=entry.get("duration") or 0,
            options=options,
            preferences=Preferences(folder=folder),
            status=status,
            **fields,
        )

    hd = DownloadOptions(VIDEO, 1080, "mp4")
    mp3 = DownloadOptions(AUDIO, audio_format="mp3")
    return [
        job(
            1,
            Status.DOWNLOADING,
            hd,
            progress=0.42,
            stage="Baixando vídeo",
            detail="48,2 MB de 112 MB · 6,4 MB/s · faltam 0:10",
            speed=6.4 * 1024 * 1024,
        ),
        job(2, Status.POSTPROCESSING, mp3, progress=1.0, stage="Convertendo áudio"),
        job(3, Status.QUEUED, hd, progress=0.0, stage="Na fila"),
        job(4, Status.COMPLETED, mp3, progress=1.0, stage="Concluído", detail="7,8 MB", file_path="/tmp/a.mp3"),
        job(
            5,
            Status.FAILED,
            hd,
            stage="Falhou",
            error="O YouTube pediu login pra liberar o vídeo. Ative os cookies do navegador em Configurações.",
            error_detail="ERROR: [youtube] abc: Sign in to confirm you’re not a bot",
        ),
        job(6, Status.INTERRUPTED, DownloadOptions(VIDEO, 0, "mkv"), progress=0.63, stage="Interrompido"),
        job(7, Status.COMPLETED, hd, progress=1.0, stage="Concluído", detail="214 MB", file_path="/tmp/b.mp4"),
    ]


def build_preview_services(root: Path, scenario: str) -> AppServices:
    settings = Settings(JsonFile(root / "settings.json"))
    settings.update("folder", os.path.expanduser("~/Downloads"))
    if scenario == "audio":
        settings.update("defaultMode", AUDIO)
    runtime = YtDlpRuntime.prepare("/nonexistent/yt-dlp", root / "yt-dlp-home")
    downloads = DownloadManager(settings, JsonFile(root / "history.json"), QtDownloadRunner(runtime))
    if scenario != "empty":
        downloads._model.reset_with(sample_jobs(settings.value("folder")))
        downloads.countsChanged.emit()
        downloads._total_speed = 6.4 * 1024 * 1024
        downloads.speedChanged.emit()
    analyzer = Analyzer(settings, FixtureProbe(scenario_result(scenario)))
    return AppServices(settings, analyzer, downloads, Desktop(QtDesktopShell()), BackgroundWriter())


def apply_scenario(services: AppServices, window, scenario: str) -> None:
    if scenario in SCENARIO_URLS:
        services.analyzer.analyze(SCENARIO_URLS[scenario])
    elif scenario == "settings":
        window.setProperty("currentPage", 1)
    elif scenario == "empty":
        for group in [*STATUS_GROUPS, "all"]:
            services.downloads._view.setProperty("group", group)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("output", type=Path)
    parser.add_argument("--size", default="1200x800")
    parser.add_argument("--wait", type=float, default=2.5)
    args = parser.parse_args()

    configure_application()
    app = QGuiApplication(sys.argv[:1])
    app.setFont(QFont("Inter Variable", 10))
    with tempfile.TemporaryDirectory() as temporary:
        services = build_preview_services(Path(temporary), args.scenario)
        engine = build_engine(services)
        engine.warnings.connect(lambda warnings: [print(warning.toString(), file=sys.stderr) for warning in warnings])
        engine.load(QML_DIR / "Main.qml")
        if not engine.rootObjects():
            return 1
        window = engine.rootObjects()[0]
        if not isinstance(window, QQuickWindow):
            return 1
        width, height = (int(part) for part in args.size.split("x"))
        window.setWidth(width)
        window.setHeight(height)
        services.desktop.check_tools()
        apply_scenario(services, window, args.scenario)

        started = time.monotonic()
        while time.monotonic() - started < args.wait:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)
        window.grabWindow().save(str(args.output))
        print(f"{args.output} ({time.monotonic() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
