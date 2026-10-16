# ⚡ ROG Auto-Power & Live Watt Tray Indicator (`rog-auto-power`)

🇬🇧 **English** | 🇩🇪 **[Deutsch](README.de.md)**

[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/version-0.1.2-brightgreen.svg)](https://github.com/Gigoslav/rog-auto-power/releases)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Arch%20%7C%20KDE%20Plasma%206-informational.svg)](https://github.com/Gigoslav/rog-auto-power)

Intelligent 3-state power management, display refresh-rate switching (`60 Hz` ↔ `240 Hz`), **live Wattage System-Tray indicator (`Total IN = Battery + System`)**, **Battery C-Rate & Charge-Limit Protection**, and **GPU/MUX switcher** (`supergfxctl` + `asus-nb-wmi`) for **ASUS ROG Strix (G17 G713RM)** laptops running Linux & KDE Plasma 6 (Wayland & X11).

Automatically detects your system language (**English `en`** and **German `de`** built-in).

---

## ✨ Features

1. **Automatic 3-State Power, Brightness & Display Switching**
   Detects whether the laptop is on **Battery**, **USB-C Power Delivery (`ucsi-source-psy`)**, or the **240W Barrel AC Adapter (`ADP0`)** via `UPower` D-Bus events & `sysfs`:

   | Power Source | Power Profile | Refresh Rate | Screen Brightness | Keyboard LED | Hardware Tuning |
   | :--- | :--- | :--- | :--- | :--- | :--- |
   | **⚡ Battery (`battery`)** | `power-saver` | **60 Hz** | **50%** | Level 1 | Turbo Off, Panel OD Off, PCIe PM `auto`, Wi-Fi PS `on` (**~12.4 W idle**) |
   | **🔌 USB-C PD (`usbc`)** | `balanced` | **60 Hz** | **75%** | Level 1 | Prevents overloading 45W/65W USB-C chargers (**~0.45 C charging**) |
   | **🚀 240W Barrel (`ac`)** | `performance` | **240 Hz** | **100%** | Level 3 | Full Turbo Boost & Panel Overdrive (**~0.95 C fast charging**) |

2. **Live KDE System-Tray Wattage Badge & Energy Balance (`IN = Battery + System`)**
   * **2-Line Dynamic Tray Icon Badge** updated every 2 seconds:
     * **Charging (Green):** Top line shows **`Total IN`** (`89W`), bottom line shows **`+Battery|System`** (`+64|25`).
     * **Discharging (Amber/Red):** Top line shows **`-SystemW`** (`-12W`), bottom line shows **`OUT`**.
     * **Bypass / Limit Reached (Blue):** Top line shows **`SystemW`**, bottom line shows **`0|SystemW`**.
   * **Detailed Tooltip & Context Menu:**
     ```text
     ⚡ Energy Balance (Live)
     🔌 Total IN:     54.5 W  [USB-C PD (Charging) (Max 60W)]
     ├── 🔋 Battery: +30.3 W  (0.38 C • Charging • 45%/80% • ~0.8h to 80%)
     └── 💻 System:   24.2 W  (Active Load)
            ↳ CPU/iGPU: 17.2W | RTX 3060: 0.0W | Display/Board: 7.0W
     ```
   * **Zero-Wakeup NVIDIA `D3cold` Monitoring:** Reads AMD Ryzen APU Package Power (`PPT`) via `/sys/class/hwmon` (`amdgpu`) and checks NVIDIA RTX 3060 runtime sleep status via `/sys/bus/pci/devices/0000:01:00.0/power/runtime_status` **without ever calling `nvidia-smi`** (which would otherwise wake the dGPU from `D3cold` and waste ~10W).

3. **Battery Protection & Live C-Rate Control**
   * Displays live charging/discharging **C-Rate** (`Watts / 80 Wh`).
   * **⏸️ Stop Charging Now (`0.0 C` Bypass):** Locks `charge_control_end_threshold` to current battery percentage so the laptop runs 100% off the AC adapter with `0.0 W` battery wear.
   * **🛡️ Charge Limits:** One-click switching between **60% (Desk/Ultra)**, **80% (Daily Standard)**, and **100% (Travel Mode)**.

4. **Integrated GPU & Hardware MUX Switcher**
   * **🔋 Integrated:** AMD Radeon 680M only (`0.0 W` NVIDIA).
   * **⚡ Hybrid:** AMD Radeon 680M for desktop + NVIDIA RTX 3060 on-demand (`prime-run`), sleeping at `0.0 W` (`suspended`) when idle.
   * **🔥 Dedicated (`AsusMuxDgpu`):** Hardware MUX switch (`gpu_mux_mode = 0`) routing internal display directly to the NVIDIA RTX 3060.

---

## 🚀 Installation

### Prerequisites (Arch / EndeavourOS)
```bash
sudo pacman -S power-profiles-daemon python-pyqt6 python-dbus nvidia-prime switcheroo-control iw
yay -S supergfxctl
sudo systemctl enable --now supergfxd switcheroo-control
```

### Option A: User & System Helper Install (Recommended)
```bash
git clone https://github.com/Gigoslav/rog-auto-power.git
cd rog-auto-power
./install.sh
```

### Option B: Arch Linux Package (`makepkg`)
```bash
git clone https://github.com/Gigoslav/rog-auto-power.git
cd rog-auto-power
makepkg -si
```

---

## 🛠️ CLI Usage

```bash
# Show current power source, energy balance (IN / Battery / System), C-rate & display status:
auto-power-profile.py --status

# Force English or German output:
auto-power-profile.py --lang en --status
auto-power-profile.py --lang de --status

# Print version, author credits & license:
auto-power-profile.py --version

# Apply appropriate profile & refresh rate once and exit:
auto-power-profile.py --once
```

---

## 👤 Author, Credits & License

* **Author & Maintainer:** **Marcel Berghaus ([Gigoslav](https://github.com/Gigoslav))** — `<berghaus.marcel@gmail.com>`
* **License:** Licensed under the **GNU General Public License v3.0 or later (`GPL-3.0-or-later`)** — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
* **Attribution Requirement (GPLv3 §7b):** All copies, packages, forks, or derivative works **must** retain the original copyright notice, author attribution (`Marcel Berghaus / Gigoslav`), and repository link.
