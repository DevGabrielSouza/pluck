import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    implicitWidth: 10
    padding: 2
    policy: size < 1 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

    contentItem: Rectangle {
        implicitWidth: 6
        radius: 3
        color: control.pressed ? "#33FFFFFF" : control.hovered ? "#24FFFFFF" : "#1AFFFFFF"
        opacity: control.active || control.hovered ? 1 : 0.35

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
    }

    background: Item {}
}
