import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons as Commons

Ui.BarWidget {
  id: root

  moduleName: "maeder.youtube-audio"
  implicitWidth: barSize
  implicitHeight: barSize

  property bool opened: false
  property string currentTitle: ""
  property string playbackClass: "stopped"
  property string errorMessage: ""

  readonly property string controllerPath: decodeURIComponent(
    String(Qt.resolvedUrl("../index.py")).replace(/^file:\/\//, "")
  )
  readonly property bool hasPlayback: playbackClass !== "stopped"

  function open() {
    if (opened) return
    opened = true
    refreshStatus()
    Qt.callLater(function() { searchField.forceActiveFocus() })
  }

  function close() {
    if (!opened) return
    opened = false
  }

  function togglePanel() {
    if (opened) close()
    else open()
  }

  function closeForPopoutSwitch() {
    close()
  }

  function reportError(message) {
    errorMessage = message
    console.error("YouTube Audio: " + message)
  }

  function refreshStatus() {
    if (!statusProcess.running)
      statusProcess.exec(["python3", controllerPath, "status"])
  }

  function readStatus(output) {
    try {
      const result = JSON.parse(output)
      if (!result || typeof result.class !== "string" || typeof result.title !== "string")
        throw new Error("format d'état inattendu")
      playbackClass = result.class
      currentTitle = result.title
    } catch (error) {
      reportError("Impossible de lire l'état du lecteur : " + error)
    }
  }

  function runController(arguments) {
    if (actionProcess.running) {
      reportError("Une commande du lecteur est déjà en cours.")
      return
    }
    errorMessage = ""
    actionProcess.exec(["python3", controllerPath].concat(arguments))
  }

  function playUrl(value) {
    const url = String(value || "").trim()
    const youtubeUrl = /^https?:\/\/(?:www\.|m\.|music\.)?youtube\.com(?:[/:?#]|$)|^https?:\/\/youtu\.be(?:[/:?#]|$)/i
    if (!youtubeUrl.test(url)) {
      reportError("Saisis une URL YouTube valide.")
      return
    }
    runController(["play", "--replace", url])
  }

  function pasteClipboard() {
    const clipboard = String(Quickshell.clipboardText || "").trim()
    if (!clipboard) {
      reportError("Le presse-papiers est vide.")
      return
    }
    searchField.text = clipboard
    searchField.forceActiveFocus()
    errorMessage = ""
  }

  function runControl(action) {
    if (action === "rewind") runController(["seek", "-30"])
    else if (action === "toggle") runController(["toggle"])
    else if (action === "forward") runController(["seek", "30"])
    else if (action === "pip") runController(["pip-current"])
  }

  Timer {
    interval: 1000
    repeat: true
    running: root.opened
    onTriggered: root.refreshStatus()
  }

  Process {
    id: statusProcess
    stdout: StdioCollector {
      onStreamFinished: root.readStatus(text)
    }
    stderr: StdioCollector { }
    onExited: function(exitCode) {
      if (exitCode !== 0)
        root.reportError(stderr.text.trim() || "Impossible de lire l'état du lecteur.")
    }
  }

  Process {
    id: actionProcess
    stdout: StdioCollector { }
    stderr: StdioCollector { }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.reportError(stderr.text.trim() || "La commande du lecteur a échoué (code " + exitCode + ").")
      } else {
        root.errorMessage = ""
        root.refreshStatus()
      }
    }
  }

  Ui.BarIconButton {
    id: barButton
    anchors.fill: parent
    bar: root.bar
    active: root.opened
    activeColor: Commons.Color.accent
    useActiveColor: true
    tooltipText: "YouTube Audio"
    iconComponent: Component {
      Icon {
        anchors.centerIn: parent
        width: Commons.Style.space(24)
        height: Commons.Style.space(24)
        kind: "headphones"
        pixelSize: Commons.Style.space(20)
        color: root.bar ? root.bar.barForeground : Commons.Color.foreground
      }
    }
    onPressed: function(button) {
      if (button === Qt.LeftButton) root.togglePanel()
    }
  }

  Ui.PopupCard {
    id: playerPanel

    anchorItem: barButton
    bar: root.bar
    owner: root
    open: root.opened
    margin: Commons.Style.gapsOut
    padding: Commons.Style.space(14)
    contentWidth: playerPanel.fittedContentWidth(Commons.Style.space(360))
    contentHeight: playerPanel.cappedContentHeight(Commons.Style.space(210))

    Column {
      id: panelContent
      anchors.fill: parent
      spacing: Commons.Style.space(8)

      Row {
        width: parent.width
        height: Commons.Style.space(20)

        Text {
          width: parent.width - author.implicitWidth
          height: parent.height
          text: "YouTube Audio"
          color: Commons.Color.popups.text
          font.family: Commons.Style.font.family
          font.pixelSize: Commons.Style.font.body
          font.bold: true
          verticalAlignment: Text.AlignVCenter
          elide: Text.ElideRight
        }

        Text {
          id: author
          height: parent.height
          text: "Maeder Eloim"
          color: Qt.darker(Commons.Color.popups.text, 1.35)
          font.family: Commons.Style.font.family
          font.pixelSize: Commons.Style.font.bodySmall
          verticalAlignment: Text.AlignVCenter
        }
      }

      Ui.BorderSurface {
        id: searchBox
        width: parent.width
        height: Commons.Style.space(34)
        color: Commons.Style.controlFill(searchField.activeFocus, searchField.hovered, Commons.Color.popups.text, Commons.Color.accent)
        borderSpec: Commons.Border.controlSpec(
          searchField.activeFocus ? "focus" : (searchField.hovered ? "hover-cursor" : "normal"),
          Commons.Color.popups.text,
          Commons.Color.accent
        )
        radius: Commons.Style.cornerRadius

        Ui.TextField {
          id: searchField
          anchors.left: parent.left
          anchors.top: parent.top
          anchors.bottom: parent.bottom
          anchors.right: clipboardButton.left
          background: null
          foreground: Commons.Color.popups.text
          accent: Commons.Color.accent
          horizontalPadding: Commons.Style.space(10)
          verticalPadding: 0
          placeholderText: "Colle une URL YouTube…"
          selectByMouse: true
          onAccepted: root.playUrl(text)
          onTextEdited: root.errorMessage = ""
        }

        Rectangle {
          width: 1
          height: parent.height * 0.55
          anchors.right: clipboardButton.left
          anchors.verticalCenter: parent.verticalCenter
          color: Commons.Color.popups.border
          opacity: 0.55
        }

        Item {
          id: clipboardButton
          width: Commons.Style.space(38)
          anchors.top: parent.top
          anchors.right: parent.right
          anchors.bottom: parent.bottom

          Icon {
            anchors.centerIn: parent
            width: Commons.Style.space(20)
            height: width
            kind: "clipboard"
            pixelSize: Commons.Style.space(18)
            color: Commons.Color.popups.text
          }

          MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.pasteClipboard()
          }
        }
      }

      Column {
        width: parent.width
        height: Commons.Style.space(34)
        spacing: Commons.Style.space(2)

        Item {
          id: titleViewport
          width: parent.width
          height: Commons.Style.space(18)
          clip: true

          Row {
            id: titleTrack
            spacing: Commons.Style.space(28)

            Text {
              id: titleText
              textFormat: Text.PlainText
              text: root.currentTitle || "Aucune lecture en cours"
              color: Commons.Color.popups.text
              font.family: Commons.Style.font.family
              font.pixelSize: Commons.Style.font.body
              verticalAlignment: Text.AlignVCenter
            }

            Text {
              textFormat: Text.PlainText
              text: titleText.text
              color: titleText.color
              font: titleText.font
              verticalAlignment: Text.AlignVCenter
              visible: titleTrack.width > titleViewport.width
            }

            NumberAnimation {
              target: titleTrack
              property: "x"
              from: 0
              to: -(titleText.implicitWidth + titleTrack.spacing)
              duration: Math.max(6000, titleText.implicitWidth * 35)
              loops: Animation.Infinite
              running: root.currentTitle !== "" && titleText.implicitWidth > titleViewport.width
            }
          }
        }

        Text {
          width: parent.width
          height: Commons.Style.space(14)
          visible: root.errorMessage !== ""
          text: root.errorMessage
          color: Commons.Color.urgent
          font.family: Commons.Style.font.family
          font.pixelSize: Commons.Style.font.caption
          elide: Text.ElideRight
          verticalAlignment: Text.AlignVCenter
        }
      }

      Row {
        id: controls
        width: parent.width
        height: Commons.Style.space(42)
        spacing: Commons.Style.space(10)

        Repeater {
          model: [
            { action: "rewind", icon: "rewind", label: "Reculer de 30 secondes" },
            { action: "toggle", icon: root.playbackClass === "playing" ? "pause" : "play", label: "Lecture / pause" },
            { action: "forward", icon: "forward", label: "Avancer de 30 secondes" },
            { action: "pip", icon: "pip", label: "Basculer en Picture-in-Picture" }
          ]

          delegate: Ui.BorderSurface {
            required property var modelData
            readonly property bool enabledControl: root.hasPlayback && !actionProcess.running
            readonly property color foreground: Commons.Color.popups.text
            readonly property var controlBorder: Commons.Border.controlSpec(
              controlMouse.containsMouse ? "hover-cursor" : "normal",
              foreground,
              Commons.Color.accent
            )

            width: (controls.width - controls.spacing * 3) / 4
            height: controls.height
            color: enabledControl
              ? Commons.Style.controlFill(false, controlMouse.containsMouse, foreground, Commons.Color.accent)
              : Commons.Style.normalFillFor(foreground, Commons.Color.accent)
            borderSpec: controlBorder
            radius: Commons.Style.cornerRadius
            opacity: enabledControl ? 1 : 0.45

            Icon {
              anchors.centerIn: parent
              width: Commons.Style.space(22)
              height: width
              kind: modelData.icon
              pixelSize: Commons.Style.space(19)
              color: Commons.Color.popups.text
            }

            MouseArea {
              id: controlMouse
              anchors.fill: parent
              enabled: parent.enabledControl
              hoverEnabled: true
              cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
              onClicked: root.runControl(modelData.action)
            }

            ToolTip.visible: controlMouse.containsMouse
            ToolTip.text: modelData.label
            ToolTip.delay: 450
          }
        }
      }
    }
  }
}
