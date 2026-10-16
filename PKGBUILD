# Maintainer: Marcel Berghaus <berghaus.marcel@gmail.com>
pkgname=rog-auto-power-git
pkgver=1.0.0
pkgrel=1
pkgdesc="ASUS ROG Strix 3-state auto power profile, 60/240Hz switcher, live Wattage (IN/Battery/System) KDE tray badge & GPU/MUX switcher"
arch=('any')
url="https://github.com/Gigoslav/rog-auto-power"
license=('MIT')
depends=('python' 'python-pyqt6' 'python-dbus' 'power-profiles-daemon' 'libnotify')
optdepends=(
  'supergfxctl: GPU mode switching (Integrated / Hybrid / AsusMuxDgpu)'
  'kscreen: Wayland/X11 display refresh rate switching via kscreen-doctor'
  'xorg-xrandr: X11 fallback refresh rate switching'
)
makedepends=('git')
source=("git+${url}.git")
sha256sums=('SKIP')

package() {
  cd "$srcdir/rog-auto-power"
  install -Dm755 auto-power-profile.py "$pkgdir/usr/bin/auto-power-profile.py"
  install -Dm755 rog-gpu-mux-helper "$pkgdir/usr/local/bin/rog-gpu-mux-helper"
  install -Dm644 auto-power-profile.service "$pkgdir/usr/lib/systemd/user/auto-power-profile.service"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
