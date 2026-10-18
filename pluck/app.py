from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, QStandardPaths, Qt
from PySide6.QtGui import QFont, QGuiApplication, QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle

from pluck import APP_ID
from pluck.adapters.desktop_shell import QtDesktopShell, send_notification
from pluck.adapters.download_runner import QtDownloadRunner
from pluck.adapters.instance import SingleInstance
from pluck.adapters.media_probe import YtDlpMediaProbe
from pluck.adapters.process import YtDlpRuntime, find_executable
from pluck.adapters.signals import quit_on_signals
from pluck.adapters.storage import BackgroundWriter, JsonFile
from pluck.presentation.analyzer import Analyzer
from pluck.presentation.desktop import Desktop
from pluck.presentation.downloads import DownloadManager
from pluck.presentation.icons import IconProvider
from pluck.presentation.settings import Settings

PACKAGE_DIR = Path(__file__).resolve().parent
QML_DIR = PACKAGE_DIR / "qml"
ICONS_DIR = PACKAGE_DIR / "icons"
APP_ICON = PACKAGE_DIR / "assets" / "pluck.svg"
CORE_MODULE = "Pluck.Core"
YTDLP_HOME_NAME = "yt-dlp-home"

register_singleton = cast("Callable[..., int]", qmlRegisterSingletonInstance)


@dataclass
class AppServices:
    settings: Settings
    analyzer: Analyzer
    downloads: DownloadManager
    desktop: Desktop
    writer: BackgroundWriter

    def shutdown(self) -> None:
        self.analyzer.cancel()
        self.downloads.shutdown()
        self.settings.save()
        self.writer.close()


def configure_application() -> None:
    QGuiApplication.setApplicationName(APP_ID)
    QGuiApplication.setDesktopFileName(APP_ID)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QQuickStyle.setStyle("Basic")
    QQuickWindow.setDefaultAlphaBuffer(True)


def build_services(config_dir: Path, data_dir: Path, ytdlp: str = "yt-dlp") -> AppServices:
    writer = BackgroundWriter()
    settings = Settings(JsonFile(config_dir / "settings.json", writer))
    runtime = YtDlpRuntime.prepare(ytdlp, data_dir / YTDLP_HOME_NAME)
    return AppServices(
        settings=settings,
        analyzer=Analyzer(settings, YtDlpMediaProbe(runtime)),
        downloads=DownloadManager(settings, JsonFile(data_dir / "history.json", writer), QtDownloadRunner(runtime)),
        desktop=Desktop(QtDesktopShell(runtime.executable, find_executable("ffmpeg"))),
        writer=writer,
    )


def build_engine(services: AppServices) -> QQmlApplicationEngine:
    register_singleton(Settings, CORE_MODULE, 1, 0, "AppSettings", services.settings)
    register_singleton(Analyzer, CORE_MODULE, 1, 0, "Analyzer", services.analyzer)
    register_singleton(DownloadManager, CORE_MODULE, 1, 0, "Downloads", services.downloads)
    register_singleton(Desktop, CORE_MODULE, 1, 0, "Desktop", services.desktop)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconProvider(ICONS_DIR))
    engine.addImportPath(str(QML_DIR))
    return engine


def notify_when_unfocused(services: AppServices, app: QGuiApplication):
    def on_job_finished(_job_id: str, title: str, status: str) -> None:
        if not services.settings.store.notify_on_finish or status == "canceled":
            return
        if app.applicationState() == Qt.ApplicationState.ApplicationActive:
            return
        heading = "Download concluído" if status == "completed" else "Download falhou"
        send_notification(APP_ICON, heading, title)

    return on_job_finished


def bring_to_front(window: QObject) -> None:
    if isinstance(window, QWindow):
        window.show()
        window.raise_()
        window.requestActivate()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    configure_application()
    app = QGuiApplication(sys.argv if argv is None else argv)
    instance = SingleInstance(
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.RuntimeLocation)), APP_ID
    )
    if not instance.claim():
        return 0
    app.setWindowIcon(QIcon(str(APP_ICON)))
    app.setFont(QFont("Inter Variable", 10))
    services = build_services(
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)),
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)),
    )
    engine = build_engine(services)
    engine.load(QML_DIR / "Main.qml")
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    instance.activated.connect(lambda: bring_to_front(window))
    app.aboutToQuit.connect(instance.release)
    services.downloads.jobFinished.connect(notify_when_unfocused(services, app))
    app.aboutToQuit.connect(services.shutdown)
    app.aboutToQuit.connect(quit_on_signals(app))
    services.desktop.check_tools()
    return app.exec()
