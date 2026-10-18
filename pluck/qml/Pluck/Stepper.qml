import QtQuick

Rectangle {
    id: root

    property int value: 1
    property int from: 1
    property int to: 10
    property string accessibleName

    signal valueModified(int value)

    implicitWidth: 132
    implicitHeight: 36
    radius: Theme.radiusMd
    color: Theme.bgElev
    border.color: Theme.border
    Accessible.role: Accessible.SpinBox
    Accessible.name: accessibleName
    Accessible.description: String(value)

    IconButton {
        anchors.left: parent.left
        anchors.leftMargin: 2
        anchors.verticalCenter: parent.verticalCenter
        iconName: "minus"
        hint: "Diminuir"
        iconSize: 14
        enabled: root.value > root.from
        onClicked: root.valueModified(root.value - 1)
    }

    AppText {
        anchors.centerIn: parent
        text: root.value
        mono: true
        font.pixelSize: Theme.textMd
        font.weight: Font.Medium
    }

    IconButton {
        anchors.right: parent.right
        anchors.rightMargin: 2
        anchors.verticalCenter: parent.verticalCenter
        iconName: "plus"
        hint: "Aumentar"
        iconSize: 14
        enabled: root.value < root.to
        onClicked: root.valueModified(root.value + 1)
    }
}
