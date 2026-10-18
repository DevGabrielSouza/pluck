pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Pluck.Core

Flickable {
    id: root

    readonly property var qualityChoices: [
        { value: 0, label: "Melhor" },
        { value: 2160, label: "4K" },
        { value: 1440, label: "1440p" },
        { value: 1080, label: "1080p" },
        { value: 720, label: "720p" },
        { value: 480, label: "480p" }
    ]
    readonly property var browserChoices: [
        { value: "", label: "Desativado" },
        { value: "firefox", label: "Firefox" },
        { value: "chrome", label: "Chrome" },
        { value: "chromium", label: "Chromium" },
        { value: "brave", label: "Brave" },
        { value: "edge", label: "Edge" },
        { value: "vivaldi", label: "Vivaldi" },
        { value: "opera", label: "Opera" }
    ]
    readonly property var templatePresets: [
        { value: "%(title)s [%(id)s].%(ext)s", label: "Título [id]" },
        { value: "%(title)s.%(ext)s", label: "Título" },
        { value: "%(channel)s - %(title)s.%(ext)s", label: "Canal - Título" },
        { value: "%(upload_date)s - %(title)s.%(ext)s", label: "Data - Título" },
        { value: "%(channel)s/%(title)s.%(ext)s", label: "Pasta por canal" }
    ]

    contentHeight: column.implicitHeight + 40
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    ScrollBar.vertical: AppScrollBar {}

    ColumnLayout {
        id: column

        width: Math.min(root.width - 40, 1100)
        x: (root.width - width) / 2
        y: 20
        spacing: 20

        ColumnLayout {
            spacing: 4

            AppText {
                text: "Configurações"
                font.pixelSize: Theme.textXl
                font.weight: Font.DemiBold
            }

            AppText {
                text: "Valem pros próximos downloads. Os que já estão na fila mantêm o que foi escolhido."
                color: Theme.textMuted
                font.pixelSize: Theme.textSm
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 980 ? 2 : 1
            columnSpacing: 20
            rowSpacing: 20

            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Pasta de destino"
                subtitle: "Onde os arquivos são salvos"
                iconName: "folder"

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    radius: Theme.radiusMd
                    color: Theme.bgElev
                    border.color: Theme.border

                    AppText {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        text: Desktop.shortPath(AppSettings.folder)
                        mono: true
                        font.pixelSize: Theme.textSm
                        elide: Text.ElideMiddle
                    }
                }

                RowLayout {
                    spacing: 8

                    AppButton {
                        text: "Alterar"
                        iconName: "folder"
                        variant: "secondary"
                        onClicked: folderDialog.open()
                    }

                    AppButton {
                        text: "Abrir"
                        iconName: "external-link"
                        variant: "ghost"
                        onClicked: Desktop.openFolder(AppSettings.folder)
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Fila"
                subtitle: "Quantos downloads rodam ao mesmo tempo"
                iconName: "layers"

                SettingRow {
                    label: "Downloads simultâneos"
                    description: "Mais de 3 costuma não acelerar nada e pode irritar o site."
                    control: Stepper {
                        accessibleName: "Downloads simultâneos"
                        value: AppSettings.maxConcurrent
                        from: 1
                        to: 6
                        onValueModified: value => AppSettings.maxConcurrent = value
                    }
                }

                Divider {}

                SettingRow {
                    label: "Avisar quando terminar"
                    description: "Notificação do sistema quando o Pluck está em segundo plano."
                    control: ToggleSwitch {
                        accessibleName: "Avisar quando terminar"
                        checked: AppSettings.notifyOnFinish
                        onToggled: AppSettings.notifyOnFinish = checked
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Padrões do novo download"
                subtitle: "O que vem selecionado quando você analisa um link"
                iconName: "sliders-horizontal"

                FieldLabel {
                    text: "Formato"
                }

                Segmented {
                    options: [{ value: "video", label: "Vídeo", icon: "film" }, { value: "audio", label: "Só áudio", icon: "music" }]
                    value: AppSettings.defaultMode
                    onActivated: value => AppSettings.defaultMode = value
                }

                FieldLabel {
                    Layout.topMargin: 4
                    text: "Qualidade do vídeo"
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.qualityChoices

                        delegate: ChoiceChip {
                            required property var modelData

                            text: modelData.label
                            selected: AppSettings.defaultQuality === modelData.value
                            onClicked: AppSettings.defaultQuality = modelData.value
                        }
                    }
                }

                RowLayout {
                    Layout.topMargin: 4
                    spacing: 24

                    ColumnLayout {
                        spacing: 8

                        FieldLabel {
                            text: "Container"
                        }

                        Segmented {
                            compact: true
                            options: [{ value: "mp4", label: "MP4" }, { value: "mkv", label: "MKV" }]
                            value: AppSettings.defaultContainer
                            onActivated: value => AppSettings.defaultContainer = value
                        }
                    }

                    ColumnLayout {
                        spacing: 8

                        FieldLabel {
                            text: "Áudio"
                        }

                        Segmented {
                            compact: true
                            options: [{ value: "mp3", label: "MP3" }, { value: "m4a", label: "M4A" }, { value: "opus", label: "Opus" }]
                            value: AppSettings.defaultAudioFormat
                            onActivated: value => AppSettings.defaultAudioFormat = value
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Arquivo final"
                subtitle: "O que vai embutido no arquivo"
                iconName: "file-text"

                SettingRow {
                    label: "Capa"
                    description: "A thumbnail vira a capa do arquivo."
                    control: ToggleSwitch {
                        accessibleName: "Capa"
                        checked: AppSettings.embedThumbnail
                        onToggled: AppSettings.embedThumbnail = checked
                    }
                }

                Divider {}

                SettingRow {
                    label: "Metadados"
                    description: "Título, canal, data e descrição."
                    control: ToggleSwitch {
                        accessibleName: "Metadados"
                        checked: AppSettings.embedMetadata
                        onToggled: AppSettings.embedMetadata = checked
                    }
                }

                Divider {}

                SettingRow {
                    label: "Capítulos"
                    description: "Marcadores de capítulo, quando o vídeo tiver."
                    control: ToggleSwitch {
                        accessibleName: "Capítulos"
                        checked: AppSettings.embedChapters
                        onToggled: AppSettings.embedChapters = checked
                    }
                }

                Divider {}

                SettingRow {
                    label: "Legendas"
                    description: "Português e inglês, quando existirem. Só em vídeo."
                    control: ToggleSwitch {
                        accessibleName: "Legendas"
                        checked: AppSettings.subtitles
                        onToggled: AppSettings.subtitles = checked
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Cookies do navegador"
                subtitle: "Pra vídeos que pedem login"
                iconName: "cookie"

                AppText {
                    Layout.fillWidth: true
                    text: "Use quando o YouTube pedir pra confirmar que você não é um robô, ou em vídeos com restrição de idade e de membros. O navegador escolhido precisa estar logado no site."
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                    wrapMode: Text.Wrap
                    lineHeight: 1.2
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.browserChoices

                        delegate: ChoiceChip {
                            required property var modelData

                            text: modelData.label
                            selected: AppSettings.cookiesBrowser === modelData.value
                            onClicked: AppSettings.cookiesBrowser = modelData.value
                        }
                    }
                }
            }

            Card {
                id: templateCard

                readonly property string preview: AppSettings.previewFilename(AppSettings.filenameTemplate)
                readonly property bool missingExtension: AppSettings.filenameTemplate.indexOf("%(ext)s") === -1
                readonly property bool missingId: !AppSettings.namesTheId(AppSettings.filenameTemplate)
                readonly property bool unsafe: !AppSettings.isFilenameTemplateSafe(AppSettings.filenameTemplate)
                readonly property string warning: unsafe
                    ? "O modelo não pode sair da pasta de destino: não comece com / ou ~, não use .. e não formate campos usados como pasta. O padrão vai ser usado."
                    : missingExtension ? "Inclua %(ext)s no fim, senão o arquivo fica sem extensão."
                    : missingId ? "Sem %(id)s no nome, um arquivo da pasta com o mesmo nome conta como já baixado e pode ser convertido ou apagado." : ""

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.alignment: Qt.AlignTop
                title: "Nome do arquivo"
                subtitle: "Modelo no formato do yt-dlp"
                iconName: "tag"

                AppTextField {
                    id: templateField

                    Layout.fillWidth: true
                    mono: true
                    text: AppSettings.filenameTemplate
                    onTextEdited: AppSettings.filenameTemplate = text
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 6

                    Repeater {
                        model: root.templatePresets

                        delegate: ChoiceChip {
                            required property var modelData

                            implicitHeight: 30
                            text: modelData.label
                            selected: AppSettings.filenameTemplate === modelData.value
                            onClicked: AppSettings.filenameTemplate = modelData.value
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Icon {
                        name: templateCard.warning !== "" ? "circle-alert" : "file-text"
                        size: 13
                        color: templateCard.warning !== "" ? Theme.warn : Theme.textDim
                    }

                    AppText {
                        Layout.fillWidth: true
                        text: templateCard.warning !== "" ? templateCard.warning : templateCard.preview
                        color: templateCard.warning !== "" ? Theme.warn : Theme.textMuted
                        mono: templateCard.warning === ""
                        wrapMode: templateCard.warning !== "" ? Text.WordWrap : Text.NoWrap
                        font.pixelSize: Theme.textXs
                        elide: Text.ElideMiddle
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true
            title: "Sobre"
            subtitle: "Pluck " + Desktop.appVersion + " · interface pro yt-dlp"
            iconName: "info"

            GridLayout {
                columns: 2
                columnSpacing: 24
                rowSpacing: 8

                AppText {
                    text: "yt-dlp"
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                }

                AppText {
                    text: Desktop.ytdlpVersion !== "" ? Desktop.ytdlpVersion : "não encontrado"
                    mono: true
                    color: Desktop.ytdlpVersion !== "" ? Theme.text : Theme.err
                    font.pixelSize: Theme.textSm
                }

                AppText {
                    text: "ffmpeg"
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                }

                AppText {
                    text: Desktop.ffmpegVersion !== "" ? Desktop.ffmpegVersion : "não encontrado"
                    mono: true
                    color: Desktop.ffmpegVersion !== "" ? Theme.text : Theme.warn
                    font.pixelSize: Theme.textSm
                }

                AppText {
                    text: "Atualizar"
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                }

                AppText {
                    text: "sudo dnf upgrade yt-dlp"
                    mono: true
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                }
            }
        }
    }

    FolderDialog {
        id: folderDialog

        title: "Pasta de destino"
        currentFolder: Desktop.fileUrl(AppSettings.folder)
        onAccepted: AppSettings.folder = Desktop.localPath(selectedFolder.toString())
    }
}
