pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

Item {
    id: root

    property int nextId: 1
    property var actions: ({})

    function show(tone, title, message, actionText, action) {
        const toastId = nextId++
        if (action)
            actions[toastId] = action
        toasts.append({ toastId: toastId, tone: tone, title: title, message: message || "", actionText: actionText || "" })
        if (toasts.count > 4)
            dismiss(toasts.get(0).toastId)
    }

    function dismiss(toastId) {
        for (let index = 0; index < toasts.count; index++) {
            if (toasts.get(index).toastId === toastId) {
                toasts.remove(index)
                break
            }
        }
        delete actions[toastId]
    }

    ListModel {
        id: toasts
    }

    Column {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 8

        move: Transition {
            NumberAnimation { properties: "y"; duration: 180; easing.type: Easing.OutCubic }
        }

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180 }
        }

        Repeater {
            model: toasts

            delegate: Rectangle {
                id: toast

                required property int toastId
                required property string tone
                required property string title
                required property string message
                required property string actionText

                readonly property color toneColor: Theme.tone(tone)
                readonly property bool containsActiveFocus: {
                    let item = toast.Window.activeFocusItem
                    while (item !== null) {
                        if (item === toast)
                            return true
                        item = item.parent
                    }
                    return false
                }

                width: 360
                height: content.implicitHeight + 24
                radius: Theme.radiusLg
                color: Theme.popover
                border.color: Theme.borderStrong
                Accessible.role: Accessible.AlertMessage
                Accessible.name: title + ". " + message

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 10
                    width: 3
                    radius: 1.5
                    color: toast.toneColor
                }

                Timer {
                    interval: toast.actionText !== "" ? 8000 : 4500
                    running: !toastHover.hovered && !toast.containsActiveFocus
                    onTriggered: root.dismiss(toast.toastId)
                }

                HoverHandler {
                    id: toastHover
                }

                RowLayout {
                    id: content

                    anchors.fill: parent
                    anchors.leftMargin: 24
                    anchors.rightMargin: 8
                    anchors.topMargin: 12
                    anchors.bottomMargin: 12
                    spacing: 10

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppText {
                            Layout.fillWidth: true
                            text: toast.title
                            font.weight: Font.Medium
                            elide: Text.ElideRight
                        }

                        AppText {
                            visible: toast.message !== ""
                            Layout.fillWidth: true
                            text: toast.message
                            color: Theme.textMuted
                            font.pixelSize: Theme.textSm
                            elide: Text.ElideRight
                            maximumLineCount: 2
                            wrapMode: Text.Wrap
                        }
                    }

                    AppButton {
                        visible: toast.actionText !== ""
                        text: toast.actionText
                        size: "sm"
                        variant: "secondary"
                        onClicked: {
                            const action = root.actions[toast.toastId]
                            root.dismiss(toast.toastId)
                            if (action)
                                action()
                        }
                    }

                    IconButton {
                        iconName: "x"
                        boxSize: 26
                        iconSize: 14
                        onClicked: root.dismiss(toast.toastId)
                    }
                }
            }
        }
    }
}
