import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

// Headless service that hosts one ticker strip per screen, stacked just under the bar.
Item {
  id: root

  // Injected by the Omarchy shell host
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null

  property var quotes: []
  readonly property color upColor: "#3fb950"
  readonly property color downColor: "#f85149"
  // True while any symbol moved past the alert threshold; drives the strip flash.
  readonly property bool anyAlert: quotes.some(q => q.alert)
  readonly property int alertWindowMin: quotes.length && quotes[0].win ? quotes[0].win : 15
  property real flash: 0   // 0..1 pulse, animated below
  SequentialAnimation on flash {
    running: root.anyAlert && !Style.reduceMotion
    loops: Animation.Infinite
    NumberAnimation { from: 0; to: 1; duration: 500; easing.type: Easing.InOutSine }
    NumberAnimation { from: 1; to: 0; duration: 500; easing.type: Easing.InOutSine }
    onStopped: root.flash = 0
  }
  readonly property real alertLevel: Style.reduceMotion ? (anyAlert ? 0.6 : 0) : flash
  readonly property int stripHeight: Math.round(Style.font.body * 1.8)

  Process {
    id: fetcher
    command: ["python3", Qt.resolvedUrl("fetch.py").toString().replace("file://", "")]
    stdout: StdioCollector {
      onStreamFinished: {
        try { const q = JSON.parse(text); if (q.length) root.quotes = q } catch (e) {}
      }
    }
  }
  Timer {
    interval: 60000; running: true; repeat: true; triggeredOnStart: true
    onTriggered: if (!fetcher.running) fetcher.running = true
  }

  Variants {
    model: Quickshell.screens
    PanelWindow {
      required property var modelData
      screen: modelData
      anchors { top: true; left: true; right: true }
      implicitHeight: root.stripHeight
      exclusiveZone: root.stripHeight   // the compositor stacks it under the bar's zone
      color: Qt.rgba(Color.background.r, Color.background.g, Color.background.b, 0.9)
      WlrLayershell.namespace: "omarchy-stock-ticker"
      WlrLayershell.layer: WlrLayer.Top
      visible: root.quotes.length > 0

      Item {
        anchors.fill: parent
        clip: true

        Row {
          id: strip
          height: parent.height
          Repeater {
            model: root.quotes.length ? 2 : 0   // two copies for a seamless loop
            Row {
              height: strip.height
              Repeater {
                model: root.quotes
                Row {
                  required property var modelData
                  height: strip.height
                  spacing: Style.space(6)
                  leftPadding: Style.space(14)
                  readonly property bool up: modelData.d5 >= 0
                  readonly property bool alerting: modelData.alert === true
                  readonly property color alertColor: modelData.pctw >= 0 ? root.upColor : root.downColor
                  Rectangle {
                    // flashing highlight behind an alerting symbol
                    z: -1
                    anchors.fill: parent
                    visible: parent.alerting
                    color: Qt.rgba(parent.alertColor.r, parent.alertColor.g, parent.alertColor.b, 0.15 + 0.45 * root.alertLevel)
                  }
                  Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.s; color: Color.foreground; font { family: Style.font.family; pixelSize: Style.font.body; bold: true } }
                  Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.p.toFixed(2); color: Color.muted; font { family: Style.font.family; pixelSize: Style.font.body } }
                  Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: (up ? "▲ " : "▼ ") + Math.abs(modelData.d5).toFixed(2) + " (" + Math.abs(modelData.pct5).toFixed(2) + "%)"
                    color: up ? root.upColor : root.downColor
                    font { family: Style.font.family; pixelSize: Style.font.body }
                  }
                  Text {
                    visible: alerting
                    anchors.verticalCenter: parent.verticalCenter
                    text: "⚠ " + (modelData.pctw >= 0 ? "+" : "−") + Math.abs(modelData.pctw).toFixed(1) + "% / " + root.alertWindowMin + "m"
                    color: alertColor
                    font { family: Style.font.family; pixelSize: Style.font.body; bold: true }
                  }
                }
              }
            }
          }
          property real copyWidth: children.length > 1 ? children[0].width : 0
          NumberAnimation on x {
            running: strip.copyWidth > 0 && !Style.reduceMotion
            from: 0; to: -strip.copyWidth
            duration: Math.max(1000, strip.copyWidth * 18)
            loops: Animation.Infinite
          }
        }
      }
    }
  }
}
