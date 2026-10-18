pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Pluck.Core

Card {
    id: root

    property string clipboardUrl
    property string dismissedClipboard
    property alias urlField: urlField
    property alias formatOptions: formatOptions

    readonly property var result: Analyzer.result

    signal openSettings()
    readonly property bool ready: Analyzer.state === "ready"
    readonly property bool isPlaylist: ready && result.kind === "playlist"
    readonly property PlaylistPreview playlist: playlistLoader.item as PlaylistPreview
    readonly property int selectionCount: isPlaylist && playlist ? playlist.selectedCount : 1

    function analyze(text) {
        const url = Desktop.normalizeUrl(text)
        if (url === "")
            return
        urlField.text = url
        clipboardUrl = ""
        Analyzer.analyze(url)
    }

    function pasteAndAnalyze() {
        const text = Desktop.clipboardText()
        if (text !== "")
            analyze(text)
        urlField.forceActiveFocus()
    }

    function checkClipboard() {
        const text = Desktop.clipboardText()
        const candidate = Desktop.looksLikeUrl(text) ? Desktop.normalizeUrl(text) : ""
        const alreadyUsed = candidate === urlField.text || candidate === Analyzer.url || candidate === dismissedClipboard
        clipboardUrl = alreadyUsed ? "" : candidate
    }

    function resetOptions() {
        formatOptions.mode = result.hasVideo === false ? "audio" : AppSettings.defaultMode
        formatOptions.quality = result.defaultQuality !== undefined ? result.defaultQuality : 0
        formatOptions.container = AppSettings.defaultContainer
        formatOptions.audioFormat = AppSettings.defaultAudioFormat
    }

    function startDownload() {
        const options = {
            mode: formatOptions.mode,
            quality: formatOptions.quality,
            container: formatOptions.container,
            audioFormat: formatOptions.audioFormat
        }
        const entries = isPlaylist ? playlist.selectedEntries() : [{
            url: result.url,
            title: result.title,
            channel: result.channel,
            thumbnail: result.thumbnail,
            duration: result.duration,
            expectedSizes: Analyzer.expectedSizes(options.mode, options.quality, options.container, options.audioFormat)
        }]
        const added = Downloads.enqueue(entries, options)
        if (added === 0) {
            Toasts.show("warn", "Já está na fila", entries.length === 1 ? result.title : "Os vídeos escolhidos já estão sendo baixados.")
            return
        }
        Downloads.view.group = "all"
        Toasts.show("info", added === 1 ? "Adicionado à fila" : added + " vídeos adicionados à fila", result.title)
        urlField.text = ""
        Analyzer.clear()
    }

    title: "Novo download"
    subtitle: "Vídeo, playlist ou canal de qualquer site suportado"
    iconName: "link"
    active: urlField.activeFocus || dropArea.containsDrag

    headerActions: IconButton {
        visible: Analyzer.state !== "idle"
        iconName: "x"
        hint: "Limpar"
        onClicked: {
            urlField.text = ""
            Analyzer.clear()
        }
    }

    Connections {
        target: Analyzer

        function onStateChanged() {
            if (Analyzer.state === "ready")
                root.resetOptions()
        }
    }

    Connections {
        target: root.Window.window

        function onActiveChanged() {
            if (root.Window.window.active)
                root.checkClipboard()
        }
    }

    Component.onCompleted: checkClipboard()

    DropArea {
        id: dropArea

        Layout.fillWidth: true
        Layout.preferredHeight: urlRow.implicitHeight
        keys: ["text/uri-list", "text/plain"]
        onDropped: drop => {
            const text = drop.hasUrls ? drop.urls[0].toString() : drop.text
            if (text) {
                root.analyze(text)
                drop.accept()
            }
        }

        RowLayout {
            id: urlRow

            anchors.fill: parent
            spacing: 8

            AppTextField {
                id: urlField

                Layout.fillWidth: true
                large: true
                iconName: "link"
                placeholderText: "Cole o link aqui"
                onAccepted: root.analyze(text)
                Keys.onEscapePressed: {
                    if (Analyzer.state === "loading")
                        Analyzer.cancel()
                }

                trailing: IconButton {
                    iconName: "clipboard-paste"
                    hint: "Colar e analisar (Ctrl+V)"
                    boxSize: 30
                    iconSize: 15
                    onClicked: root.pasteAndAnalyze()
                }
            }

            AppButton {
                Layout.preferredHeight: 44
                variant: "primary"
                iconName: Analyzer.state === "loading" ? "" : "arrow-right"
                loading: Analyzer.state === "loading"
                hint: Analyzer.state === "loading" ? "Cancelar análise" : "Analisar link (Enter)"
                enabled: urlField.text.trim() !== "" || Analyzer.state === "loading"
                onClicked: Analyzer.state === "loading" ? Analyzer.cancel() : root.analyze(urlField.text)
            }
        }
    }

    Rectangle {
        visible: root.clipboardUrl !== ""
        Layout.fillWidth: true
        Layout.preferredHeight: 38
        radius: Theme.radiusMd
        color: Theme.withAlpha(Theme.accent, 0.06)
        border.color: Theme.withAlpha(Theme.accent, 0.22)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 4
            spacing: 8

            Icon {
                name: "clipboard-paste"
                size: 14
                color: Theme.accentText
            }

            AppText {
                text: "Link copiado:"
                font.pixelSize: Theme.textSm
            }

            AppText {
                Layout.fillWidth: true
                text: root.clipboardUrl.replace(/^https?:\/\/(www\.)?/, "")
                color: Theme.textMuted
                font.pixelSize: Theme.textSm
                elide: Text.ElideRight
            }

            AppButton {
                text: "Usar"
                size: "sm"
                variant: "ghost"
                onClicked: root.analyze(root.clipboardUrl)
            }

            IconButton {
                iconName: "x"
                boxSize: 26
                iconSize: 13
                hint: "Ignorar"
                onClicked: {
                    root.dismissedClipboard = root.clipboardUrl
                    root.clipboardUrl = ""
                }
            }
        }
    }

    Rectangle {
        visible: Analyzer.state === "idle"
        Layout.fillWidth: true
        Layout.preferredHeight: 196
        radius: Theme.radiusLg
        color: dropArea.containsDrag ? Theme.accentSoft : "transparent"
        border.color: dropArea.containsDrag ? Theme.borderNeon : Theme.borderStrong
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 12

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 52
                height: 52
                radius: 16
                color: Theme.accentSoft
                border.color: Theme.borderNeon

                Icon {
                    anchors.centerIn: parent
                    name: "arrow-down-to-line"
                    size: 22
                    color: Theme.accentText
                }
            }

            AppText {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Cole um link ou arraste pra cá"
                font.pixelSize: Theme.textMd
                font.weight: Font.Medium
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 6

                Repeater {
                    model: ["YouTube", "Instagram", "TikTok", "X", "Vimeo", "+1.800"]

                    delegate: Rectangle {
                        required property string modelData

                        width: siteText.implicitWidth + 14
                        height: 22
                        radius: 11
                        color: Theme.bgElev
                        border.color: Theme.border

                        AppText {
                            id: siteText

                            anchors.centerIn: parent
                            text: parent.modelData
                            color: Theme.textMuted
                            font.pixelSize: Theme.textXs
                        }
                    }
                }
            }
        }
    }

    ColumnLayout {
        visible: Analyzer.state === "loading"
        Layout.fillWidth: true
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            Skeleton {
                Layout.preferredWidth: 168
                Layout.preferredHeight: 94
                radius: Theme.radiusMd
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 10

                Skeleton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 14
                }

                Skeleton {
                    Layout.preferredWidth: parent.width * 0.7
                    Layout.preferredHeight: 14
                }

                Skeleton {
                    Layout.preferredWidth: parent.width * 0.45
                    Layout.preferredHeight: 10
                    Layout.topMargin: 6
                }
            }
        }

        Skeleton {
            Layout.preferredWidth: 180
            Layout.preferredHeight: 34
            radius: Theme.radiusMd
        }

        Row {
            spacing: 8

            Repeater {
                model: 4

                delegate: Skeleton {
                    width: 76
                    height: 46
                    radius: Theme.radiusMd
                }
            }
        }
    }

    Rectangle {
        visible: Analyzer.state === "error"
        Layout.fillWidth: true
        Layout.preferredHeight: errorColumn.implicitHeight + 28
        radius: Theme.radiusLg
        color: Theme.withAlpha(Theme.err, 0.06)
        border.color: Theme.withAlpha(Theme.err, 0.28)

        ColumnLayout {
            id: errorColumn

            anchors.fill: parent
            anchors.margins: 14
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Icon {
                    Layout.alignment: Qt.AlignTop
                    name: "circle-alert"
                    size: 18
                    color: Theme.err
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    AppText {
                        Layout.fillWidth: true
                        text: "Não deu pra ler esse link"
                        font.weight: Font.Medium
                    }

                    AppText {
                        Layout.fillWidth: true
                        text: Analyzer.errorText
                        color: Theme.textMuted
                        font.pixelSize: Theme.textSm
                        wrapMode: Text.Wrap
                    }
                }
            }

            ScrollView {
                id: errorDetails

                property bool expanded: false

                visible: expanded && Analyzer.errorDetail !== ""
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(detailText.implicitHeight + 16, 140)

                TextArea {
                    id: detailText

                    text: Analyzer.errorDetail
                    readOnly: true
                    wrapMode: Text.WrapAnywhere
                    color: Theme.textMuted
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.textXs
                    selectByMouse: true
                    background: Rectangle {
                        radius: Theme.radiusSm
                        color: Theme.bgElev
                    }
                }
            }

            RowLayout {
                spacing: 6

                AppButton {
                    text: "Tentar de novo"
                    iconName: "rotate-cw"
                    size: "sm"
                    variant: "secondary"
                    onClicked: Analyzer.retry()
                }

                AppButton {
                    visible: Analyzer.errorText.indexOf("cookies") !== -1
                    text: "Configurar cookies"
                    iconName: "cookie"
                    size: "sm"
                    variant: "secondary"
                    onClicked: root.openSettings()
                }

                AppButton {
                    visible: Analyzer.errorDetail !== ""
                    text: errorDetails.expanded ? "Esconder detalhes" : "Ver detalhes"
                    size: "sm"
                    variant: "ghost"
                    onClicked: errorDetails.expanded = !errorDetails.expanded
                }
            }
        }
    }

    Loader {
        id: previewLoader

        active: root.ready && !root.isPlaylist
        visible: active
        Layout.fillWidth: true

        sourceComponent: MediaPreview {
            result: root.result
            onOpenPlaylist: Analyzer.analyze(Analyzer.url, true)
        }
    }

    Loader {
        id: playlistLoader

        active: root.isPlaylist
        visible: active
        Layout.fillWidth: true

        sourceComponent: PlaylistPreview {
            result: root.result
        }
    }

    Rectangle {
        visible: root.ready
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: Theme.border
    }

    FormatOptions {
        id: formatOptions

        visible: root.ready
        Layout.fillWidth: true
        qualities: root.result.qualities || []
        audioFormats: root.result.audioFormats || []
        hasVideo: root.result.hasVideo !== false
    }
}
