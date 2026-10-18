import QtQuick

Item {
    id: root

    property string tone: "ok"
    property bool pulse: false
    property int dotSize: 6

    readonly property color toneColor: Theme.tone(tone)

    implicitWidth: dotSize
    implicitHeight: dotSize

    Rectangle {
        anchors.centerIn: parent
        width: root.dotSize * 2.4
        height: width
        radius: width / 2
        color: Theme.withAlpha(root.toneColor, 0.22)
        visible: root.tone !== "idle"
    }

    Rectangle {
        id: dot

        anchors.centerIn: parent
        width: root.dotSize
        height: root.dotSize
        radius: root.dotSize / 2
        color: root.toneColor

        SequentialAnimation on opacity {
            running: root.pulse && root.visible
            loops: Animation.Infinite
            alwaysRunToEnd: true
            NumberAnimation { from: 1; to: 0.45; duration: 900; easing.type: Easing.InOutSine }
            NumberAnimation { from: 0.45; to: 1; duration: 900; easing.type: Easing.InOutSine }
        }
    }
}
