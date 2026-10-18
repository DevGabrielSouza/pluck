import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root

    property string label
    property string description
    property alias control: controlSlot.data

    Layout.fillWidth: true
    spacing: 16

    ColumnLayout {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
        spacing: 3

        AppText {
            Layout.fillWidth: true
            text: root.label
            font.weight: Font.Medium
            wrapMode: Text.Wrap
        }

        AppText {
            visible: root.description !== ""
            Layout.fillWidth: true
            text: root.description
            color: Theme.textMuted
            font.pixelSize: Theme.textSm
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
    }

    Item {
        id: controlSlot

        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
        implicitWidth: childrenRect.width
        implicitHeight: childrenRect.height
    }
}
