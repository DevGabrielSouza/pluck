import os
import signal
import threading

from PySide6.QtCore import QTimer

from pluck.adapters.signals import quit_on_signals


def test_sigterm_during_the_event_loop_quits_cleanly(qt_app, capfd):
    previous = signal.getsignal(signal.SIGTERM)
    restore = quit_on_signals(qt_app)
    try:
        threading.Timer(0.2, os.kill, (os.getpid(), signal.SIGTERM)).start()
        QTimer.singleShot(5000, lambda: qt_app.exit(1))
        assert qt_app.exec() == 0
    finally:
        restore()
    assert signal.getsignal(signal.SIGTERM) is previous
    assert "Traceback" not in capfd.readouterr().err


def test_restoring_inside_about_to_quit_does_not_break_the_wakeup_read(qt_app, capfd):
    restore = quit_on_signals(qt_app)
    qt_app.aboutToQuit.connect(restore)
    try:
        threading.Timer(0.2, os.kill, (os.getpid(), signal.SIGTERM)).start()
        QTimer.singleShot(5000, lambda: qt_app.exit(1))
        assert qt_app.exec() == 0
        qt_app.processEvents()
    finally:
        qt_app.aboutToQuit.disconnect(restore)
    assert "Traceback" not in capfd.readouterr().err
