import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Pluck.Core

Rectangle {
    id: root

    required property Composer composer

    readonly property var options: composer.formatOptions

    implicitHeight: layout.implicitHeight + 28
    radius: Theme.radiusCard
    color: Theme.card
    border.color: Theme.borderNeon

    ColumnLayout {
        id: layout

        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            AbstractButton {
                id: folderButton

                Layout.fillWidth: true
                implicitHeight: 24
                hoverEnabled: true
                onClicked: folderDialog.open()

                contentItem: RowLayout {
                    spacing: 6

                    Icon {
                        name: "folder"
                        size: 13
                        color: folderButton.hovered ? Theme.accentText : Theme.textDim
                    }

                    AppText {
                        Layout.fillWidth: true
                        text: Desktop.shortPath(AppSettings.folder)
                        mono: true
                        color: folderButton.hovered ? Theme.accentText : Theme.textMuted
                        font.pixelSize: Theme.textXs
                        elide: Text.ElideMiddle
                    }
                }

                background: Item {}

                Hint {
                    visible: folderButton.hovered
                    text: "Trocar a pasta de destino"
                }
            }

            AppText {
                visible: root.options.estimatedSize > 0 && !root.composer.isPlaylist
                text: "≈ " + Desktop.formatBytes(root.options.estimatedSize)
                mono: true
                color: Theme.textMuted
                font.pixelSize: Theme.textXs
            }
        }

        RowLayout {
            visible: Desktop.toolsChecked && Desktop.ffmpegVersion === ""
            Layout.fillWidth: true
            spacing: 6

            Icon {
                name: "circle-alert"
                size: 13
                color: Theme.warn
            }

            AppText {
                Layout.fillWidth: true
                text: "ffmpeg não encontrado: juntar vídeo e áudio e converter áudio vão falhar."
                color: Theme.warn
                font.pixelSize: Theme.textXs
                wrapMode: Text.Wrap
            }
        }

        AppButton {
            Layout.fillWidth: true
            size: "lg"
            variant: "primary"
            iconName: "download"
            enabled: root.composer.selectionCount > 0
            text: root.composer.isPlaylist
                ? (root.composer.selectionCount === 1 ? "Baixar 1 vídeo" : "Baixar " + root.composer.selectionCount + " vídeos")
                : root.options.mode === "audio" ? "Baixar áudio" : "Baixar vídeo"
            onClicked: root.composer.startDownload()
        }
    }

    FolderDialog {
        id: folderDialog

        title: "Pasta de destino"
        currentFolder: Desktop.fileUrl(AppSettings.folder)
        onAccepted: AppSettings.folder = Desktop.localPath(selectedFolder.toString())
    }
}
