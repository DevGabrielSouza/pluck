import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property string variant: "secondary"
    property string size: "md"
    property string iconName
    property bool loading: false
    property string hint

    readonly property int controlHeight: size === "sm" ? 30 : size === "lg" ? 42 : 36
    readonly property bool filled: variant === "primary" || variant === "destructive"
    readonly property color foreground: {
        if (filled)
            return "#FFFFFF"
        if (variant === "ghost")
            return hovered ? Theme.text : Theme.textMuted
        if (variant === "outline")
            return hovered ? Theme.accentText : Theme.text
        return Theme.text
    }
    readonly property color surface: {
        switch (variant) {
        case "primary":
            return down ? Theme.accentPressed : hovered ? Theme.accentHover : Theme.accent
        case "destructive":
            return down ? "#DC2626" : hovered ? Theme.err : Theme.withAlpha(Theme.err, 0.9)
        case "secondary":
            return hovered ? Theme.cardHover : Theme.card
        case "ghost":
            return hovered ? Theme.cardHover : "transparent"
        default:
            return "transparent"
        }
    }

    implicitHeight: controlHeight
    implicitWidth: Math.max(controlHeight, contentRow.implicitWidth + leftPadding + rightPadding)
    leftPadding: text ? (size === "sm" ? 12 : size === "lg" ? 20 : 16) : 0
    rightPadding: leftPadding
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    opacity: enabled ? 1 : 0.45
    scale: down && filled ? 0.98 : 1
    font.family: Theme.fontFamily
    font.pixelSize: size === "sm" ? Theme.textSm : Theme.textBase
    font.weight: Font.Medium
    Accessible.role: Accessible.Button
    Accessible.name: text !== "" ? text : hint

    Behavior on scale {
        NumberAnimation { duration: 90 }
    }

    background: Rectangle {
        radius: Theme.radiusMd
        color: control.surface
        border.width: control.variant === "secondary" || control.variant === "outline" ? 1 : 0
        border.color: control.variant === "outline" && control.hovered ? Theme.accent : control.hovered ? Theme.borderStrong : Theme.border

        Behavior on color {
            ColorAnimation { duration: 120 }
        }

        Rectangle {
            visible: control.variant === "primary"
            anchors.fill: parent
            anchors.margins: -2
            radius: parent.radius + 2
            color: "transparent"
            border.width: 2
            border.color: control.hovered ? Theme.withAlpha(Theme.accent, 0.35) : Theme.withAlpha(Theme.accent, 0.18)
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
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow

            anchors.centerIn: parent
            spacing: 8

            Spinner {
                visible: control.loading
                size: control.size === "sm" ? 14 : 16
                color: control.foreground
                anchors.verticalCenter: parent.verticalCenter
            }

            Icon {
                visible: !control.loading && control.iconName !== ""
                name: control.iconName
                size: control.size === "sm" ? 14 : 16
                color: control.foreground
                anchors.verticalCenter: parent.verticalCenter
            }

            AppText {
                visible: control.text !== ""
                text: control.text
                font: control.font
                color: control.foreground
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    Hint {
        visible: control.hint !== "" && control.hovered
        text: control.hint
    }
}
