import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string title
    property string subtitle
    property string iconName
    property bool active: false
    property int padding: 20
    property bool stretchContent: false
    property alias headerActions: actionSlot.data
    default property alias content: body.data

    implicitHeight: layout.implicitHeight + padding * 2
    radius: Theme.radiusCard
    color: Theme.card
    border.color: active ? Theme.borderNeon : Theme.border

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: root.radius
        anchors.topMargin: 1
        height: 1
        color: "#0AFFFFFF"
    }

    ColumnLayout {
        id: layout

        anchors.fill: parent
        anchors.margins: root.padding
        spacing: 16

        RowLayout {
            visible: root.title !== ""
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                visible: root.iconName !== ""
                Layout.preferredWidth: 30
                Layout.preferredHeight: 30
                Layout.alignment: Qt.AlignTop
                radius: Theme.radiusSm
                color: Theme.bgElev
                border.color: Theme.border

                Icon {
                    anchors.centerIn: parent
                    name: root.iconName
                    color: Theme.accent
                    size: 16
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                AppText {
                    Layout.fillWidth: true
                    text: root.title
                    font.pixelSize: Theme.textMd
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }

                AppText {
                    visible: root.subtitle !== ""
                    Layout.fillWidth: true
                    text: root.subtitle
                    color: Theme.textMuted
                    font.pixelSize: Theme.textSm
                    elide: Text.ElideRight
                }
            }

            Row {
                id: actionSlot

                Layout.alignment: Qt.AlignVCenter
                spacing: 6
            }
        }

        ColumnLayout {
            id: body

            Layout.fillWidth: true
            Layout.fillHeight: root.stretchContent
            spacing: 12
        }

        Item {
            visible: !root.stretchContent
            Layout.fillHeight: true
            Layout.topMargin: -layout.spacing
        }
    }
}
