#!/usr/bin/env bash
set -e

# Resolve script directory dynamically (No hardcoded paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

mkdir -p "${BIN_DIR}" "${APP_DIR}" "${ICON_DIR}"

echo "Installing OMM..."

# Clean up legacy files if present
rm -f "${BIN_DIR}/logitech-onboard-gui" "${APP_DIR}/logitech-onboard.desktop" "${ICON_DIR}/logitech-onboard.svg" "${APP_DIR}/omm-linux.desktop"

# 1. Install application launcher script
ln -sf "${SCRIPT_DIR}/main.py" "${BIN_DIR}/omm"
chmod +x "${BIN_DIR}/omm"
echo "Created command link: ${BIN_DIR}/omm"

# Provide compatibility symlinks
ln -sf "${BIN_DIR}/omm" "${BIN_DIR}/omm-linux"
ln -sf "${BIN_DIR}/omm" "${BIN_DIR}/logitech-onboard-gui"

# 2. Install SVG icon
cp "${SCRIPT_DIR}/assets/icon.svg" "${ICON_DIR}/omm.svg"
cp "${SCRIPT_DIR}/assets/icon.svg" "${ICON_DIR}/omm-linux.svg"
# Also install to base icons dir and active KDE theme if present
cp "${SCRIPT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/omm.svg" 2>/dev/null || true
cp "${SCRIPT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/omm-linux.svg" 2>/dev/null || true
if [ -d "${HOME}/.local/share/icons/Papirus-Dark-Breeze-actions/scalable/apps" ]; then
    cp "${SCRIPT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/Papirus-Dark-Breeze-actions/scalable/apps/omm.svg"
    cp "${SCRIPT_DIR}/assets/icon.svg" "${HOME}/.local/share/icons/Papirus-Dark-Breeze-actions/scalable/apps/omm-linux.svg"
fi
echo "Installed icons."

# 3. Install .desktop entry
cp "${SCRIPT_DIR}/assets/omm.desktop" "${APP_DIR}/omm.desktop"
echo "Installed desktop entry to: ${APP_DIR}/omm.desktop"

# 4. Refresh icon and desktop caches if utilities are available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 --noincremental >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
    if [ -d "${HOME}/.local/share/icons/Papirus-Dark-Breeze-actions" ]; then
        gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/Papirus-Dark-Breeze-actions" >/dev/null 2>&1 || true
    fi
fi

# 5. Update background service unit if installed
python3 -c "import sys; sys.path.insert(0, '${SCRIPT_DIR}'); from core.service_manager import BackgroundServiceManager; BackgroundServiceManager.ensure_service_installed()" >/dev/null 2>&1 || true
systemctl --user daemon-reload >/dev/null 2>&1 || true

echo "Installation complete!"
echo "You can launch it anytime by running: omm"
echo "Or searching for 'OMM' in your application menu."
