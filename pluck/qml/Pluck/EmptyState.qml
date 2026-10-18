import QtQuick

Column {
    id: root

    property string iconName: "inbox"
    property string title
    property string description

    spacing: 10

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        width: 48
        height: 48
        radius: 14
        color: Theme.bgElev
        border.color: Theme.border

        Icon {
            anchors.centerIn: parent
            name: root.iconName
            size: 22
            color: Theme.textDim
        }
    }

    AppText {
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.title
        font.pixelSize: Theme.textMd
        font.weight: Font.Medium
    }

    AppText {
        visible: root.description !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(implicitWidth, 320)
        text: root.description
        color: Theme.textMuted
        font.pixelSize: Theme.textSm
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }
}
