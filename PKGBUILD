# Maintainer: Mikele <mikele@gmail.com>

pkgname=alsachainqt-bin
pkgver=0.1.0beta.1
_upstream_version=0.1.0-beta.1
pkgrel=1
pkgdesc="Native Qt desktop manager for ALSAChain virtual PCM profiles"
arch=('x86_64')
url="https://github.com/mikelexp/alsachainqt"
license=('custom')
depends=(
  'alsa-lib'
  'glibc'
  'libxcb'
  'libxkbcommon-x11'
  'xcb-util-cursor'
  'xcb-util-image'
  'xcb-util-keysyms'
  'xcb-util-renderutil'
  'xcb-util-wm'
)
optdepends=(
  'alsa-utils: discover playback hardware and control mixers'
  'alsa-plugins: ALSA equalizer PCM and CTL modules'
  'caps: CAPS Eq10 LADSPA DSP'
  'bs2b-ladspa: optional headphone crossfeed DSP'
)
source=("${url}/releases/download/v${_upstream_version}/alsachainqt-${_upstream_version}-linux-x86_64.tar.gz")
sha256sums=('SKIP')

package() {
  cd "${srcdir}"

  install -Dm755 alsachainqt "${pkgdir}/usr/bin/alsachainqt"
  install -Dm755 libasound_module_pcm_alsachain_status.so \
    "${pkgdir}/usr/lib/alsa-lib/libasound_module_pcm_alsachain_status.so"
  install -Dm644 icon.png \
    "${pkgdir}/usr/share/icons/hicolor/512x512/apps/mikelexp.alsachainqt.png"
  install -Dm644 mikelexp.alsachainqt.desktop \
    "${pkgdir}/usr/share/applications/mikelexp.alsachainqt.desktop"
}
