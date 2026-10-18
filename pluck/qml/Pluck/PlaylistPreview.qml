pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    required property var result
    property var checked: []

    readonly property var entries: result.entries || []
    readonly property int selectedCount: checked.filter(value => value).length

    function setAll(value) {
        checked = entries.map(() => value)
    }

    function toggle(index) {
        const next = checked.slice()
        next[index] = !next[index]
        checked = next
    }

    function selectedEntries() {
        return entries.filter((entry, index) => checked[index])
    }

    onEntriesChanged: setAll(true)
    Component.onCompleted: setAll(true)
    spacing: 14

    RowLayout {
        Layout.fillWidth: true
        spacing: 14

        Item {
            Layout.preferredWidth: 112
            Layout.preferredHeight: 70

            Rectangle {
                x: 12
                width: 88
                height: 56
                radius: Theme.radiusSm
                color: Theme.cardRaised
                border.color: Theme.border
            }

            Rectangle {
                x: 6
                y: 5
                width: 100
                height: 60
                radius: Theme.radiusSm
                color: Theme.bgElev
                border.color: Theme.border
            }

            Thumbnail {
                y: 10
                width: 112
                height: 60
                source: root.result.thumbnail || ""
                fallbackIcon: "list-video"
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            AppText {
                Layout.fillWidth: true
                text: root.result.title || ""
                font.pixelSize: Theme.textLg
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            AppText {
                Layout.fillWidth: true
                text: {
                    const parts = []
                    if (root.result.channel)
                        parts.push(root.result.channel)
                    parts.push(root.result.totalCount + (root.result.totalCount === 1 ? " vídeo" : " vídeos"))
                    return parts.join(" · ")
                }
                color: Theme.textMuted
                font.pixelSize: Theme.textSm
                elide: Text.ElideRight
            }

            AppText {
                visible: root.result.totalCount > root.entries.length
                Layout.fillWidth: true
                text: "Mostrando os primeiros " + root.entries.length
                color: Theme.warn
                font.pixelSize: Theme.textXs
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: listHeader.height + Math.min(list.contentHeight, 280) + 1
        radius: Theme.radiusMd
        color: Theme.bgElev
        border.color: Theme.border
        clip: true

        RowLayout {
            id: listHeader

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 12
            anchors.rightMargin: 6
            height: 38
            spacing: 10

            CheckMark {
                accessibleName: "Selecionar todos"
                checked: root.selectedCount === root.entries.length && root.entries.length > 0
                onClicked: root.setAll(root.selectedCount !== root.entries.length)
            }

            AppText {
                Layout.fillWidth: true
                text: root.selectedCount + " de " + root.entries.length + " selecionados"
                color: Theme.textMuted
                font.pixelSize: Theme.textSm
            }

            AppButton {
                text: "Todos"
                size: "sm"
                variant: "ghost"
                onClicked: root.setAll(true)
            }

            AppButton {
                text: "Nenhum"
                size: "sm"
                variant: "ghost"
                onClicked: root.setAll(false)
            }
        }

        Rectangle {
            anchors.top: listHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.border
        }

        ListView {
            id: list

            anchors.top: listHeader.bottom
            anchors.topMargin: 1
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.entries
            reuseItems: true

            ScrollBar.vertical: AppScrollBar {}

            delegate: Rectangle {
                id: entry

                required property var modelData
                required property int index
                readonly property bool selected: root.checked[index] === true

                width: ListView.view.width
                height: 48
                color: entryHover.hovered ? Theme.cardHover : "transparent"
                activeFocusOnTab: true

                Keys.onSpacePressed: root.toggle(entry.index)
                Keys.onReturnPressed: root.toggle(entry.index)
                Keys.onEnterPressed: root.toggle(entry.index)

                Rectangle {
                    visible: entry.activeFocus
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: Theme.radiusSm
                    color: "transparent"
                    border.width: 2
                    border.color: Theme.accent
                }

                HoverHandler {
                    id: entryHover
                }

                TapHandler {
                    onTapped: root.toggle(entry.index)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 14
                    spacing: 10

                    CheckMark {
                        accessibleName: entry.modelData.title
                        checked: entry.selected
                        onClicked: root.toggle(entry.index)
                    }

                    AppText {
                        Layout.preferredWidth: 26
                        text: entry.index + 1
                        mono: true
                        color: Theme.textDim
                        font.pixelSize: Theme.textXs
                        horizontalAlignment: Text.AlignRight
                    }

                    Thumbnail {
                        Layout.preferredWidth: 60
                        Layout.preferredHeight: 34
                        source: entry.modelData.thumbnail
                        cornerRadius: 5
                        maskColor: entry.color.a > 0 ? Theme.cardHover : Theme.bgElev
                    }

                    AppText {
                        Layout.fillWidth: true
                        text: entry.modelData.title
                        color: entry.selected ? Theme.text : Theme.textDim
                        font.pixelSize: Theme.textSm
                        elide: Text.ElideRight
                    }

                    AppText {
                        text: entry.modelData.durationText
                        mono: true
                        color: Theme.textDim
                        font.pixelSize: Theme.textXs
                    }
                }
            }
        }
    }
}
