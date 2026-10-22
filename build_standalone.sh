#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
BUILD_DIR="${SCRIPT_DIR}/build"

echo "Building standalone portable binary for fresh Linux installations..."

mkdir -p "${DIST_DIR}"

pyinstaller \
    --name="logitech-onboard-gui" \
    --onefile \
    --windowed \
    --clean \
    --add-data="${SCRIPT_DIR}/assets:assets" \
    --paths="${SCRIPT_DIR}" \
    --distpath="${DIST_DIR}" \
    --workpath="${BUILD_DIR}" \
    "${SCRIPT_DIR}/main.py"

echo "Build finished successfully!"
echo "Standalone binary located at: ${DIST_DIR}/logitech-onboard-gui"
echo "This single file can be copied to any fresh Linux PC and executed directly."
