#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
BUILD_DIR="${SCRIPT_DIR}/build"
APP_DIR="${BUILD_DIR}/AppDir"

echo "Building standalone binary via PyInstaller..."
mkdir -p "${DIST_DIR}"

pyinstaller \
    --name="logitech-onboard-gui" \
    --onefile \
    --windowed \
    --clean \
    --exclude-module PyQt6 \
    --exclude-module PyQt5 \
    --exclude-module PySide2 \
    --add-data="${SCRIPT_DIR}/assets:assets" \
    --paths="${SCRIPT_DIR}" \
    --distpath="${DIST_DIR}" \
    --workpath="${BUILD_DIR}" \
    "${SCRIPT_DIR}/main.py"

echo "Preparing AppDir structure..."
rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${APP_DIR}/usr/share/applications"

cp "${DIST_DIR}/logitech-onboard-gui" "${APP_DIR}/usr/bin/"
cp "${SCRIPT_DIR}/assets/icon.svg" "${APP_DIR}/usr/share/icons/hicolor/scalable/apps/logitech-onboard.svg"
cp "${SCRIPT_DIR}/assets/icon.svg" "${APP_DIR}/logitech-onboard.svg"
cp "${SCRIPT_DIR}/assets/logitech-onboard.desktop" "${APP_DIR}/usr/share/applications/"
cp "${SCRIPT_DIR}/assets/logitech-onboard.desktop" "${APP_DIR}/logitech-onboard.desktop"

# Create AppRun
cat << 'RUN' > "${APP_DIR}/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/logitech-onboard-gui" "$@"
RUN
chmod +x "${APP_DIR}/AppRun"

echo "Building AppImage..."
APPIMAGETOOL=$(command -v appimagetool || echo "${HOME}/.local/bin/appimagetool")

if [ ! -x "${APPIMAGETOOL}" ]; then
    echo "Error: appimagetool not found"
    exit 1
fi

VERSION="${1:-v0.8.1}"
OUTPUT_NAME="Logitech-Onboard-Memory-Manager-${VERSION}-x86_64.AppImage"
rm -f "${DIST_DIR}/${OUTPUT_NAME}"
ARCH=x86_64 "${APPIMAGETOOL}" "${APP_DIR}" "${DIST_DIR}/${OUTPUT_NAME}"

echo "AppImage created successfully at ${DIST_DIR}/${OUTPUT_NAME}"
