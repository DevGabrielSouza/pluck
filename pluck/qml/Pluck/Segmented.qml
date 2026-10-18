pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property var options: []
    property var counts: ({})
    property var value
    property bool compact: false

    signal activated(var value)

    implicitWidth: row.implicitWidth + 6
    implicitHeight: compact ? 30 : 34
    radius: Theme.radiusMd
    color: Theme.bgElev
    border.color: Theme.border

    Row {
        id: row

        anchors.centerIn: parent
        spacing: 2

        Repeater {
            model: root.options

            delegate: AbstractButton {
                id: option

                required property var modelData
                readonly property bool selected: modelData.value === root.value
                readonly property var count: root.counts[modelData.value] !== undefined ? root.counts[modelData.value] : modelData.count

                height: root.implicitHeight - 6
                implicitWidth: optionRow.implicitWidth + (root.compact ? 18 : 24)
                text: modelData.label
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.RadioButton
                Accessible.name: modelData.label + (option.count !== undefined ? ", " + option.count : "")
                Accessible.checked: selected
                onClicked: root.activated(modelData.value)

                background: Rectangle {
                    radius: Theme.radiusSm
                    color: option.selected ? Theme.accent : option.hovered ? Theme.cardHover : "transparent"
                    border.width: option.visualFocus ? 2 : 0
                    border.color: option.selected ? Theme.accentText : Theme.accentHover

                    Behavior on color {
                        ColorAnimation { duration: 120 }
                    }
                }

                contentItem: Item {
                    Row {
                        id: optionRow

                        anchors.centerIn: parent
                        spacing: 6

                        Icon {
                            visible: !!option.modelData.icon
                            name: option.modelData.icon || ""
                            size: 14
                            color: option.selected ? "#FFFFFF" : option.hovered ? Theme.text : Theme.textMuted
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        AppText {
                            text: option.modelData.label
                            color: option.selected ? "#FFFFFF" : option.hovered ? Theme.text : Theme.textMuted
                            font.pixelSize: root.compact ? Theme.textSm : Theme.textBase
                            font.weight: Font.Medium
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Rectangle {
                            visible: option.count !== undefined && option.count > 0
                            width: Math.max(18, countText.implicitWidth + 10)
                            height: 16
                            radius: 8
                            color: option.selected ? "#33FFFFFF" : Theme.track
                            anchors.verticalCenter: parent.verticalCenter

                            AppText {
                                id: countText

                                anchors.centerIn: parent
                                text: option.count !== undefined ? option.count : ""
                                mono: true
                                font.pixelSize: Theme.textMicro
                                color: option.selected ? "#FFFFFF" : Theme.textMuted
                            }
                        }
                    }
                }
            }
        }
    }
}
