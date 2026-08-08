#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  python3 -m venv "${ROOT_DIR}/.venv"
fi

"${ROOT_DIR}/.venv/bin/pip" install --upgrade pip
"${ROOT_DIR}/.venv/bin/pip" install -e "${ROOT_DIR}[dev,build]"

echo "Development and build dependencies installed into ${ROOT_DIR}/.venv"
