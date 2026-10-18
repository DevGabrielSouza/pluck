pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root

    property var qualities: []
    property var audioFormats: []
    property bool hasVideo: true
    property string mode: "video"
    property int quality: 0
    property string container: "mp4"
    property string audioFormat: "mp3"

    readonly property bool qualitiesHaveSizes: qualities.some(choice => choice.size > 0)
    readonly property bool audioHasSizes: audioFormats.some(choice => choice.size > 0)
    readonly property var selectedQuality: qualities.find(choice => choice.value === quality)
    readonly property var selectedAudio: audioFormats.find(choice => choice.value === audioFormat)
    readonly property real estimatedSize: {
        if (mode === "audio")
            return selectedAudio ? selectedAudio.size : 0
        if (!selectedQuality)
            return 0
        return container === "mkv" ? selectedQuality.sizeMkv || 0 : selectedQuality.size
    }

    spacing: 16

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 8

        FieldLabel {
            text: "Formato"
        }

        Segmented {
            options: root.hasVideo
                ? [{ value: "video", label: "Vídeo", icon: "film" }, { value: "audio", label: "Só áudio", icon: "music" }]
                : [{ value: "audio", label: "Só áudio", icon: "music" }]
            value: root.mode
            onActivated: value => root.mode = value
        }
    }

    ColumnLayout {
        visible: root.mode === "video"
        Layout.fillWidth: true
        spacing: 8

        RowLayout {
            Layout.fillWidth: true

            FieldLabel {
                text: "Qualidade"
            }

            Item {
                Layout.fillWidth: true
            }

            Segmented {
                compact: true
                options: [{ value: "mp4", label: "MP4" }, { value: "mkv", label: "MKV" }]
                value: root.container
                onActivated: value => root.container = value
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: root.qualities

                delegate: ChoiceChip {
                    required property var modelData

                    text: modelData.label
                    detail: root.container === "mkv" ? modelData.sizeMkvText || "" : modelData.sizeText
                    reserveDetail: root.qualitiesHaveSizes
                    selected: modelData.value === root.quality
                    onClicked: root.quality = modelData.value
                }
            }
        }

        AppText {
            Layout.fillWidth: true
            text: root.container === "mp4"
                ? "MP4 abre em qualquer player e celular."
                : "MKV guarda o melhor codec disponível, sem conversão."
            color: Theme.textDim
            font.pixelSize: Theme.textSm
            wrapMode: Text.Wrap
        }
    }

    ColumnLayout {
        visible: root.mode === "audio"
        Layout.fillWidth: true
        spacing: 8

        FieldLabel {
            text: "Arquivo de áudio"
        }

        Flow {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: root.audioFormats

                delegate: ChoiceChip {
                    required property var modelData

                    text: modelData.label
                    detail: modelData.sizeText
                    reserveDetail: root.audioHasSizes
                    selected: modelData.value === root.audioFormat
                    onClicked: root.audioFormat = modelData.value
                }
            }
        }

        AppText {
            Layout.fillWidth: true
            text: ({
                mp3: "MP3 toca em qualquer lugar. Convertido na melhor qualidade.",
                m4a: "M4A (AAC) é menor e mantém a qualidade original do YouTube.",
                opus: "Opus é o áudio original do YouTube, sem conversão."
            })[root.audioFormat]
            color: Theme.textDim
            font.pixelSize: Theme.textSm
            wrapMode: Text.Wrap
        }
    }
}
