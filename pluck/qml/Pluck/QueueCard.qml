pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Pluck.Core

Card {
    id: root

    signal showError(string message, string detail)

    readonly property string emptyTitle: ({
        all: "Nenhum download ainda",
        active: "Nada baixando agora",
        completed: "Nenhum download concluído",
        failed: "Nenhuma falha"
    })[Downloads.view.group]
    readonly property string emptyDescription: ({
        all: "Cole um link ao lado pra começar. Os downloads aparecem aqui.",
        active: "Os downloads em andamento e na fila aparecem aqui.",
        completed: "Quando um download terminar, ele aparece aqui.",
        failed: "Tudo certo por aqui."
    })[Downloads.view.group]

    title: "Fila"
    subtitle: {
        const parts = []
        if (Downloads.runningCount > 0)
            parts.push(Downloads.runningCount + " baixando")
        if (Downloads.queuedCount > 0)
            parts.push(Downloads.queuedCount + " na fila")
        if (Downloads.completedCount > 0)
            parts.push(Downloads.completedCount + (Downloads.completedCount === 1 ? " concluído" : " concluídos"))
        return parts.length > 0 ? parts.join(" · ") : "Vazia"
    }
    iconName: "list-video"
    stretchContent: true

    headerActions: [
        IconButton {
            visible: Downloads.failedCount > 0
            iconName: "rotate-cw"
            hint: "Tentar de novo os que falharam"
            onClicked: Downloads.retryFailed()
        },
        IconButton {
            visible: Downloads.completedCount > 0
            iconName: "list-checks"
            hint: "Limpar concluídos"
            onClicked: Downloads.clearFinished()
        },
        IconButton {
            iconName: "folder-open"
            hint: "Abrir pasta de downloads"
            onClicked: Desktop.openFolder(AppSettings.folder)
        }
    ]

    Segmented {
        options: [
            { value: "all", label: "Todos" },
            { value: "active", label: "Em andamento" },
            { value: "completed", label: "Concluídos" },
            { value: "failed", label: "Falhas" }
        ]
        counts: ({ all: Downloads.totalCount, active: Downloads.pendingCount, completed: Downloads.completedCount, failed: Downloads.failedCount })
        value: Downloads.view.group
        onActivated: value => Downloads.view.group = value
    }

    Rectangle {
        visible: Downloads.interruptedCount > 0
        Layout.fillWidth: true
        Layout.preferredHeight: 46
        radius: Theme.radiusMd
        color: Theme.withAlpha(Theme.warn, 0.07)
        border.color: Theme.withAlpha(Theme.warn, 0.28)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 6
            spacing: 10

            Icon {
                name: "history"
                size: 16
                color: Theme.warn
            }

            AppText {
                Layout.fillWidth: true
                text: Downloads.interruptedCount === 1
                    ? "1 download foi interrompido antes de terminar."
                    : Downloads.interruptedCount + " downloads foram interrompidos antes de terminar."
                font.pixelSize: Theme.textSm
                elide: Text.ElideRight
            }

            AppButton {
                text: "Tentar de novo"
                iconName: "rotate-cw"
                size: "sm"
                variant: "secondary"
                onClicked: Downloads.retryInterrupted()
            }
        }
    }

    ListView {
        id: list

        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 160
        clip: true
        spacing: 8
        model: Downloads.view
        boundsBehavior: Flickable.StopAtBounds
        reuseItems: true

        ScrollBar.vertical: AppScrollBar {}

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 200 }
        }

        displaced: Transition {
            NumberAnimation { properties: "y"; duration: 200; easing.type: Easing.OutCubic }
        }

        delegate: DownloadRow {
            width: ListView.view.width - 12
            onShowError: (message, detail) => root.showError(message, detail)
        }

        EmptyState {
            visible: list.count === 0
            anchors.centerIn: parent
            iconName: Downloads.view.group === "failed" ? "circle-check" : "inbox"
            title: root.emptyTitle
            description: root.emptyDescription
        }
    }
}
