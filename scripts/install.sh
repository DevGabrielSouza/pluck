#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
launcher="$bin_dir/pluck"
desktop_file="$data_dir/applications/pluck.desktop"
icon_file="$data_dir/icons/hicolor/scalable/apps/pluck.svg"

uninstall() {
    rm -f "$launcher" "$desktop_file" "$icon_file"
    update-desktop-database "$data_dir/applications" 2>/dev/null || true
    echo "Pluck removido."
}

require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Falta o $1. $2" >&2
        exit 1
    fi
}

if [[ "${1:-}" == "--uninstall" ]]; then
    uninstall
    exit 0
fi

require python3 "Instale o Python 3.12 ou mais novo."
if ! python3 -c "import sys; sys.exit(sys.version_info < (3, 12))"; then
    echo "O Pluck precisa do Python 3.12 ou mais novo. Esta máquina tem o $(python3 --version)." >&2
    exit 1
fi
require yt-dlp "Instale com: sudo dnf install yt-dlp"
require ffmpeg "Instale com: sudo dnf install ffmpeg"
if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "Falta o PySide6. Instale com: sudo dnf install python3-pyside6" >&2
    exit 1
fi

mkdir -p "$bin_dir" "$(dirname "$desktop_file")" "$(dirname "$icon_file")"

cat > "$launcher" <<LAUNCHER
#!/usr/bin/env bash
export PYTHONPATH="$project_dir\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m pluck "\$@"
LAUNCHER
chmod 755 "$launcher"

install -m 644 "$project_dir/pluck/assets/pluck.svg" "$icon_file"

cat > "$desktop_file" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Pluck
GenericName=Baixador de vídeos
Comment=Baixe vídeos e áudios do YouTube e de outros sites
Exec=$launcher
Icon=pluck
Terminal=false
Categories=Network;FileTransfer;
Keywords=youtube;yt-dlp;download;video;audio;mp3;
StartupWMClass=pluck
StartupNotify=true
DESKTOP

update-desktop-database "$data_dir/applications" 2>/dev/null || true
echo "Pluck instalado. Abra pelo menu ou rode: pluck"
