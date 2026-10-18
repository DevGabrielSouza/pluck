import QtQuick
import QtQuick.Layouts
import Pluck.Core

Item {
    id: root

    required property Window window
    property int currentPage: 0

    signal navigate(int page)

    implicitHeight: 48

    Item {
        anchors.fill: parent

        TapHandler {
            acceptedButtons: Qt.LeftButton
            onDoubleTapped: root.window.visibility === Window.Maximized ? root.window.showNormal() : root.window.showMaximized()
        }

        DragHandler {
            target: null
            onActiveChanged: if (active) root.window.startSystemMove()
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        spacing: 0

        Image {
            Layout.preferredWidth: 26
            Layout.preferredHeight: 26
            source: Qt.resolvedUrl("../../assets/pluck.svg")
            sourceSize: Qt.size(52, 52)
            smooth: true
        }

        AppText {
            Layout.leftMargin: 10
            text: "Pluck"
            font.pixelSize: Theme.textMd
            font.weight: Font.DemiBold
        }

        AppText {
            Layout.leftMargin: 8
            text: "v" + Desktop.appVersion
            mono: true
            color: Theme.textDim
            font.pixelSize: Theme.textXs
        }

        Row {
            Layout.leftMargin: 28
            spacing: 4

            NavTab {
                text: "Downloads"
                iconName: "download"
                current: root.currentPage === 0
                badge: Downloads.pendingCount
                onClicked: root.navigate(0)
            }

            NavTab {
                text: "Configurações"
                iconName: "settings"
                current: root.currentPage === 1
                onClicked: root.navigate(1)
            }
        }

        Item {
            Layout.fillWidth: true
        }

        Pill {
            visible: Downloads.runningCount > 0
            Layout.rightMargin: 12
            tone: "info"
            iconName: "zap"
            text: Downloads.totalSpeedText !== "" ? Downloads.totalSpeedText : Downloads.runningCount + " ativo" + (Downloads.runningCount > 1 ? "s" : "")
        }

        WindowControls {
            window: root.window
        }
    }
}
