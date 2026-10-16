# Maintainer: Marcel Berghaus (Gigoslav) <berghaus.marcel@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

pkgname=rog-auto-power-git
pkgver=0.1.1
pkgrel=1
pkgdesc="ASUS ROG Strix 3-state auto power profile, 60/240Hz switcher, live Wattage (IN/Battery/System) KDE tray badge & GPU/MUX switcher"
arch=('any')
url="https://github.com/Gigoslav/rog-auto-power"
license=('GPL-3.0-or-later')
depends=('python' 'python-pyqt6' 'python-dbus' 'power-profiles-daemon' 'libnotify')
optdepends=(
  'supergfxctl: GPU mode switching (Integrated / Hybrid / AsusMuxDgpu)'
  'kscreen: Wayland/X11 display refresh rate switching via kscreen-doctor'
  'xorg-xrandr: X11 fallback refresh rate switching'
  'iw: Wi-Fi power-save toggling on battery'
)
makedepends=('git')
provides=('rog-auto-power')
conflicts=('rog-auto-power')
source=("git+${url}.git")
sha256sums=('SKIP')

package() {
  cd "$srcdir/rog-auto-power"
  make DESTDIR="$pkgdir" PREFIX=/usr install
}
