import QtQuick

Rectangle {
    id: root

    property string text
    property string tone: "idle"
    property bool dot: true
    property bool pulse: false
    property string iconName

    readonly property color toneColor: tone === "idle" ? Theme.textMuted : Theme.tone(tone)

    implicitWidth: row.implicitWidth + 16
    implicitHeight: 22
    radius: height / 2
    color: Theme.withAlpha(toneColor, tone === "idle" ? 0.08 : 0.12)
    border.color: Theme.withAlpha(toneColor, tone === "idle" ? 0.16 : 0.32)

    Row {
        id: row

        anchors.centerIn: parent
        spacing: 6

        StatusDot {
            visible: root.dot && root.iconName === ""
            tone: root.tone
            pulse: root.pulse
            anchors.verticalCenter: parent.verticalCenter
        }

        Icon {
            visible: root.iconName !== ""
            name: root.iconName
            color: root.toneColor
            size: 12
            anchors.verticalCenter: parent.verticalCenter
        }

        AppText {
            text: root.text
            color: root.toneColor
            font.pixelSize: Theme.textXs
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
