import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root

    property string title
    property string message
    property string confirmText: "Confirmar"
    property bool destructive: false

    signal confirmed()

    anchors.centerIn: Overlay.overlay
    width: 400
    padding: 22
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: cancelButton.forceActiveFocus()

    function activateFocused() {
        if (cancelButton.activeFocus)
            cancelButton.click()
        else if (confirmButton.activeFocus)
            confirmButton.click()
    }

    Overlay.modal: Rectangle {
        color: "#99030509"
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.97; to: 1; duration: 140; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 }
    }

    background: Rectangle {
        radius: Theme.radiusCard
        color: Theme.popover
        border.color: Theme.borderStrong
    }

    contentItem: ColumnLayout {
        Keys.onReturnPressed: root.activateFocused()
        Keys.onEnterPressed: root.activateFocused()
        spacing: 8

        AppText {
            Layout.fillWidth: true
            text: root.title
            font.pixelSize: Theme.textLg
            font.weight: Font.DemiBold
            wrapMode: Text.Wrap
        }

        AppText {
            Layout.fillWidth: true
            text: root.message
            color: Theme.textMuted
            wrapMode: Text.Wrap
            lineHeight: 1.25
        }

        RowLayout {
            Layout.topMargin: 14
            Layout.alignment: Qt.AlignRight
            spacing: 8

            AppButton {
                id: cancelButton

                text: "Cancelar"
                variant: "ghost"
                onClicked: root.close()
            }

            AppButton {
                id: confirmButton

                text: root.confirmText
                variant: root.destructive ? "destructive" : "primary"
                onClicked: {
                    root.close()
                    root.confirmed()
                }
            }
        }
    }
}
