pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root

    required property var result

    signal openPlaylist()

    spacing: 12

    RowLayout {
        Layout.fillWidth: true
        spacing: 14

        Thumbnail {
            Layout.preferredWidth: 168
            Layout.preferredHeight: 94
            Layout.alignment: Qt.AlignTop
            source: root.result.thumbnail || ""
            badge: root.result.isLive ? "AO VIVO" : root.result.durationText || ""
            cornerRadius: Theme.radiusMd
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: 8

            AppText {
                Layout.fillWidth: true
                text: root.result.title || ""
                font.pixelSize: Theme.textMd
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                lineHeight: 1.15
            }

            Repeater {
                model: [
                    { icon: "user", text: root.result.channel || "" },
                    { icon: "eye", text: [root.result.viewsText, root.result.dateText].filter(part => !!part).join(" · ") }
                ].filter(item => item.text !== "")

                delegate: RowLayout {
                    id: metaRow

                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 6

                    Icon {
                        name: metaRow.modelData.icon
                        size: 13
                        color: Theme.textDim
                    }

                    AppText {
                        Layout.fillWidth: true
                        text: metaRow.modelData.text
                        color: Theme.textMuted
                        font.pixelSize: Theme.textSm
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    Rectangle {
        visible: !!root.result.partOfPlaylist
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        radius: Theme.radiusMd
        color: Theme.withAlpha(Theme.cyan, 0.06)
        border.color: Theme.withAlpha(Theme.cyan, 0.22)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 4
            spacing: 8

            Icon {
                name: "list-video"
                size: 15
                color: Theme.cyan
            }

            AppText {
                Layout.fillWidth: true
                text: "Esse vídeo faz parte de uma playlist."
                font.pixelSize: Theme.textSm
                elide: Text.ElideRight
            }

            AppButton {
                text: "Ver playlist"
                size: "sm"
                variant: "ghost"
                onClicked: root.openPlaylist()
            }
        }
    }
}
