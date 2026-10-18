import QtQuick

Text {
    property bool mono: false
    property bool micro: false

    color: micro ? Theme.textMuted : Theme.text
    font.family: mono ? Theme.monoFamily : Theme.fontFamily
    font.pixelSize: micro ? Theme.textMicro : Theme.textBase
    font.weight: micro ? Font.DemiBold : Font.Normal
    font.letterSpacing: micro ? 0.8 : 0
    font.capitalization: micro ? Font.AllUppercase : Font.MixedCase
    renderType: Text.NativeRendering
    textFormat: Text.PlainText
    verticalAlignment: Text.AlignVCenter
}
