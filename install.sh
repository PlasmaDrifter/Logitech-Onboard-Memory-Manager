#!/usr/bin/env bash
set -e

# Resolve script directory dynamically (No hardcoded paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

mkdir -p "${BIN_DIR}" "${APP_DIR}" "${ICON_DIR}"

echo "Installing Logitech Onboard Memory Manager..."

# 1. Install application launcher script
ln -sf "${SCRIPT_DIR}/main.py" "${BIN_DIR}/logitech-onboard-gui"
chmod +x "${BIN_DIR}/logitech-onboard-gui"
echo "Created command link: ${BIN_DIR}/logitech-onboard-gui"

# 2. Install SVG icon
cp "${SCRIPT_DIR}/assets/icon.svg" "${ICON_DIR}/logitech-onboard.svg"
echo "Installed icon to: ${ICON_DIR}/logitech-onboard.svg"

# 3. Install .desktop entry
cp "${SCRIPT_DIR}/assets/logitech-onboard.desktop" "${APP_DIR}/logitech-onboard.desktop"
echo "Installed desktop entry to: ${APP_DIR}/logitech-onboard.desktop"

# 4. Refresh icon and desktop caches if utilities are available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installation complete!"
echo "You can launch it anytime by running: logitech-onboard-gui"
echo "Or searching for 'Logitech Onboard Memory Manager' in your application menu."
