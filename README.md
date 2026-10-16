# ⚡ ROG Auto-Power & Live Watt Tray Indicator

Intelligent 3-state power management, display refresh-rate switching (`60 Hz` ↔ `240 Hz`), **live Wattage System-Tray indicator (`Gesamt IN = Akku + System`)**, and **GPU/MUX switcher** (`supergfxctl` + `asus-nb-wmi`) for **ASUS ROG Strix (G17 G713RM)** laptops running Linux & KDE Plasma 6 (Wayland & X11).

---

## ✨ Features

1. **Automatic 3-State Power & Display Switching**
   Detects whether the laptop is on **Battery**, **USB-C Power Delivery (`ucsi-source-psy`)**, or the **240W Barrel AC Adapter (`ADP0`)** via `UPower` D-Bus events & `sysfs`:

   | Power Source | Power Profile (`powerprofilesctl`) | Display Refresh Rate (`kscreen-doctor`) | Purpose |
   | :--- | :--- | :--- | :--- |
   | **⚡ Battery (`battery`)** | `power-saver` | **60 Hz** | Drops idle system draw to **~10–13 W** (5–6h battery life) |
   | **🔌 USB-C PD (`usbc`)** | `balanced` | **60 Hz** | Prevents overloading 45W/65W USB-C chargers; maximizes net battery charge (~30–37 W IN) |
   | **🚀 240W Barrel (`ac`)** | `performance` | **240 Hz** | Full gaming & workstation performance |

2. **Live KDE System-Tray Wattage Badge & Energy Balance (`IN = Battery + System`)**
   * **2-Line Dynamic Tray Icon Badge** updated every 2 seconds:
     * **Charging (Green):** Top line shows **`Gesamt IN`** (`54W`), bottom line shows **`+Akku|System`** (`+30|24`).
     * **Discharging (Amber/Red):** Top line shows **`-SystemW`** (`-13W`), bottom line shows **`OUT`**.
     * **Full / 80% Charge Limit (Blue):** Top line shows **`SystemW`**, bottom line shows **`0|SystemW`**.
   * **Detailed Tooltip & Context Menu:**
     ```text
     ⚡ Energie-Bilanz (Live)
     🔌 Gesamt IN:    54.5 W  [USB-C PD (Ladebetrieb) (Max 60W)]
     ├── 🔋 Akku:    +30.3 W  (Lädt • 45% • ~0.8h bis 80%)
     └── 💻 System:   24.2 W  (Laufender Betrieb)
            ↳ CPU/iGPU: 17.2W | RTX 3060: 0.0W | Display/Rest: 7.0W
     ```
   * Reads AMD Ryzen APU Package Power (`PPT`) directly from `/sys/class/hwmon` (`amdgpu`) and checks NVIDIA RTX 3060 `D3cold` runtime sleep status (`/sys/bus/pci/devices/0000:01:00.0/power/runtime_status`) **without waking the dGPU**.

3. **Integrated GPU & Hardware MUX Switcher**
   Switch directly from the System-Tray context menu between:
   * **🔋 Integrated:** AMD Radeon 680M only (`0.0 W` NVIDIA).
   * **⚡ Hybrid:** AMD Radeon 680M for desktop + NVIDIA RTX 3060 on-demand (`prime-run` / `switcheroo-control`), sleeping at `0.0 W` (`suspended`) when idle.
   * **🔥 AsusMuxDgpu:** Hardware MUX switch (`gpu_mux_mode = 0`) routing internal display directly to the NVIDIA RTX 3060.

---

## 🚀 Installation

### Prerequisites (Arch / EndeavourOS)
```bash
sudo pacman -S power-profiles-daemon python-pyqt6 python-dbus nvidia-prime switcheroo-control
yay -S supergfxctl
sudo systemctl enable --now supergfxd switcheroo-control
```

### Install Service & Helper
```bash
chmod +x install.sh
./install.sh
```

---

## 🛠️ CLI Usage

```bash
# Show current power source, energy balance (IN / Battery / System) & display status:
auto-power-profile.py --status

# Apply appropriate profile & refresh rate once and exit:
auto-power-profile.py --once

# Check systemd user service logs:
journalctl --user -u auto-power-profile.service -f
```
