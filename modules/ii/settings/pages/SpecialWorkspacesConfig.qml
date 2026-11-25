import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.services
import qs.modules.common
import qs.modules.common.widgets

ContentPage {
    id: page
    forceWidth: true
    property string statusMessage: ""
    property bool failed: false
    readonly property bool dirty: JSON.stringify(snapshot()) !== JSON.stringify(configSnapshot())

    ListModel { id: entries }

    function configSnapshot() {
        return Config.options.hyprland.specialWorkspaces.map(entry => ({
            name: entry.name ?? "", toggleKeybind: entry.toggleKeybind ?? "",
            moveKeybind: entry.moveKeybind ?? "", toggleAliases: entry.toggleAliases ?? ""
        }))
    }

    function snapshot() {
        const result = []
        for (let i = 0; i < entries.count; i++) {
            const entry = entries.get(i)
            result.push({ name: entry.name, toggleKeybind: entry.toggleKeybind,
                moveKeybind: entry.moveKeybind, toggleAliases: entry.toggleAliases })
        }
        return result
    }

    function load() {
        entries.clear()
        for (const entry of configSnapshot()) entries.append(entry)
        statusMessage = ""
    }

    Component.onCompleted: load()

    Process {
        id: applyProcess
        property var pendingEntries: []
        property string errorText: ""
        stdout: StdioCollector {}
        stderr: StdioCollector { onStreamFinished: applyProcess.errorText = text.trim() }
        onExited: (exitCode, exitStatus) => {
            page.failed = exitCode !== 0 || exitStatus !== 0
            if (page.failed) {
                page.statusMessage = errorText || Translation.tr("Could not apply workspace shortcuts. Check Hyprland configuration.")
            } else {
                Config.options.hyprland.specialWorkspaces = pendingEntries
                page.statusMessage = Translation.tr("Workspace shortcuts applied.")
            }
        }
    }

    component WorkspaceField: ConfigTextArea {
        required property int entryIndex
        required property string field
        property bool ready: false
        fieldWidth: 300
        value: entries.get(entryIndex)[field]
        Component.onCompleted: ready = true
        onValueChanged: {
            if (ready && entryIndex >= 0 && entryIndex < entries.count)
                entries.setProperty(entryIndex, field, value)
        }
    }

    ContentSection {
        title: Translation.tr("Special workspaces")
        icon: "shelves"
        collapsible: false

        StyledText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
            text: Translation.tr("Create named workspaces and assign shortcuts. Names use letters in any language, numbers, underscores or hyphens. Assigned shortcuts replace existing bindings. Leave a shortcut empty to disable it.")
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 16
            enabled: !applyProcess.running

            Repeater {
                model: entries
                delegate: ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    RowLayout {
                        Layout.fillWidth: true
                        StyledText {
                            Layout.fillWidth: true
                            text: model.name || Translation.tr("New workspace")
                            font.weight: Font.Medium
                        }
                        RippleButton {
                            implicitWidth: 40
                            implicitHeight: 36
                            onClicked: entries.remove(index)
                            contentItem: MaterialSymbol {
                                text: "delete"
                                horizontalAlignment: Text.AlignHCenter
                                color: Appearance.colors.colError
                            }
                            StyledToolTip { text: Translation.tr("Remove") }
                        }
                    }

                    GroupedList {
                        Layout.fillWidth: true
                        WorkspaceField {
                            entryIndex: index
                            field: "name"
                            text: Translation.tr("Workspace name")
                            placeholderText: "Media"
                        }
                        WorkspaceField {
                            entryIndex: index
                            field: "toggleKeybind"
                            text: Translation.tr("Toggle shortcut")
                            placeholderText: "SUPER + M"
                        }
                        WorkspaceField {
                            entryIndex: index
                            field: "moveKeybind"
                            text: Translation.tr("Move window shortcut")
                            placeholderText: "SUPER + SHIFT + …"
                        }
                        WorkspaceField {
                            entryIndex: index
                            field: "toggleAliases"
                            text: Translation.tr("Additional toggle shortcuts")
                            description: Translation.tr("Separate shortcuts with commas")
                            placeholderText: "CTRL + SUPER + S"
                        }
                    }
                }
            }

            RippleButton {
                Layout.fillWidth: true
                implicitHeight: 42
                onClicked: entries.append({ name: "", toggleKeybind: "", moveKeybind: "", toggleAliases: "" })
                contentItem: StyledText {
                    text: Translation.tr("Add workspace")
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            RowLayout {
                Layout.fillWidth: true
                RippleButton {
                    Layout.fillWidth: true
                    implicitHeight: 42
                    enabled: page.dirty
                    onClicked: page.load()
                    contentItem: StyledText {
                        text: Translation.tr("Discard changes")
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
                RippleButton {
                    Layout.fillWidth: true
                    implicitHeight: 42
                    onClicked: {
                        applyProcess.pendingEntries = page.snapshot()
                        applyProcess.errorText = ""
                        page.statusMessage = ""
                        applyProcess.command = ["python3", `${Directories.scriptPath}/hyprland/special_workspaces.py`,
                            "--entries", JSON.stringify(applyProcess.pendingEntries)]
                        applyProcess.running = true
                    }
                    contentItem: StyledText {
                        text: Translation.tr("Apply shortcuts")
                        horizontalAlignment: Text.AlignHCenter
                        color: Appearance.colors.colPrimary
                    }
                }
            }
        }

        StyledText {
            Layout.fillWidth: true
            visible: page.statusMessage.length > 0
            text: page.statusMessage
            color: page.failed ? Appearance.colors.colError : Appearance.colors.colPrimary
            wrapMode: Text.Wrap
        }
        StyledText {
            Layout.fillWidth: true
            text: Translation.tr("To launch apps here at startup, open Hyprland → Autostart apps, enable Special workspace and choose its name. Renaming or removing a workspace keeps its open windows and existing autostart destinations.")
            wrapMode: Text.Wrap
            color: Appearance.colors.colSubtext
        }
    }
}
