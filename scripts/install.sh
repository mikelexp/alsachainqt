#!/usr/bin/env bash
set -euo pipefail

APP_ID="mikelexp.alsachainqt"
APP_BIN_NAME="alsachainqt"
INSTALL_BIN="${HOME}/.local/bin"
INSTALL_LIB="${HOME}/.local/lib/${APP_ID}"
INSTALL_APPS="${HOME}/.local/share/applications"
INSTALL_ICON_THEME="${HOME}/.local/share/icons/hicolor"
INSTALL_ICONS="${INSTALL_ICON_THEME}/512x512/apps"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${SCRIPT_DIR}/alsachainqt" && -f "${SCRIPT_DIR}/icon.png" ]]; then
  MODE="tarball"
  BIN="${SCRIPT_DIR}/alsachainqt"
  ICON="${SCRIPT_DIR}/icon.png"
  DESKTOP="${SCRIPT_DIR}/mikelexp.alsachainqt.desktop"
elif [[ -d "${SCRIPT_DIR}/../dist/alsachainqt.dist" ]]; then
  MODE="standalone"
  BIN="${SCRIPT_DIR}/../dist/alsachainqt.dist"
  ICON="${SCRIPT_DIR}/../icon.png"
  DESKTOP="${SCRIPT_DIR}/../alsachainqt.desktop"
elif [[ -f "${SCRIPT_DIR}/../dist/alsachainqt.bin" ]]; then
  MODE="onefile"
  BIN="${SCRIPT_DIR}/../dist/alsachainqt.bin"
  ICON="${SCRIPT_DIR}/../icon.png"
  DESKTOP="${SCRIPT_DIR}/../alsachainqt.desktop"
else
  echo "Error: no ALSAChainQT build found. Run make build-standalone or make build-onefile first." >&2
  exit 1
fi

mkdir -p "${INSTALL_BIN}" "${INSTALL_APPS}" "${INSTALL_ICONS}"
if [[ "${MODE}" == "standalone" ]]; then
  rm -rf "${INSTALL_LIB}"
  cp -r "${BIN}" "${INSTALL_LIB}"
  chmod +x "${INSTALL_LIB}/alsachainqt.bin"
  ln -sf "${INSTALL_LIB}/alsachainqt.bin" "${INSTALL_BIN}/${APP_BIN_NAME}"
else
  install -m 755 "${BIN}" "${INSTALL_BIN}/${APP_BIN_NAME}"
fi

install -m 644 "${ICON}" "${INSTALL_ICONS}/${APP_ID}.png"
install -m 644 "${DESKTOP}" "${INSTALL_APPS}/${APP_ID}.desktop"

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "${INSTALL_ICON_THEME}"
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${INSTALL_APPS}"
fi

echo "Installed ${APP_BIN_NAME} to ${INSTALL_BIN}."
if [[ -f "${SCRIPT_DIR}/libasound_module_pcm_alsachain_status.so" ]]; then
  echo "Install the bundled ALSA status module with:"
  echo "  sudo install -Dm755 ${SCRIPT_DIR}/libasound_module_pcm_alsachain_status.so /usr/lib/alsa-lib/libasound_module_pcm_alsachain_status.so"
else
  echo "Install the ALSA status module separately with sudo make install-native."
fi
