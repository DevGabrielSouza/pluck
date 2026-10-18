import QtQuick
import QtQuick.Layouts
import Pluck.Core

Rectangle {
    id: root

    required property string jobId
    required property string title
    required property string channel
    required property string thumbnail
    required property string durationText
    required property string formatLabel
    required property bool isAudio
    required property string status
    required property real progress
    required property string stage
    required property string detail
    required property string errorText
    required property string errorDetail
    required property string filePath

    readonly property bool running: status === "resolving" || status === "downloading" || status === "postprocessing"
    readonly property bool retryable: status === "failed" || status === "canceled" || status === "interrupted"
    readonly property bool showProgress: running || status === "interrupted" || status === "queued"
    readonly property var statusStyle: ({
        queued: { tone: "idle", text: "Na fila" },
        resolving: { tone: "info", text: "Preparando" },
        downloading: { tone: "info", text: "Baixando" },
        postprocessing: { tone: "violet", text: "Processando" },
        completed: { tone: "ok", text: "Concluído" },
        failed: { tone: "err", text: "Erro" },
        canceled: { tone: "idle", text: "Cancelado" },
        interrupted: { tone: "warn", text: "Interrompido" }
    })[status] ?? { tone: "idle", text: "" }

    signal showError(string message, string detail)

    function openFile() {
        if (!Desktop.openFile(root.filePath))
            Toasts.show("warn", "Arquivo não encontrado", "Ele pode ter sido movido ou apagado.")
    }

    implicitHeight: 92
    radius: Theme.radiusLg
    color: hover.hovered ? Theme.cardHover : Theme.card
    border.color: running ? Theme.withAlpha(Theme.accent, 0.22) : Theme.border

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    HoverHandler {
        id: hover
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        onDoubleClicked: if (root.status === "completed") root.openFile()
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        anchors.rightMargin: 14
        spacing: 14

        Thumbnail {
            Layout.preferredWidth: 128
            Layout.preferredHeight: 72
            source: root.thumbnail
            badge: root.durationText
            fallbackIcon: root.isAudio ? "music" : "film"
            maskColor: root.color
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 5

            AppText {
                Layout.fillWidth: true
                text: root.title
                font.pixelSize: Theme.textMd
                font.weight: Font.Medium
                elide: Text.ElideRight
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    Layout.preferredHeight: 18
                    Layout.preferredWidth: formatRow.implicitWidth + 12
                    radius: 5
                    color: Theme.bgElev
                    border.color: Theme.border

                    Row {
                        id: formatRow

                        anchors.centerIn: parent
                        spacing: 4

                        Icon {
                            name: root.isAudio ? "music" : "film"
                            size: 10
                            color: Theme.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        AppText {
                            text: root.formatLabel
                            mono: true
                            font.pixelSize: Theme.textMicro
                            color: Theme.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                AppText {
                    Layout.fillWidth: true
                    text: root.channel
                    color: Theme.textDim
                    font.pixelSize: Theme.textSm
                    elide: Text.ElideRight
                }
            }

            ProgressLine {
                visible: root.showProgress
                Layout.fillWidth: true
                Layout.topMargin: 3
                value: root.progress
                indeterminate: root.running && root.progress < 0
                shimmer: root.running
                tone: root.status === "postprocessing" ? Theme.violet : root.status === "interrupted" ? Theme.warn : Theme.accent
                toneEnd: root.status === "postprocessing" ? "#C4B5FD" : root.status === "interrupted" ? "#FBBF24" : Theme.cyan
                opacity: root.status === "queued" ? 0.5 : 1
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Icon {
                    visible: root.status === "failed" || root.status === "completed"
                    name: root.status === "failed" ? "circle-alert" : "circle-check"
                    size: 13
                    color: root.status === "failed" ? Theme.err : Theme.ok
                }

                AppText {
                    text: root.status === "failed" ? root.errorText : root.stage
                    color: root.status === "failed" ? Theme.err : root.status === "postprocessing" ? Theme.violet : root.running ? Theme.accentText : Theme.textMuted
                    font.pixelSize: Theme.textSm
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                    Layout.fillWidth: root.status === "failed"
                    Layout.maximumWidth: root.status === "failed" ? -1 : implicitWidth
                }

                AppText {
                    visible: root.detail !== "" && root.status !== "failed"
                    text: "· " + root.detail
                    color: Theme.textDim
                    font.pixelSize: Theme.textSm
                    mono: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Item {
                    visible: root.detail === "" && root.status !== "failed"
                    Layout.fillWidth: true
                }
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: 8

            Pill {
                Layout.alignment: Qt.AlignRight
                text: root.statusStyle.text
                tone: root.statusStyle.tone
                pulse: root.running
            }

            Row {
                Layout.alignment: Qt.AlignRight
                spacing: 2

                IconButton {
                    visible: root.status === "completed"
                    iconName: "play"
                    hint: "Abrir arquivo"
                    variant: "accent"
                    onClicked: root.openFile()
                }

                IconButton {
                    visible: root.status === "completed"
                    iconName: "folder-open"
                    hint: "Mostrar na pasta"
                    onClicked: Desktop.showInFolder(root.filePath)
                }

                IconButton {
                    visible: root.status === "failed"
                    iconName: "info"
                    hint: "Ver detalhes do erro"
                    onClicked: root.showError(root.errorText, root.errorDetail)
                }

                IconButton {
                    visible: root.retryable
                    iconName: "rotate-cw"
                    hint: "Tentar de novo"
                    variant: "accent"
                    onClicked: Downloads.retry(root.jobId)
                }

                IconButton {
                    visible: root.running || root.status === "queued"
                    iconName: "x"
                    hint: "Cancelar"
                    variant: "danger"
                    onClicked: Downloads.cancel(root.jobId)
                }

                IconButton {
                    visible: !root.running && root.status !== "queued"
                    iconName: "trash-2"
                    hint: "Remover da lista"
                    variant: "danger"
                    onClicked: Downloads.remove(root.jobId)
                }
            }
        }
    }
}
