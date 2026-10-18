import QtQuick

Rectangle {
    id: root

    radius: Theme.radiusSm
    color: "#0DFFFFFF"
    clip: true

    Rectangle {
        id: wave

        width: root.width * 0.6
        height: root.height
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#00FFFFFF" }
            GradientStop { position: 0.5; color: "#0FFFFFFF" }
            GradientStop { position: 1; color: "#00FFFFFF" }
        }

        NumberAnimation on x {
            running: root.visible
            from: -wave.width
            to: root.width
            duration: 1400
            loops: Animation.Infinite
        }
    }
}
