import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string iconName
    property string hint
    property string variant: "ghost"
    property int boxSize: 32
    property int iconSize: 16
    property color tint: Theme.textMuted

    readonly property color hoverTint: variant === "danger" ? Theme.err : variant === "accent" ? Theme.accentText : Theme.text

    implicitWidth: boxSize
    implicitHeight: boxSize
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.4
    Accessible.role: Accessible.Button
    Accessible.name: hint

    background: Rectangle {
        radius: Theme.radiusSm
        color: {
            if (control.down)
                return Theme.cardRaised
            if (!control.hovered)
                return control.variant === "secondary" ? Theme.card : "transparent"
            if (control.variant === "danger")
                return Theme.withAlpha(Theme.err, 0.12)
            if (control.variant === "accent")
                return Theme.accentSoft
            return Theme.cardHover
        }
        border.width: control.variant === "secondary" ? 1 : 0
        border.color: control.hovered ? Theme.borderStrong : Theme.border

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
        Icon {
            anchors.centerIn: parent
            name: control.iconName
            size: control.iconSize
            color: control.hovered ? control.hoverTint : control.tint
        }
    }

    Hint {
        visible: control.hint !== "" && (control.hovered || control.visualFocus)
        text: control.hint
    }
}
