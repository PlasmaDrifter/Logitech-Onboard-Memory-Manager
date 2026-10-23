#!/usr/bin/env bash
set -e

# Resolve paths dynamically (No hardcoded user paths)
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="logitech-omm-watcher.service"

echo "Uninstalling Logitech Onboard Memory Manager..."

# 1. Stop and disable background service if running
if command -v systemctl >/dev/null 2>&1; then
    if systemctl --user is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        echo "Stopping background watcher service..."
        systemctl --user stop "${SERVICE_NAME}" 2>/dev/null || true
    fi
    if systemctl --user is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        echo "Disabling background watcher service..."
        systemctl --user disable "${SERVICE_NAME}" 2>/dev/null || true
    fi
fi

if [ -f "${SERVICE_DIR}/${SERVICE_NAME}" ]; then
    rm -f "${SERVICE_DIR}/${SERVICE_NAME}"
    echo "Removed systemd unit: ${SERVICE_DIR}/${SERVICE_NAME}"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload 2>/dev/null || true
    fi
fi

# 2. Remove command launcher
if [ -L "${BIN_DIR}/logitech-onboard-gui" ] || [ -f "${BIN_DIR}/logitech-onboard-gui" ]; then
    rm -f "${BIN_DIR}/logitech-onboard-gui"
    echo "Removed command link: ${BIN_DIR}/logitech-onboard-gui"
fi

# 3. Remove .desktop entry
if [ -f "${APP_DIR}/logitech-onboard.desktop" ]; then
    rm -f "${APP_DIR}/logitech-onboard.desktop"
    echo "Removed desktop entry: ${APP_DIR}/logitech-onboard.desktop"
fi

# 4. Remove icon
if [ -f "${ICON_DIR}/logitech-onboard.svg" ]; then
    rm -f "${ICON_DIR}/logitech-onboard.svg"
    echo "Removed icon: ${ICON_DIR}/logitech-onboard.svg"
fi

# 5. Refresh icon and desktop caches if utilities are available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Uninstallation complete."
echo "Note: User configuration and profile files in ~/.config/logitech-onboard were preserved."
