from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 300
LOCK_TIMEOUT_MS = 3000

logger = logging.getLogger(__name__)


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, directory: Path, name: str, parent: QObject | None = None):
        super().__init__(parent)
        self._directory = directory
        self._socket_path = str(directory / f"{name}.sock")
        self._lock_path = str(directory / f"{name}.lock")
        self._server: QLocalServer | None = None

    def claim(self) -> bool:
        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = QLockFile(self._lock_path)
        if not lock.tryLock(LOCK_TIMEOUT_MS):
            logger.warning("could not lock %s, starting without waiting for other instances", self._lock_path)
        try:
            if self._notify_running_instance():
                return False
            self._listen()
            return True
        finally:
            lock.unlock()

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _listen(self) -> None:
        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        QLocalServer.removeServer(self._socket_path)
        if not server.listen(self._socket_path):
            logger.warning("could not listen on %s: %s", self._socket_path, server.errorString())
            return
        server.newConnection.connect(self._on_new_connection)
        self._server = server

    def _notify_running_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._socket_path)
        if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
            return False
        socket.write(b"activate\n")
        socket.waitForBytesWritten(CONNECT_TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def _on_new_connection(self) -> None:
        assert self._server is not None
        while (connection := self._server.nextPendingConnection()) is not None:
            connection.disconnected.connect(connection.deleteLater)
            connection.disconnectFromServer()
            self.activated.emit()
