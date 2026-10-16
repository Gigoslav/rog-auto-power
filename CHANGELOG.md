# Changelog

All notable changes to **`rog-auto-power`** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-10-16
### Changed
- **License & Mandatory Credits (`GPL-3.0-or-later`):** Switched to GNU General Public License v3.0 or later (`GPL-3.0-or-later`) with explicit Section 7(b) author attribution notice (`NOTICE` & `AUTHORS`) and SPDX headers across all files.
- **Standard Linux / FHS Packaging:** Added standard `Makefile` (`PREFIX=/usr`, `DESTDIR=...`), Freedesktop XDG entry (`rog-auto-power.desktop`), `--version` CLI output, and in-app **About & Credits** tray menu item.

## [0.1.1] - 2026-10-16
### Added
- **Automatic Localization (`en` / `de`):** Automatic system locale detection (`LANG`, `LC_ALL`, `LC_MESSAGES`) with `--lang en|de` CLI override and `ROG_LANG` environment variable.
- **Battery C-Rate & Protection Modes:** Live C-Rate calculation (`W / Wh`), instant `0.0 C` AC Bypass mode (stop charging immediately at current percentage), and persistent `60%`, `80%`, and `100%` charge thresholds.
- **Deep Hardware Power Savings:** Automatic screen brightness switching (`50%` Battery / `75%` USB-C / `100%` AC), CPU Turbo Boost toggle, ASUS Panel Overdrive toggle, PCIe Runtime PM (`auto`), and Wi-Fi power-save (`12.4 W` idle on battery).

### Fixed
- **NVIDIA `D3cold` Sleep Fix:** Removed `nvidia-smi` from polling loop and switched to pure `sysfs` runtime PM inspection (`/sys/bus/pci/devices/0000:01:00.0/power/runtime_status`) so the RTX 3060 stays suspended at `0.0 W` on battery and hybrid mode.

## [0.1.0] - 2026-10-16
### Added
- Initial release with 3-state power switching (`battery`, `usbc`, `ac`), `60 Hz` / `240 Hz` refresh rate switching via `kscreen-doctor`, live 2-line KDE system-tray Wattage badge (`Total IN = Battery + System`), and GPU/MUX switching (`Integrated`, `Hybrid`, `AsusMuxDgpu`).
