import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string accessibleName

    checkable: true
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: 18
    implicitHeight: 18
    Accessible.role: Accessible.CheckBox
    Accessible.name: accessibleName
    Accessible.checked: checked

    background: Rectangle {
        radius: 5
        color: control.checked ? Theme.accent : control.hovered ? Theme.cardHover : "transparent"
        border.color: control.checked ? Theme.accent : control.hovered ? Theme.textDim : Theme.borderStrong
        border.width: 1.5

        Behavior on color {
            ColorAnimation { duration: 100 }
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
    }

    contentItem: Item {
        Icon {
            anchors.centerIn: parent
            visible: control.checked
            name: "check"
            size: 12
            color: "#FFFFFF"
        }
    }
}
