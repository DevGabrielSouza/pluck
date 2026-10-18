import QtQuick

Icon {
    id: root

    property bool running: visible

    name: "loader-circle"

    RotationAnimator on rotation {
        running: root.running
        from: 0
        to: 360
        duration: 900
        loops: Animation.Infinite
    }
}
