import sys

from PySide6.QtCore import QByteArray, QEventLoop, QMetaObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from pluck.app import ICONS_DIR, QML_DIR
from pluck.presentation.icons import IconProvider

SCENE = b"""
import QtQuick
import QtQuick.Controls
import Pluck

ApplicationWindow {
    width: 600
    height: 400
    visible: true
    property int confirmations: 0
    readonly property bool dialogVisible: dialog.visible

    function openDialog() {
        dialog.open()
    }

    ConfirmDialog {
        id: dialog
        title: "Sair?"
        message: "Teste"
        onConfirmed: confirmations += 1
    }
}
"""


def settle(app: QGuiApplication) -> None:
    for _ in range(20):
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        QTest.qWait(10)


def main() -> int:
    app = QGuiApplication(sys.argv[:1])
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icon", IconProvider(ICONS_DIR))
    engine.addImportPath(str(QML_DIR))
    engine.loadData(QByteArray(SCENE), QUrl.fromLocalFile(str(QML_DIR / "scene.qml")))
    window = engine.rootObjects()[0]
    if not isinstance(window, QQuickWindow):
        return 1
    window.requestActivate()

    QMetaObject.invokeMethod(window, "openDialog")
    settle(app)
    QTest.keyClick(window, Qt.Key.Key_Return)
    settle(app)
    canceled = not window.property("dialogVisible") and window.property("confirmations") == 0

    QMetaObject.invokeMethod(window, "openDialog")
    settle(app)
    QTest.keyClick(window, Qt.Key.Key_Tab)
    QTest.keyClick(window, Qt.Key.Key_Return)
    settle(app)
    confirmed = not window.property("dialogVisible") and window.property("confirmations") == 1

    print(f"canceled={canceled} confirmed={confirmed}")
    return 0 if canceled and confirmed else 1


if __name__ == "__main__":
    sys.exit(main())
