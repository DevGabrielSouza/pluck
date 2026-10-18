import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string iconName
    property bool current: false
    property int badge: 0

    implicitHeight: 32
    implicitWidth: row.implicitWidth + 24
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.role: Accessible.PageTab
    Accessible.name: text
    Accessible.checked: current

    background: Rectangle {
        radius: Theme.radiusSm
        color: control.current ? Theme.accentSoft : control.hovered ? Theme.cardHover : "transparent"
        border.color: control.current ? Theme.borderNeon : "transparent"
        border.width: 1

        Behavior on color {
            ColorAnimation { duration: 120 }
        }

        Rectangle {
            visible: control.visualFocus
            anchors.fill: parent
            anchors.margins: -2
            radius: parent.radius + 2
            color: "transparent"
            border.width: 2
            border.color: Theme.accent
        }
    }

    contentItem: Item {
        Row {
            id: row

            anchors.centerIn: parent
            spacing: 7

            Icon {
                name: control.iconName
                size: 15
                color: control.current ? Theme.accentText : control.hovered ? Theme.text : Theme.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }

            AppText {
                text: control.text
                color: control.current ? Theme.accentText : control.hovered ? Theme.text : Theme.textMuted
                font.pixelSize: Theme.textBase
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }

            Rectangle {
                visible: control.badge > 0
                width: Math.max(18, badgeText.implicitWidth + 10)
                height: 18
                radius: 9
                color: Theme.accent
                anchors.verticalCenter: parent.verticalCenter

                AppText {
                    id: badgeText

                    anchors.centerIn: parent
                    text: control.badge
                    mono: true
                    color: "#FFFFFF"
                    font.pixelSize: Theme.textMicro
                    font.weight: Font.DemiBold
                }
            }
        }
    }
}
