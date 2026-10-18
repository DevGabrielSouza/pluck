import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QEventLoop

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_YTDLP = str(Path(__file__).resolve().parent / "fake_ytdlp.py")


@pytest.fixture(scope="session")
def qt_app() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def runtime(tmp_path: Path):
    from pluck.adapters.process import YtDlpRuntime

    return YtDlpRuntime.prepare(FAKE_YTDLP, tmp_path / "yt-dlp-home")


@pytest.fixture
def wait_until(qt_app: QCoreApplication) -> Callable[[Callable[[], bool], float], None]:
    def wait(predicate: Callable[[], bool], timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError("condition not met before timeout")
            qt_app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)

    return wait


@pytest.fixture
def build_settings(qt_app):
    from pluck.adapters.storage import JsonFile
    from pluck.presentation.settings import Settings

    def build(path: Path):
        return Settings(JsonFile(path))

    return build


@pytest.fixture
def build_manager(runtime):
    from pluck.adapters.download_runner import QtDownloadRunner
    from pluck.adapters.process import YtDlpRuntime
    from pluck.adapters.storage import JsonFile
    from pluck.presentation.downloads import DownloadManager

    managers = []

    def build(settings, history_path: Path, executable: str | None = None):
        chosen = runtime if executable is None else YtDlpRuntime.prepare(executable, runtime.home)
        manager = DownloadManager(settings, JsonFile(history_path), QtDownloadRunner(chosen))
        managers.append(manager)
        return manager

    yield build
    for manager in managers:
        manager.shutdown()


@pytest.fixture
def build_analyzer(runtime):
    from pluck.adapters.media_probe import YtDlpMediaProbe
    from pluck.adapters.process import YtDlpRuntime
    from pluck.presentation.analyzer import Analyzer

    def build(settings, executable: str | None = None):
        chosen = runtime if executable is None else YtDlpRuntime.prepare(executable, runtime.home)
        return Analyzer(settings, YtDlpMediaProbe(chosen))

    return build
