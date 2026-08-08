#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_VERSION="$(python3 "${ROOT_DIR}/scripts/version.py")"
ARCH_VERSION="${APP_VERSION/-/}"
REPO_NAME="alsachainqt-bin"
GITHUB_REPO="mikelexp/alsachainqt"
AUR_SSH="ssh://aur@aur.archlinux.org/${REPO_NAME}.git"
ARCHIVE="alsachainqt-${APP_VERSION}-linux-x86_64.tar.gz"
WORK_DIR="$(mktemp -d /tmp/alsachainqt-aur-XXXXX)"
DOWNLOAD_DIR="${WORK_DIR}/download"

cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

command -v gh >/dev/null 2>&1 || { echo "gh is required to download the GitHub release." >&2; exit 1; }
command -v makepkg >/dev/null 2>&1 || { echo "makepkg is required to validate the AUR package." >&2; exit 1; }

echo "Updating ${REPO_NAME} to v${APP_VERSION}..."
mkdir -p "${DOWNLOAD_DIR}"
gh release download "v${APP_VERSION}" --repo "${GITHUB_REPO}" --pattern "${ARCHIVE}" --dir "${DOWNLOAD_DIR}"
HASH="$(sha256sum "${DOWNLOAD_DIR}/${ARCHIVE}" | cut -d' ' -f1)"

git clone "${AUR_SSH}" "${WORK_DIR}/aur"
cp "${ROOT_DIR}/PKGBUILD" "${WORK_DIR}/aur/PKGBUILD"

cd "${WORK_DIR}/aur"
sed -i "s/^pkgver=.*/pkgver=${ARCH_VERSION}/" PKGBUILD
sed -i "s/^_upstream_version=.*/_upstream_version=${APP_VERSION}/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums=('[^']*')/sha256sums=('${HASH}')/" PKGBUILD
makepkg -s
makepkg --printsrcinfo > .SRCINFO

git add PKGBUILD .SRCINFO
git commit -m "bump to v${APP_VERSION}"
git push origin master

echo "Published ${REPO_NAME} v${APP_VERSION} to AUR."
