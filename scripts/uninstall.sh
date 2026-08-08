#!/usr/bin/env bash
set -euo pipefail

APP_ID="mikelexp.alsachainqt"
APP_BIN_NAME="alsachainqt"
INSTALL_BIN="${HOME}/.local/bin"
INSTALL_LIB="${HOME}/.local/lib/${APP_ID}"
INSTALL_APPS="${HOME}/.local/share/applications"
INSTALL_ICONS="${HOME}/.local/share/icons/hicolor/512x512/apps"

rm -f "${INSTALL_BIN}/${APP_BIN_NAME}"
rm -f "${INSTALL_APPS}/${APP_ID}.desktop"
rm -f "${INSTALL_ICONS}/${APP_ID}.png"
rm -rf "${INSTALL_LIB}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${INSTALL_APPS}"
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "${HOME}/.local/share/icons/hicolor"
fi

echo "Removed the ALSAChainQT application files. ALSAChain profiles and configuration were retained."
