import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string accessibleName

    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: 38
    implicitHeight: 22
    Accessible.role: Accessible.CheckBox
    Accessible.name: accessibleName
    Accessible.checked: checked

    background: Rectangle {
        radius: height / 2
        color: control.checked ? Theme.accent : Theme.track
        border.color: control.checked ? Theme.accentHover : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color {
            ColorAnimation { duration: 140 }
        }

        Rectangle {
            visible: control.visualFocus
            anchors.fill: parent
            anchors.margins: -3
            radius: height / 2
            color: "transparent"
            border.width: 2
            border.color: Theme.accent
        }
    }

    contentItem: Item {
        Rectangle {
            width: 16
            height: 16
            radius: 8
            y: (parent.height - height) / 2
            x: control.checked ? parent.width - width - 3 : 3
            color: control.checked ? "#FFFFFF" : Theme.textMuted

            Behavior on x {
                NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
            }
        }
    }
}
