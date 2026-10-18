pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

Row {
    id: root

    required property Window window
    readonly property bool maximized: window.visibility === Window.Maximized

    component ControlButton: AbstractButton {
        id: control

        property string iconName
        property string accessibleName
        property bool danger: false

        width: 44
        height: 48
        hoverEnabled: true
        focusPolicy: Qt.TabFocus
        Accessible.role: Accessible.Button
        Accessible.name: accessibleName

        background: Rectangle {
            color: control.hovered ? (control.danger ? Theme.err : Theme.cardHover) : "transparent"

            Behavior on color {
                ColorAnimation { duration: 100 }
            }

            Rectangle {
                visible: control.visualFocus
                anchors.fill: parent
                anchors.margins: -2
                color: "transparent"
                border.width: 2
                border.color: Theme.accent
            }
        }

        contentItem: Item {
            Icon {
                anchors.centerIn: parent
                name: control.iconName
                size: 14
                color: control.hovered ? (control.danger ? "#FFFFFF" : Theme.text) : Theme.textMuted
            }
        }
    }

    ControlButton {
        iconName: "minus"
        accessibleName: "Minimizar"
        onClicked: root.window.showMinimized()
    }

    ControlButton {
        iconName: root.maximized ? "minimize-2" : "square"
        accessibleName: root.maximized ? "Restaurar" : "Maximizar"
        onClicked: root.maximized ? root.window.showNormal() : root.window.showMaximized()
    }

    ControlButton {
        iconName: "x"
        accessibleName: "Fechar"
        danger: true
        onClicked: root.window.close()
    }
}
