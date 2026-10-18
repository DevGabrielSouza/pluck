import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Pluck
import Pluck.Core

ApplicationWindow {
    id: window

    property int currentPage: 0
    property bool closeConfirmed: false
    readonly property bool maximized: visibility === Window.Maximized || visibility === Window.FullScreen

    width: 1200
    height: 800
    minimumWidth: 940
    minimumHeight: 640
    visible: true
    title: "Pluck"
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "transparent"
    font.family: Theme.fontFamily
    font.pixelSize: Theme.textBase

    function openDownloadedFile(path) {
        if (!Desktop.openFile(path))
            Toasts.show("warn", "Arquivo não encontrado", "Ele pode ter sido movido ou apagado.")
    }

    onClosing: close => {
        if (Downloads.runningCount > 0 && !closeConfirmed) {
            close.accepted = false
            quitDialog.open()
        }
    }

    Shortcut {
        sequence: "Ctrl+1"
        enabled: !quitDialog.opened
        onActivated: window.currentPage = 0
    }

    Shortcut {
        sequence: "Ctrl+,"
        enabled: !quitDialog.opened
        onActivated: window.currentPage = 1
    }

    Shortcut {
        sequence: StandardKey.Quit
        enabled: !quitDialog.opened
        onActivated: window.close()
    }

    Connections {
        target: Downloads

        function onJobFinished(jobId, title, status) {
            if (status === "completed")
                Toasts.show("ok", "Download concluído", title, "Abrir", () => window.openDownloadedFile(Downloads.filePath(jobId)))
            else if (status === "failed")
                Toasts.show("err", "Download falhou", title, "Ver fila", () => {
                    window.currentPage = 0
                    Downloads.view.group = "failed"
                })
        }
    }

    Rectangle {
        id: frame

        anchors.fill: parent
        radius: window.maximized ? 0 : 12
        color: Theme.bg
        border.width: window.maximized ? 0 : 1
        border.color: Theme.borderStrong

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: frame.border.width
            spacing: 0

            Topbar {
                Layout.fillWidth: true
                window: window
                currentPage: window.currentPage
                onNavigate: page => window.currentPage = page
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.currentPage

                DownloadsPage {
                    onOpenSettings: window.currentPage = 1
                }

                SettingsPage {}
            }

            StatusBar {
                Layout.fillWidth: true
            }
        }
    }

    ToastHost {
        id: toastHost

        anchors.fill: parent
        anchors.rightMargin: 20
        anchors.bottomMargin: 46

        Connections {
            target: Toasts

            function onRequested(tone, title, message, actionText, action) {
                toastHost.show(tone, title, message, actionText, action)
            }
        }
    }

    ConfirmDialog {
        id: quitDialog

        title: "Fechar o Pluck?"
        message: Downloads.runningCount === 1
            ? "Tem 1 download em andamento. Dá para tentar de novo depois, e ele continua de onde parou se o site permitir."
            : "Tem " + Downloads.runningCount + " downloads em andamento. Dá para tentar de novo depois, e eles continuam de onde pararam se o site permitir."
        confirmText: "Fechar mesmo assim"
        destructive: true
        onConfirmed: {
            window.closeConfirmed = true
            window.close()
        }
    }

    ResizeHandles {
        anchors.fill: parent
        visible: !window.maximized
        window: window
    }
}
