#!/usr/bin/env bash
set -e

# Resolve paths dynamically (No hardcoded user paths)
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_NAMES=("omm-linux-watcher.service" "logitech-omm-watcher.service")

echo "Uninstalling OMM Linux..."

# 1. Stop and disable background services if running
if command -v systemctl >/dev/null 2>&1; then
    for s_name in "${SERVICE_NAMES[@]}"; do
        if systemctl --user is-active --quiet "${s_name}" 2>/dev/null; then
            echo "Stopping background watcher service (${s_name})..."
            systemctl --user stop "${s_name}" 2>/dev/null || true
        fi
        if systemctl --user is-enabled --quiet "${s_name}" 2>/dev/null; then
            echo "Disabling background watcher service (${s_name})..."
            systemctl --user disable "${s_name}" 2>/dev/null || true
        fi
        if [ -f "${SERVICE_DIR}/${s_name}" ]; then
            rm -f "${SERVICE_DIR}/${s_name}"
            echo "Removed systemd unit: ${SERVICE_DIR}/${s_name}"
        fi
    done
    systemctl --user daemon-reload 2>/dev/null || true
fi

# 2. Remove command launchers
for bin_name in "omm-linux" "logitech-onboard-gui"; do
    if [ -L "${BIN_DIR}/${bin_name}" ] || [ -f "${BIN_DIR}/${bin_name}" ]; then
        rm -f "${BIN_DIR}/${bin_name}"
        echo "Removed command link: ${BIN_DIR}/${bin_name}"
    fi
done

# 3. Remove .desktop entries
for desk_name in "omm-linux.desktop" "logitech-onboard.desktop"; do
    if [ -f "${APP_DIR}/${desk_name}" ]; then
        rm -f "${APP_DIR}/${desk_name}"
        echo "Removed desktop entry: ${APP_DIR}/${desk_name}"
    fi
done

# 4. Remove icons
for icon_name in "omm-linux.svg" "logitech-onboard.svg"; do
    if [ -f "${ICON_DIR}/${icon_name}" ]; then
        rm -f "${ICON_DIR}/${icon_name}"
        echo "Removed icon: ${ICON_DIR}/${icon_name}"
    fi
done

# 5. Refresh icon and desktop caches if utilities are available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Uninstallation complete."
echo "Note: User configuration and profile files in ~/.config/omm-linux were preserved."
