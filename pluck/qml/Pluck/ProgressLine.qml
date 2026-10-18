import QtQuick

Rectangle {
    id: root

    property real value: 0
    property bool indeterminate: false
    property bool shimmer: false
    property color tone: Theme.accent
    property color toneEnd: Theme.cyan

    implicitHeight: 4
    radius: height / 2
    color: Theme.track
    clip: true
    Accessible.role: Accessible.ProgressBar
    Accessible.description: indeterminate ? "indeterminado" : Math.round(Math.max(0, Math.min(1, value)) * 100) + "%"

    Rectangle {
        id: fill

        visible: !root.indeterminate
        width: root.width * Math.max(0, Math.min(1, root.value))
        height: root.height
        radius: root.radius
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: root.tone }
            GradientStop { position: 1; color: root.toneEnd }
        }

        Behavior on width {
            NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
        }

        Rectangle {
            id: sheen

            visible: root.shimmer && fill.width > 24
            width: 72
            height: parent.height
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#00FFFFFF" }
                GradientStop { position: 0.5; color: "#66FFFFFF" }
                GradientStop { position: 1; color: "#00FFFFFF" }
            }

            NumberAnimation on x {
                running: sheen.visible
                from: -72
                to: Math.max(fill.width, 72)
                duration: 1400
                loops: Animation.Infinite
            }
        }
    }

    Rectangle {
        id: runner

        visible: root.indeterminate
        width: root.width * 0.28
        height: root.height
        radius: root.radius
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.withAlpha(root.tone, 0) }
            GradientStop { position: 0.5; color: root.tone }
            GradientStop { position: 1; color: Theme.withAlpha(root.toneEnd, 0) }
        }

        NumberAnimation on x {
            running: runner.visible
            from: -runner.width
            to: root.width
            duration: 1200
            loops: Animation.Infinite
            easing.type: Easing.InOutQuad
        }
    }
}
