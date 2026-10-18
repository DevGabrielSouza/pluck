import QtQuick

Item {
    id: root

    property string name
    property color color: Theme.textMuted
    property real size: 16

    implicitWidth: size
    implicitHeight: size
    width: size
    height: size

    Image {
        anchors.fill: parent
        sourceSize: Qt.size(root.size * 2, root.size * 2)
        source: root.name ? "image://icon/" + root.name + "/" + root.color.toString().slice(1) : ""
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }
}
