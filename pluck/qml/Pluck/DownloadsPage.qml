import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    signal openSettings()

    readonly property bool textInputFocused: {
        const item = root.Window.activeFocusItem
        return item instanceof TextInput || item instanceof TextEdit
    }

    Shortcut {
        sequences: [StandardKey.Paste]
        enabled: root.visible && !root.textInputFocused && !errorDialog.opened
        onActivated: composer.pasteAndAnalyze()
    }

    Shortcut {
        sequence: "Ctrl+L"
        enabled: root.visible && !errorDialog.opened
        onActivated: {
            composer.urlField.forceActiveFocus()
            composer.urlField.selectAll()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        ColumnLayout {
            Layout.preferredWidth: 430
            Layout.fillWidth: false
            Layout.fillHeight: true
            spacing: 12

            Flickable {
                id: composerScroll

                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: composer.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: AppScrollBar {}

                Composer {
                    id: composer

                    onOpenSettings: root.openSettings()

                    width: composerScroll.width - (composerScroll.contentHeight > composerScroll.height ? 12 : 0)
                }
            }

            DownloadBar {
                visible: composer.ready
                Layout.fillWidth: true
                Layout.rightMargin: composer.width < composerScroll.width ? 12 : 0
                composer: composer
            }
        }

        QueueCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            onShowError: (message, detail) => errorDialog.show(message, detail)
        }
    }

    ErrorDialog {
        id: errorDialog
    }
}
