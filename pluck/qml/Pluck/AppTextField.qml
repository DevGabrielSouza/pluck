import QtQuick
import QtQuick.Controls

TextField {
    id: control

    property string iconName
    property bool large: false
    property bool mono: false
    property alias trailing: trailingSlot.data

    implicitHeight: large ? 44 : 36
    leftPadding: iconName !== "" ? (large ? 40 : 34) : 12
    rightPadding: trailingSlot.width > 0 ? trailingSlot.width + 12 : 12
    color: Theme.text
    placeholderTextColor: Theme.textDim
    selectionColor: Theme.withAlpha(Theme.accent, 0.35)
    selectedTextColor: "#FFFFFF"
    font.family: mono ? Theme.monoFamily : Theme.fontFamily
    font.pixelSize: large ? Theme.textMd : Theme.textBase
    verticalAlignment: TextInput.AlignVCenter
    selectByMouse: true

    background: Rectangle {
        radius: Theme.radiusMd
        color: Theme.bgElev
        border.width: 1
        border.color: control.activeFocus ? Theme.borderNeon : control.hovered ? Theme.borderStrong : Theme.border

        Rectangle {
            visible: control.activeFocus
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: 3
            border.color: Theme.withAlpha(Theme.accent, 0.16)
        }

        Icon {
            visible: control.iconName !== ""
            anchors.left: parent.left
            anchors.leftMargin: control.large ? 14 : 11
            anchors.verticalCenter: parent.verticalCenter
            name: control.iconName
            size: 16
            color: control.activeFocus ? Theme.accent : Theme.textDim
        }

        Row {
            id: trailingSlot

            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
        }
    }
}
