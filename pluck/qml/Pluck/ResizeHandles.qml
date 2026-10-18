pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root

    required property Window window
    property int edgeSize: 6
    property int cornerSize: 14

    component Handle: MouseArea {
        property int edges

        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        onPressed: root.window.startSystemResize(edges)
    }

    Handle {
        edges: Qt.LeftEdge
        cursorShape: Qt.SizeHorCursor
        x: 0
        y: root.cornerSize
        width: root.edgeSize
        height: root.height - root.cornerSize * 2
    }

    Handle {
        edges: Qt.RightEdge
        cursorShape: Qt.SizeHorCursor
        x: root.width - root.edgeSize
        y: root.cornerSize
        width: root.edgeSize
        height: root.height - root.cornerSize * 2
    }

    Handle {
        edges: Qt.TopEdge
        cursorShape: Qt.SizeVerCursor
        x: root.cornerSize
        y: 0
        width: root.width - root.cornerSize * 2
        height: root.edgeSize
    }

    Handle {
        edges: Qt.BottomEdge
        cursorShape: Qt.SizeVerCursor
        x: root.cornerSize
        y: root.height - root.edgeSize
        width: root.width - root.cornerSize * 2
        height: root.edgeSize
    }

    Handle {
        edges: Qt.LeftEdge | Qt.TopEdge
        cursorShape: Qt.SizeFDiagCursor
        width: root.cornerSize
        height: root.cornerSize
    }

    Handle {
        edges: Qt.RightEdge | Qt.TopEdge
        cursorShape: Qt.SizeBDiagCursor
        x: root.width - root.cornerSize
        width: root.cornerSize
        height: root.cornerSize
    }

    Handle {
        edges: Qt.LeftEdge | Qt.BottomEdge
        cursorShape: Qt.SizeBDiagCursor
        y: root.height - root.cornerSize
        width: root.cornerSize
        height: root.cornerSize
    }

    Handle {
        edges: Qt.RightEdge | Qt.BottomEdge
        cursorShape: Qt.SizeFDiagCursor
        x: root.width - root.cornerSize
        y: root.height - root.cornerSize
        width: root.cornerSize
        height: root.cornerSize
    }
}
