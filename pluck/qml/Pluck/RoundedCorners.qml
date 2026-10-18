import QtQuick
import QtQuick.Shapes

Shape {
    id: root

    property real radius: Theme.radiusSm
    property color maskColor: Theme.card

    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeWidth: -1
        fillColor: root.maskColor
        startX: 0
        startY: 0
        PathLine { x: root.radius; y: 0 }
        PathArc { x: 0; y: root.radius; radiusX: root.radius; radiusY: root.radius; direction: PathArc.Counterclockwise }
        PathLine { x: 0; y: 0 }
    }

    ShapePath {
        strokeWidth: -1
        fillColor: root.maskColor
        startX: root.width
        startY: 0
        PathLine { x: root.width; y: root.radius }
        PathArc { x: root.width - root.radius; y: 0; radiusX: root.radius; radiusY: root.radius; direction: PathArc.Counterclockwise }
        PathLine { x: root.width; y: 0 }
    }

    ShapePath {
        strokeWidth: -1
        fillColor: root.maskColor
        startX: root.width
        startY: root.height
        PathLine { x: root.width - root.radius; y: root.height }
        PathArc { x: root.width; y: root.height - root.radius; radiusX: root.radius; radiusY: root.radius; direction: PathArc.Counterclockwise }
        PathLine { x: root.width; y: root.height }
    }

    ShapePath {
        strokeWidth: -1
        fillColor: root.maskColor
        startX: 0
        startY: root.height
        PathLine { x: 0; y: root.height - root.radius }
        PathArc { x: root.radius; y: root.height; radiusX: root.radius; radiusY: root.radius; direction: PathArc.Counterclockwise }
        PathLine { x: 0; y: root.height }
    }
}
