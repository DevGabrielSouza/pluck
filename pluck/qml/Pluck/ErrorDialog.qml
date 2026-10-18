import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Pluck.Core

Popup {
    id: root

    property string message
    property string detail

    function show(errorMessage, errorDetail) {
        message = errorMessage
        detail = errorDetail
        open()
    }

    anchors.centerIn: Overlay.overlay
    width: Math.min(560, parent ? parent.width - 80 : 560)
    padding: 22
    modal: true
    focus: true

    Overlay.modal: Rectangle {
        color: "#99030509"
    }

    background: Rectangle {
        radius: Theme.radiusCard
        color: Theme.popover
        border.color: Theme.borderStrong
    }

    contentItem: ColumnLayout {
        spacing: 12

        RowLayout {
            spacing: 10

            Icon {
                name: "circle-alert"
                size: 18
                color: Theme.err
            }

            AppText {
                Layout.fillWidth: true
                text: root.message
                font.pixelSize: Theme.textMd
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }
        }

        ScrollView {
            visible: root.detail !== ""
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(detailArea.implicitHeight + 8, 260)

            TextArea {
                id: detailArea

                text: root.detail
                readOnly: true
                selectByMouse: true
                wrapMode: Text.WrapAnywhere
                color: Theme.textMuted
                font.family: Theme.monoFamily
                font.pixelSize: Theme.textXs
                padding: 12
                background: Rectangle {
                    radius: Theme.radiusMd
                    color: Theme.bgElev
                    border.color: Theme.border
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 8

            AppButton {
                visible: root.detail !== ""
                text: "Copiar detalhes"
                iconName: "copy"
                variant: "ghost"
                onClicked: {
                    Desktop.copyText(root.message + "\n\n" + root.detail)
                    Toasts.show("ok", "Detalhes copiados")
                }
            }

            AppButton {
                text: "Fechar"
                variant: "secondary"
                onClicked: root.close()
            }
        }
    }
}
