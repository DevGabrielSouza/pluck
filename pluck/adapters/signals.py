from __future__ import annotations

import contextlib
import signal
import socket
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, QSocketNotifier

TERMINATING_SIGNALS = (signal.SIGINT, signal.SIGTERM)


def quit_on_signals(app: QCoreApplication) -> Callable[[], None]:
    reader, writer = socket.socketpair()

    def drain() -> None:
        with contextlib.suppress(OSError):
            reader.recv(64)

    reader.setblocking(False)
    writer.setblocking(False)
    previous_fd = signal.set_wakeup_fd(writer.fileno())
    previous_handlers = {number: signal.signal(number, lambda *_: app.quit()) for number in TERMINATING_SIGNALS}
    notifier = QSocketNotifier(reader.fileno(), QSocketNotifier.Type.Read, app)
    notifier.activated.connect(drain)

    def restore() -> None:
        notifier.setEnabled(False)
        notifier.deleteLater()
        signal.set_wakeup_fd(previous_fd)
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)
        reader.close()
        writer.close()

    return restore
