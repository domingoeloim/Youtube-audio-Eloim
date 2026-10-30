import QtQuick

Item {
  id: root

  property string kind: "headphones"
  property color color: "white"
  property real pixelSize: 20

  readonly property string glyph: {
    if (kind === "headphones") return "\uf025"
    if (kind === "rewind") return "\uf04a"
    if (kind === "forward") return "\uf04e"
    if (kind === "play") return "\uf04b"
    if (kind === "pause") return "\uf04c"
    if (kind === "clipboard") return "\uf0c5"
    if (kind === "pip") return "\uf2d2"
    return ""
  }

  Text {
    anchors.centerIn: parent
    text: root.glyph
    color: root.color
    font.family: "Font Awesome 7 Free"
    font.weight: Font.Black
    font.pixelSize: root.pixelSize
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
  }

  Text {
    visible: root.kind === "headphones"
    anchors.centerIn: parent
    anchors.verticalCenterOffset: -root.pixelSize * 0.02
    text: "\uf001"
    color: root.color
    font.family: "Font Awesome 7 Free"
    font.weight: Font.Black
    font.pixelSize: root.pixelSize * 0.48
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
  }

  Text {
    visible: root.kind === "rewind" || root.kind === "forward"
    anchors.centerIn: parent
    anchors.verticalCenterOffset: root.pixelSize * 0.14
    text: "30"
    color: root.color
    font.family: "Font Awesome 7 Free"
    font.weight: Font.Black
    font.pixelSize: root.pixelSize * 0.36
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
  }
}
