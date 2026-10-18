import QtQuick
import QtQuick.Layouts
import Pluck.Core

Item {
    id: root

    readonly property string summary: {
        if (Downloads.runningCount > 0) {
            const queued = Downloads.queuedCount > 0 ? " · " + Downloads.queuedCount + " na fila" : ""
            return "Baixando " + Downloads.runningCount + queued
        }
        return "Pronto"
    }

    implicitHeight: 30

    component Separator: Rectangle {
        Layout.preferredWidth: 3
        Layout.preferredHeight: 3
        radius: 1.5
        color: Theme.textDim
        opacity: 0.6
    }

    component Meta: AppText {
        color: Theme.textDim
        font.pixelSize: Theme.textXs
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: Theme.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 10

        StatusDot {
            tone: Downloads.runningCount > 0 ? "info" : "ok"
            pulse: Downloads.runningCount > 0
        }

        Meta {
            text: root.summary
            color: Theme.textMuted
        }

        Separator {}

        Meta {
            text: !Desktop.toolsChecked ? "yt-dlp …"
                : Desktop.ytdlpVersion === "" ? "yt-dlp não encontrado"
                : Desktop.ytdlpOutdated ? "yt-dlp " + Desktop.ytdlpVersion + " desatualizado (mínimo " + Desktop.minimumYtdlpVersion + ")"
                : "yt-dlp " + Desktop.ytdlpVersion
            color: Desktop.toolsChecked && (Desktop.ytdlpVersion === "" || Desktop.ytdlpOutdated) ? Theme.err : Theme.textDim
            mono: true
        }

        Separator {}

        Meta {
            text: !Desktop.toolsChecked ? "ffmpeg …" : Desktop.ffmpegVersion !== "" ? "ffmpeg " + Desktop.ffmpegVersion : "ffmpeg não encontrado"
            color: Desktop.toolsChecked && Desktop.ffmpegVersion === "" ? Theme.warn : Theme.textDim
            mono: true
        }

        Item {
            Layout.fillWidth: true
        }

        Item {
            implicitWidth: folderRow.implicitWidth
            implicitHeight: folderRow.implicitHeight

            Row {
                id: folderRow

                spacing: 6

                Icon {
                    name: "folder"
                    size: 12
                    color: folderArea.containsMouse ? Theme.accentText : Theme.textDim
                    anchors.verticalCenter: parent.verticalCenter
                }

                Meta {
                    text: Desktop.shortPath(AppSettings.folder)
                    color: folderArea.containsMouse ? Theme.accentText : Theme.textDim
                    mono: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: folderArea

                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Desktop.openFolder(AppSettings.folder)
            }
        }
    }
}
