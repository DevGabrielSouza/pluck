import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string detail
    property string iconName
    property bool selected: false
    property bool reserveDetail: false

    implicitHeight: detail !== "" || reserveDetail ? 46 : 36
    implicitWidth: Math.max(72, content.implicitWidth + 28)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.RadioButton
    Accessible.name: text + (detail !== "" ? ", " + detail : "")
    Accessible.checked: selected

    background: Rectangle {
        radius: Theme.radiusMd
        color: control.selected ? Theme.accentSoft : control.hovered ? Theme.cardHover : Theme.card
        border.color: control.selected ? Theme.borderNeon : control.hovered ? Theme.borderStrong : Theme.border
        border.width: 1

        Behavior on color {
            ColorAnimation { duration: 120 }
        }

        Rectangle {
            visible: control.visualFocus
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: 2
            border.color: Theme.accent
        }

        Rectangle {
            visible: control.selected
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 5
            width: 14
            height: 14
            radius: 7
            color: Theme.accent

            Icon {
                anchors.centerIn: parent
                name: "check"
                size: 10
                color: "#FFFFFF"
            }
        }
    }

    contentItem: Item {
        Column {
            id: content

            anchors.centerIn: parent
            spacing: 1

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 6

                Icon {
                    visible: control.iconName !== ""
                    name: control.iconName
                    size: 14
                    color: control.selected ? Theme.accentText : Theme.textMuted
                    anchors.verticalCenter: parent.verticalCenter
                }

                AppText {
                    text: control.text
                    color: control.selected ? Theme.text : control.hovered ? Theme.text : Theme.textMuted
                    font.pixelSize: Theme.textBase
                    font.weight: Font.Medium
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            AppText {
                visible: control.detail !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: control.detail
                color: control.selected ? Theme.accentText : Theme.textDim
                mono: true
                font.pixelSize: Theme.textMicro
            }
        }
    }
}
