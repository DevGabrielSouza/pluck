import QtQuick
import QtQuick.Controls

ToolTip {
    id: root

    delay: 450
    timeout: 6000
    padding: 8
    topPadding: 6
    bottomPadding: 6

    contentItem: AppText {
        text: root.text
        font.pixelSize: Theme.textSm
        wrapMode: Text.Wrap
    }

    background: Rectangle {
        color: Theme.popover
        radius: Theme.radiusSm
        border.color: Theme.borderStrong
    }
}
