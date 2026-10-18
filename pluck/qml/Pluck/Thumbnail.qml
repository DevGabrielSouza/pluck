import QtQuick

Rectangle {
    id: root

    property string source
    property string badge
    property string fallbackIcon: "film"
    property color maskColor: Theme.card
    property real cornerRadius: Theme.radiusSm

    color: Theme.bgElev
    clip: true

    Icon {
        anchors.centerIn: parent
        visible: image.status !== Image.Ready
        name: root.fallbackIcon
        size: Math.min(28, root.height * 0.36)
        color: Theme.textDim
    }

    Image {
        id: image

        anchors.fill: parent
        source: root.source
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        smooth: true
        mipmap: true
        sourceSize.width: Math.max(1, root.width) * 2
        opacity: status === Image.Ready ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: 180 }
        }
    }

    Rectangle {
        visible: root.badge !== ""
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 5
        width: badgeText.implicitWidth + 10
        height: 18
        radius: 5
        color: "#CC05080F"

        AppText {
            id: badgeText

            anchors.centerIn: parent
            text: root.badge
            mono: true
            font.pixelSize: Theme.textMicro
            font.weight: Font.Medium
            color: "#FFFFFF"
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: "#14FFFFFF"
        radius: root.cornerRadius
    }

    RoundedCorners {
        anchors.fill: parent
        radius: root.cornerRadius
        maskColor: root.maskColor
    }
}
