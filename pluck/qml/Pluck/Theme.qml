pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#070B14"
    readonly property color bgElev: "#0B1120"
    readonly property color card: "#0D111A"
    readonly property color cardHover: "#11161F"
    readonly property color cardRaised: "#121826"
    readonly property color popover: "#0E1424"
    readonly property color track: "#14FFFFFF"

    readonly property color border: "#0FFFFFFF"
    readonly property color borderStrong: "#1AFFFFFF"
    readonly property color borderNeon: "#663B82F6"

    readonly property color accent: "#3B82F6"
    readonly property color accentHover: "#60A5FA"
    readonly property color accentPressed: "#2563EB"
    readonly property color accentSoft: "#1F3B82F6"
    readonly property color accentRing: "#4D3B82F6"
    readonly property color accentText: "#93C5FD"
    readonly property color cyan: "#22D3EE"
    readonly property color violet: "#A78BFA"

    readonly property color text: "#E5E7EB"
    readonly property color textMuted: "#9CA3AF"
    readonly property color textDim: "#7D8594"

    readonly property color ok: "#10B981"
    readonly property color warn: "#F59E0B"
    readonly property color err: "#EF4444"

    readonly property string fontFamily: "Inter Variable"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property int radiusCard: 14
    readonly property int radiusLg: 12
    readonly property int radiusMd: 10
    readonly property int radiusSm: 8

    readonly property int textMicro: 10
    readonly property int textXs: 11
    readonly property int textSm: 12
    readonly property int textBase: 13
    readonly property int textMd: 14
    readonly property int textLg: 16
    readonly property int textXl: 20

    function tone(name) {
        switch (name) {
        case "ok": return ok
        case "warn": return warn
        case "err": return err
        case "info": return accent
        case "violet": return violet
        case "cyan": return cyan
        default: return textDim
        }
    }

    function withAlpha(base, alpha) {
        return Qt.rgba(base.r, base.g, base.b, alpha)
    }
}
