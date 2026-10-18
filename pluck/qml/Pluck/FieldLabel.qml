import QtQuick

Row {
    id: root

    property string text
    property string iconName

    spacing: 6

    Icon {
        visible: root.iconName !== ""
        name: root.iconName
        size: 12
        color: Theme.textMuted
        anchors.verticalCenter: parent.verticalCenter
    }

    AppText {
        text: root.text
        micro: true
        anchors.verticalCenter: parent.verticalCenter
    }
}
