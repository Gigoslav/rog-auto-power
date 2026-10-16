#!/usr/bin/env python3
"""
Auto Power Profile, Display Refresh Rate Switcher & Live Wattage Tray Indicator
- AC (Barrel Plug):    Performance profile + 240 Hz
- USB-C PD Charger:    Balanced profile    + 60 Hz
- Battery (Unplugged): Power-saver profile + 60 Hz
Includes a live KDE System Tray icon showing Total IN, Battery IN/OUT, and System Watts.
"""

import os
import sys
import glob
import subprocess
import re
import argparse

import dbus
from dbus.mainloop.glib import DBusGMainLoop


def get_power_source() -> str:
    """
    Determine current power source:
    - 'battery': running on battery
    - 'usbc':    charging via USB-C Power Delivery
    - 'ac':      charging via full AC barrel adapter
    """
    power_supply_dir = "/sys/class/power_supply"
    usbc_online = False
    ac_online = False

    if os.path.isdir(power_supply_dir):
        for name in os.listdir(power_supply_dir):
            online_file = os.path.join(power_supply_dir, name, "online")
            if not os.path.exists(online_file):
                continue
            try:
                with open(online_file, "r") as f:
                    val = f.read().strip()
            except Exception:
                continue

            if name.startswith("ucsi-source-psy") and val == "1":
                usbc_online = True
            elif name.startswith(("AC", "ADP", "acad")) and val == "1":
                ac_online = True

    charge_mode_path = "/sys/devices/platform/asus-nb-wmi/charge_mode"
    if ac_online and os.path.exists(charge_mode_path):
        try:
            with open(charge_mode_path, "r") as f:
                cm = f.read().strip()
                if cm == "2":
                    usbc_online = True
        except Exception:
            pass

    if usbc_online:
        return "usbc"
    if ac_online:
        return "ac"

    try:
        bus = dbus.SystemBus()
        up_obj = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower")
        props = dbus.Interface(up_obj, "org.freedesktop.DBus.Properties")
        on_batt = bool(props.Get("org.freedesktop.UPower", "OnBattery"))
        return "battery" if on_batt else "ac"
    except Exception:
        return "battery"


def get_apu_ppt_watts() -> float:
    """Read AMD Ryzen APU (CPU + Radeon 680M iGPU) package power in Watts from hwmon."""
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            name_file = os.path.join(h, "name")
            if os.path.exists(name_file):
                with open(name_file, "r") as f:
                    if f.read().strip() == "amdgpu":
                        p_file = os.path.join(h, "power1_input")
                        if os.path.exists(p_file):
                            with open(p_file, "r") as pf:
                                return int(pf.read().strip()) / 1_000_000.0
        except Exception:
            pass
    return 0.0


def get_dgpu_status_and_watts() -> tuple[str, float]:
    """
    Check NVIDIA dGPU runtime PM state via sysfs ONLY.
    IMPORTANT: Never call nvidia-smi in a polling loop, as nvidia-smi resets the
    kernel runtime PM autosuspend timer and prevents the GPU from entering D3cold (0W)!
    """
    pm_path = "/sys/bus/pci/devices/0000:01:00.0/power/runtime_status"
    pm_state = "unknown"
    if os.path.exists(pm_path):
        try:
            with open(pm_path, "r") as f:
                pm_state = f.read().strip()
        except Exception:
            pass

    if pm_state == "suspended":
        return "suspended", 0.0

    return pm_state, 10.0 if pm_state == "active" else 0.0


def get_backlight_ratio() -> float:
    """Get screen brightness ratio (0.0 to 1.0) via KDE Solid or sysfs."""
    try:
        bus = dbus.SessionBus()
        obj = bus.get_object("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl")
        iface = dbus.Interface(obj, "org.kde.Solid.PowerManagement.Actions.BrightnessControl")
        cur = float(iface.brightness())
        mx = float(iface.brightnessMax())
        if mx > 0:
            return max(0.0, min(1.0, cur / mx))
    except Exception:
        pass
    return 0.5


def set_screen_and_kbd_brightness(screen_pct: int, kbd_level: int):
    """Set screen brightness (0-100%) and keyboard backlight (0-3) via KDE Solid D-Bus."""
    try:
        bus = dbus.SessionBus()
        b_obj = bus.get_object("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/BrightnessControl")
        b_iface = dbus.Interface(b_obj, "org.kde.Solid.PowerManagement.Actions.BrightnessControl")
        b_max = int(b_iface.brightnessMax())
        target_b = int(round((screen_pct / 100.0) * b_max))
        b_iface.setBrightnessSilent(target_b)
    except Exception as e:
        print(f"[Brightness] Failed to set screen brightness: {e}")

    try:
        bus = dbus.SessionBus()
        k_obj = bus.get_object("org.kde.Solid.PowerManagement", "/org/kde/Solid/PowerManagement/Actions/KeyboardBrightnessControl")
        k_iface = dbus.Interface(k_obj, "org.kde.Solid.PowerManagement.Actions.KeyboardBrightnessControl")
        k_iface.setKeyboardBrightnessSilent(int(kbd_level))
    except Exception as e:
        print(f"[Brightness] Failed to set keyboard backlight: {e}")


def apply_hardware_tunings(state: str):
    """Run selective root helper for PCIe Runtime PM, CPU Boost, Panel Overdrive & Wi-Fi Power Save."""
    if os.path.exists("/usr/local/bin/rog-gpu-mux-helper"):
        try:
            subprocess.Popen(
                ["sudo", "-n", "/usr/local/bin/rog-gpu-mux-helper", f"power-{state}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


def get_power_telemetry(current_hz: float = 60.0) -> dict:
    """
    Compute complete power telemetry:
    - total_in_watts: Total power coming from charger (0.0 on battery)
    - bat_watts:      Power going into (+) or out of (-) the battery
    - sys_watts:      Power consumed by the laptop system itself
    - apu_watts:      AMD CPU + iGPU package power
    - dgpu_watts:     NVIDIA RTX 3060 power (0.0W when suspended)
    - rest_watts:     Display + Mainboard + NVMe + Wi-Fi
    """
    bat_dir = "/sys/class/power_supply/BAT0"
    status = "Unknown"
    bat_watts = 0.0
    capacity = 0
    energy_now_wh = 0.0
    energy_full_wh = 0.0
    usbc_amps = 0.0

    charge_limit = 80
    try:
        with open(os.path.join(bat_dir, "status"), "r") as f:
            status = f.read().strip()
        with open(os.path.join(bat_dir, "power_now"), "r") as f:
            bat_watts = int(f.read().strip()) / 1_000_000.0
        with open(os.path.join(bat_dir, "capacity"), "r") as f:
            capacity = int(f.read().strip())
        with open(os.path.join(bat_dir, "energy_now"), "r") as f:
            energy_now_wh = int(f.read().strip()) / 1_000_000.0
        with open(os.path.join(bat_dir, "energy_full"), "r") as f:
            energy_full_wh = int(f.read().strip()) / 1_000_000.0
        limit_file = os.path.join(bat_dir, "charge_control_end_threshold")
        if os.path.exists(limit_file):
            with open(limit_file, "r") as f:
                charge_limit = int(f.read().strip())
    except Exception:
        pass

    usbc_curr = "/sys/class/power_supply/ucsi-source-psy-USBC000:001/current_now"
    if os.path.exists(usbc_curr):
        try:
            with open(usbc_curr, "r") as f:
                usbc_amps = int(f.read().strip()) / 1_000_000.0
        except Exception:
            pass

    apu_watts = get_apu_ppt_watts()
    dgpu_state, dgpu_watts = get_dgpu_status_and_watts()

    # Estimate board + display backlight + refresh rate overhead when on AC/USB-C
    bl_ratio = get_backlight_ratio()
    hz_extra = 2.2 if (current_hz and current_hz > 100) else 0.0
    estimated_rest = 3.2 + (3.8 * bl_ratio) + hz_extra

    if status == "Discharging":
        # On battery, BAT0 power_now IS the exact total system consumption
        sys_watts = bat_watts
        rest_watts = max(0.5, sys_watts - apu_watts - dgpu_watts)
        total_in_watts = 0.0
    elif status == "Charging":
        # On charger, System = APU + dGPU + Rest; Total IN = Battery IN + System
        rest_watts = estimated_rest
        sys_watts = apu_watts + dgpu_watts + rest_watts
        total_in_watts = bat_watts + sys_watts
    else:
        # Full / Not charging (at charge limit threshold on AC)
        rest_watts = estimated_rest
        sys_watts = apu_watts + dgpu_watts + rest_watts
        bat_watts = 0.0
        total_in_watts = sys_watts

    c_rate = (bat_watts / energy_full_wh) if energy_full_wh > 0 else 0.0

    return {
        "status": status,
        "total_in_watts": total_in_watts,
        "bat_watts": bat_watts,
        "c_rate": c_rate,
        "charge_limit": charge_limit,
        "sys_watts": sys_watts,
        "apu_watts": apu_watts,
        "dgpu_state": dgpu_state,
        "dgpu_watts": dgpu_watts,
        "rest_watts": rest_watts,
        "capacity": capacity,
        "energy_now_wh": energy_now_wh,
        "energy_full_wh": energy_full_wh,
        "usbc_amps": usbc_amps,
        "usbc_max_watts": usbc_amps * 20.0,
    }


def get_current_power_profile() -> str:
    """Get the currently active power-profiles-daemon profile."""
    try:
        res = subprocess.check_output(["powerprofilesctl", "get"], stderr=subprocess.DEVNULL)
        return res.decode().strip()
    except Exception:
        return "unknown"


def set_power_profile(profile: str) -> bool:
    """Set the power profile via powerprofilesctl."""
    current = get_current_power_profile()
    if current == profile:
        return False
    try:
        subprocess.check_call(["powerprofilesctl", "set", profile], stderr=subprocess.DEVNULL)
        print(f"[PowerProfile] Profile switched: {current} -> {profile}")
        return True
    except Exception as e:
        print(f"[PowerProfile] Failed to set profile to {profile}: {e}")
        return False


def get_panel_info():
    """
    Get the internal panel name, current resolution, current rate, and available rates.
    Uses kscreen-doctor first, falls back to xrandr.
    """
    try:
        out = subprocess.check_output(["kscreen-doctor", "-o"], stderr=subprocess.DEVNULL).decode()
        for block in out.split("Output: "):
            if not block.strip():
                continue
            lines = block.splitlines()
            header = lines[0].split()
            output_name = header[1] if len(header) > 1 else header[0]
            is_panel = any("Panel" in l for l in lines)
            is_connected = "connected" in block and "enabled" in block

            if (is_panel or output_name.startswith(("eDP", "DP-2"))) and is_connected:
                current_rate = None
                available_rates = []
                current_res = "2560x1440"
                for l in lines:
                    if "Modes:" in l:
                        modes_matches = re.findall(r'(\d+x\d+)@(\d+(?:\.\d+)?)([\*\!]*)', l)
                        for res, rate_str, flags in modes_matches:
                            rate = float(rate_str)
                            available_rates.append((res, rate))
                            if "*" in flags:
                                current_rate = rate
                                current_res = res
                return output_name, current_res, current_rate, available_rates
    except Exception:
        pass

    try:
        out = subprocess.check_output(["xrandr", "--current"], stderr=subprocess.DEVNULL).decode()
        current_disp = None
        current_res = None
        current_rate = None
        available_rates = []
        is_active_panel = False

        for line in out.splitlines():
            m_disp = re.match(r"^(\S+)\s+connected.*", line)
            if m_disp:
                name = m_disp.group(1)
                if current_disp and is_active_panel:
                    break
                current_disp = name
                is_active_panel = name.startswith(("eDP", "DP-2", "DP-0")) or "primary" in line
                continue
            if current_disp and is_active_panel:
                m_mode = re.match(r"^\s+(\d+x\d+)\s+(.*)", line)
                if m_mode:
                    res = m_mode.group(1)
                    raw_rates = m_mode.group(2).split()
                    for r in raw_rates:
                        clean_r = r.replace("+", "").replace("*", "")
                        try:
                            rate_val = float(clean_r)
                            available_rates.append((res, rate_val))
                            if "*" in r:
                                current_rate = rate_val
                                current_res = res
                        except ValueError:
                            pass
        if current_disp:
            return current_disp, current_res or "2560x1440", current_rate, available_rates
    except Exception:
        pass

    return "eDP-1", "2560x1440", None, []


def set_display_refresh_rate(target_rate: int) -> bool:
    """Set the internal display refresh rate using kscreen-doctor or xrandr."""
    panel_name, current_res, current_rate, available_rates = get_panel_info()
    if not panel_name:
        return False

    if current_rate is not None and abs(current_rate - target_rate) < 1.0:
        return False

    res = current_res or "2560x1440"
    print(f"[Display] Changing {panel_name} ({res}) refresh rate: {current_rate}Hz -> {target_rate}Hz")

    try:
        mode_str = f"{res}@{target_rate}"
        cmd = ["kscreen-doctor", f"output.{panel_name}.mode.{mode_str}"]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass

    try:
        cmd = ["xrandr", "--output", panel_name, "--mode", res, "--rate", f"{target_rate:.2f}"]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"[Display] Error switching display rate with xrandr: {e}")
        return False


def send_notification(title: str, message: str, icon: str = "preferences-system-power-management"):
    """Send a desktop notification to the user."""
    try:
        subprocess.Popen(
            ["notify-send", "-u", "low", "-a", "AutoPower", "-i", icon, title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass


STATE_CONFIG = {
    "battery": {
        "profile": "power-saver",
        "hz": 60,
        "brightness": 50,
        "kbd": 1,
        "label": "Battery (Akkubetrieb)",
        "title": "⚡ Akkubetrieb aktiviert",
        "msg": "Power-Saver | 60 Hz | 50% Helligkeit | Eco-Tuning",
        "icon": "battery-good",
    },
    "usbc": {
        "profile": "balanced",
        "hz": 60,
        "brightness": 75,
        "kbd": 1,
        "label": "USB-C PD (Ladebetrieb)",
        "title": "🔌 USB-C Laden aktiviert",
        "msg": "Balanced | 60 Hz | 75% Helligkeit",
        "icon": "ac-adapter",
    },
    "ac": {
        "profile": "performance",
        "hz": 240,
        "brightness": 100,
        "kbd": 3,
        "label": "AC 240W (Netzbetrieb)",
        "title": "🚀 Netzbetrieb (240W) aktiviert",
        "msg": "Performance | 240 Hz | 100% Helligkeit",
        "icon": "ac-adapter",
    },
}


class PowerManagerController:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.last_state = None
        self.auto_mode = True
        self.cached_panel = ("eDP-1", "2560x1440", 60.0, [])
        self.cached_profile = "balanced"

    def apply_state(self, force: bool = False):
        if not self.auto_mode and not force:
            return

        new_state = get_power_source()
        cfg = STATE_CONFIG[new_state]
        prof = cfg["profile"]
        hz = cfg["hz"]

        state_changed = (self.last_state is not None and self.last_state != new_state)
        prof_changed = set_power_profile(prof)
        rate_changed = set_display_refresh_rate(hz)

        if state_changed or force:
            set_screen_and_kbd_brightness(cfg["brightness"], cfg["kbd"])
            apply_hardware_tunings(new_state)

        self.cached_panel = get_panel_info()
        self.cached_profile = get_current_power_profile()
        _, _, current_rate, _ = self.cached_panel
        display_ok = (current_rate is not None and abs(current_rate - hz) < 1.0)

        if display_ok:
            self.last_state = new_state

        if self.verbose and (state_changed or prof_changed or rate_changed or force):
            print(f"[AutoPower] State: {new_state.upper()} | Profile: {prof} | Refresh Rate: {hz}Hz (Display OK: {display_ok})")

        if state_changed or force:
            send_notification(cfg["title"], cfg["msg"], cfg["icon"])


def run_gui_daemon(controller: PowerManagerController):
    """Run the PyQt6 System Tray live Wattage monitor + DBus event loop."""
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
    from PyQt6.QtCore import Qt, QTimer, QRect

    DBusGMainLoop(set_as_default=True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon()

    def create_watt_icon(tel: dict) -> QIcon:
        size = 64
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        status = tel["status"]
        total_in = int(round(tel["total_in_watts"]))
        bat_w = int(round(tel["bat_watts"]))
        sys_w = int(round(tel["sys_watts"]))

        if status == "Charging":
            bg_color = QColor(16, 124, 65, 235)      # Emerald green
            border_color = QColor(52, 211, 153)      # Bright mint
            top_text = f"{total_in}W"
            bot_text = f"+{bat_w}|{sys_w}"
        elif status == "Discharging":
            if sys_w >= 25:
                bg_color = QColor(185, 28, 28, 235)  # Red
                border_color = QColor(248, 113, 113)
            else:
                bg_color = QColor(180, 83, 9, 235)   # Amber/Orange
                border_color = QColor(251, 191, 36)
            top_text = f"-{sys_w}W"
            bot_text = f"OUT"
        else:
            bg_color = QColor(30, 64, 175, 235)      # Blue (80% Limit / Full)
            border_color = QColor(96, 165, 250)
            top_text = f"{sys_w}W"
            bot_text = f"0|{sys_w}"

        # Draw rounded badge
        painter.setBrush(bg_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 12, 12)

        # Top line: Total IN (on charger) or Total OUT (on battery)
        font_top = QFont("Sans Serif", 16 if len(top_text) <= 4 else 13, QFont.Weight.Bold)
        painter.setFont(font_top)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRect(0, 4, size, 32), int(Qt.AlignmentFlag.AlignCenter), top_text)

        # Bottom line: +Bat|Sys (on charger) or OUT (on battery)
        font_bot = QFont("Sans Serif", 10 if len(bot_text) > 4 else 11, QFont.Weight.Bold)
        painter.setFont(font_bot)
        painter.setPen(border_color)
        painter.drawText(QRect(0, 34, size, 24), int(Qt.AlignmentFlag.AlignCenter), bot_text)

        painter.end()
        return QIcon(pix)

    # Context Menu
    menu = QMenu()
    act_header = QAction("⚡ Live Energie-Bilanz", menu)
    act_header.setEnabled(False)
    menu.addAction(act_header)

    act_total_in = QAction("🔌 Gesamt IN: ...", menu)
    act_total_in.setEnabled(False)
    menu.addAction(act_total_in)

    act_bat = QAction("├── 🔋 Davon Akku: ...", menu)
    act_bat.setEnabled(False)
    menu.addAction(act_bat)

    act_sys = QAction("└── 💻 Davon System: ...", menu)
    act_sys.setEnabled(False)
    menu.addAction(act_sys)

    act_sys_detail = QAction("       (CPU/iGPU | RTX | Rest)", menu)
    act_sys_detail.setEnabled(False)
    menu.addAction(act_sys_detail)

    menu.addSeparator()

    act_state = QAction("⚙️ Profil: ...", menu)
    act_state.setEnabled(False)
    menu.addAction(act_state)

    act_auto = QAction("🔄 Automatik-Modus", menu)
    act_auto.setCheckable(True)
    act_auto.setChecked(True)

    def toggle_auto(checked):
        controller.auto_mode = checked
        if checked:
            controller.apply_state(force=True)
            update_tray()

    act_auto.triggered.connect(toggle_auto)
    menu.addAction(act_auto)
    menu.addSeparator()

    def manual_set(prof: str, hz: int):
        controller.auto_mode = False
        act_auto.setChecked(False)
        set_power_profile(prof)
        set_display_refresh_rate(hz)
        controller.cached_profile = get_current_power_profile()
        controller.cached_panel = get_panel_info()
        send_notification("⚙️ Manuelles Profil", f"Profil: {prof} | Display: {hz} Hz")
        update_tray()

    act_ps = QAction("🌱 Power-Saver + 60 Hz", menu)
    act_ps.triggered.connect(lambda: manual_set("power-saver", 60))
    menu.addAction(act_ps)

    act_bal = QAction("⚖️ Balanced + 60 Hz", menu)
    act_bal.triggered.connect(lambda: manual_set("balanced", 60))
    menu.addAction(act_bal)

    act_perf = QAction("🚀 Performance + 240 Hz", menu)
    act_perf.triggered.connect(lambda: manual_set("performance", 240))
    menu.addAction(act_perf)

    menu.addSeparator()
    act_gpu_status = QAction("🎮 GPU-Modus: ...", menu)
    act_gpu_status.setEnabled(False)
    menu.addAction(act_gpu_status)

    def get_gpu_mode() -> str:
        try:
            res = subprocess.check_output(["supergfxctl", "-g"], stderr=subprocess.DEVNULL, timeout=1.5).decode().strip()
        except Exception:
            res = "n/a"
        pm_path = "/sys/bus/pci/devices/0000:01:00.0/power/runtime_status"
        if os.path.exists(pm_path):
            try:
                with open(pm_path, "r") as f:
                    pm = f.read().strip()
                if pm == "suspended":
                    return f"{res} (RTX 3060: 💤 0W)"
                elif pm == "active":
                    return f"{res} (RTX 3060: ⚡ Aktiv)"
            except Exception:
                pass
        return res

    def switch_gpu_mode(mode: str):
        current = get_gpu_mode()
        try:
            if mode == "AsusMuxDgpu":
                subprocess.check_call(["sudo", "/usr/local/bin/rog-gpu-mux-helper", "AsusMuxDgpu"])
                send_notification("🎮 GPU-Umschaltung (MUX -> NVIDIA)", "MUX-Switch für nächsten Neustart auf Dedicated NVIDIA gestellt. Bitte neu starten!")
            elif current.startswith("AsusMuxDgpu"):
                subprocess.check_call(["sudo", "/usr/local/bin/rog-gpu-mux-helper", mode])
                send_notification(f"🎮 GPU-Umschaltung (MUX -> {mode})", f"MUX-Switch auf {mode} vorbereitet. Bitte Laptop einmal neu starten!")
            else:
                subprocess.check_call(["supergfxctl", "-m", mode])
                send_notification("🎮 GPU-Umschaltung (supergfxctl)", f"GPU-Modus '{mode}' gesetzt. Bitte einmal ab- und wieder anmelden!")
        except Exception as e:
            send_notification("⚠️ GPU-Umschaltung Fehler", str(e))
        update_tray()

    act_gpu_int = QAction("🔋 GPU: Integrated (Nur AMD, 0W NVIDIA)", menu)
    act_gpu_int.triggered.connect(lambda: switch_gpu_mode("Integrated"))
    menu.addAction(act_gpu_int)

    act_gpu_hyb = QAction("⚡ GPU: Hybrid (AMD + NVIDIA für Games)", menu)
    act_gpu_hyb.triggered.connect(lambda: switch_gpu_mode("Hybrid"))
    menu.addAction(act_gpu_hyb)

    act_gpu_ded = QAction("🔥 GPU: AsusMuxDgpu (MUX Direkt NVIDIA)", menu)
    act_gpu_ded.triggered.connect(lambda: switch_gpu_mode("AsusMuxDgpu"))
    menu.addAction(act_gpu_ded)

    menu.addSeparator()
    act_bat_prot = QAction("🛡️ Akku-Schutz (Limit: 80%)", menu)
    act_bat_prot.setEnabled(False)
    menu.addAction(act_bat_prot)

    def set_charge_limit(limit: int, label: str):
        try:
            subprocess.check_call(["sudo", "-n", "/usr/local/bin/rog-gpu-mux-helper", "charge-limit", str(limit)])
            send_notification("🛡️ Akku-Schutzmodus", f"{label} aktiviert (Lade-Limit: {limit}%)")
        except Exception as e:
            send_notification("⚠️ Akku-Schutz Fehler", str(e))
        update_tray()

    def stop_charging_now():
        tel_now = get_power_telemetry()
        cur_cap = max(20, min(100, tel_now["capacity"]))
        set_charge_limit(cur_cap, f"Laden sofort gestoppt (0.0 C Bypass bei {cur_cap}%)")

    act_lim_stop = QAction("⏸️ Laden sofort stoppen (0.0 C Bypass)", menu)
    act_lim_stop.triggered.connect(stop_charging_now)
    menu.addAction(act_lim_stop)

    act_lim_60 = QAction("🛡️ Ultra-Schutz: Max 60% (Schreibtisch)", menu)
    act_lim_60.triggered.connect(lambda: set_charge_limit(60, "Ultra-Schutz (60%)"))
    menu.addAction(act_lim_60)

    act_lim_80 = QAction("⚖️ Standard-Schutz: Max 80% (Alltag)", menu)
    act_lim_80.triggered.connect(lambda: set_charge_limit(80, "Standard-Schutz (80%)"))
    menu.addAction(act_lim_80)

    act_lim_100 = QAction("🎒 Reise-Modus: Max 100% (Voll)", menu)
    act_lim_100.triggered.connect(lambda: set_charge_limit(100, "Reise-Modus (100%)"))
    menu.addAction(act_lim_100)

    tray.setContextMenu(menu)

    tick_count = 0
    cached_gpu_mode = get_gpu_mode()

    def update_tray():
        nonlocal tick_count, cached_gpu_mode
        tick_count += 1

        if tick_count % 3 == 1:
            controller.apply_state()
            cached_gpu_mode = get_gpu_mode()

        prof = controller.cached_profile
        panel_name, _, rate, _ = controller.cached_panel
        rate_val = rate if rate else 60.0
        rate_str = f"{int(rate_val)} Hz"

        tel = get_power_telemetry(rate_val)
        status = tel["status"]
        cap = tel["capacity"]
        limit = tel["charge_limit"]
        c_rate = tel["c_rate"]
        src = get_power_source()
        src_label = STATE_CONFIG[src]["label"]

        total_in = tel["total_in_watts"]
        bat_w = tel["bat_watts"]
        sys_w = tel["sys_watts"]
        apu_w = tel["apu_watts"]
        dgpu_w = tel["dgpu_watts"]
        rest_w = tel["rest_watts"]

        usbc_extra = f" (Max {tel['usbc_max_watts']:.0f}W)" if src == "usbc" and tel["usbc_max_watts"] > 0 else ""

        if status == "Charging":
            rem_wh = max(0.0, tel["energy_full_wh"] * (limit / 100.0) - tel["energy_now_wh"])
            eta = f"~{rem_wh / bat_w:.1f}h bis {limit}%" if bat_w > 1.0 and rem_wh > 0 else f"Fast {limit}%"
            line_in = f"🔌 Gesamt IN:   {total_in:5.1f} W  [{src_label}{usbc_extra}]"
            line_bat = f"├── 🔋 Akku:   +{bat_w:5.1f} W  ({c_rate:.2f} C • Lädt • {cap}%/{limit}% • {eta})"
            line_sys = f"└── 💻 System:  {sys_w:5.1f} W  (Laufender Betrieb)"
        elif status == "Discharging":
            eta = f"~{tel['energy_now_wh'] / bat_w:.1f}h Rest" if bat_w > 1.0 else ""
            line_in = f"🔌 Gesamt IN:     0.0 W  [Kein Netzteil]"
            line_bat = f"├── 🔋 Akku:   -{bat_w:5.1f} W  ({c_rate:.2f} C • Entlädt • {cap}% • {eta})"
            line_sys = f"└── 💻 System:  {sys_w:5.1f} W  (Aus dem Akku)"
        else:
            line_in = f"🔌 Gesamt IN:   {total_in:5.1f} W  [{src_label}{usbc_extra}]"
            line_bat = f"├── 🔋 Akku:      0.0 W  (0.00 C • {cap}% • Bypass bei {limit}% Limit)"
            line_sys = f"└── 💻 System:  {sys_w:5.1f} W  (Direkt vom Netzteil)"

        line_detail = f"       ↳ CPU/iGPU: {apu_w:.1f}W | RTX 3060: {dgpu_w:.1f}W | Display/Rest: {rest_w:.1f}W"

        tray.setIcon(create_watt_icon(tel))

        act_total_in.setText(line_in)
        act_bat.setText(line_bat)
        act_sys.setText(line_sys)
        act_sys_detail.setText(line_detail)
        act_state.setText(f"⚙️ Profil: {prof} | {panel_name} @ {rate_str}")
        act_gpu_status.setText(f"🎮 GPU-Modus: {cached_gpu_mode}")
        act_bat_prot.setText(f"🛡️ Akku-Schutz: Limit {limit}% ({c_rate:.2f} C)")

        tooltip = (
            f"⚡ Energie-Bilanz (Live)\n"
            f"{line_in}\n"
            f"{line_bat}\n"
            f"{line_sys}\n"
            f"{line_detail}\n"
            f"──────────────────────────\n"
            f"🛡️ Akku-Limit: {limit}% | Rate: {c_rate:.2f} C\n"
            f"⚙️ Profil: {prof} | Display: {rate_str}\n"
            f"🎮 GPU: {cached_gpu_mode}"
        )
        tray.setToolTip(tooltip)

    try:
        bus = dbus.SystemBus()
        bus.add_signal_receiver(
            lambda interface, changed, invalidated: (
                controller.apply_state(),
                update_tray()
            ) if ("OnBattery" in changed or "Online" in changed) else None,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            path=None
        )
    except Exception:
        pass

    controller.apply_state(force=True)
    update_tray()
    tray.show()

    timer = QTimer()
    timer.timeout.connect(update_tray)
    timer.start(2000)

    print("[AutoPower] Tray indicator & daemon started.")
    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(description="Auto Power Profile & Refresh Rate Switcher")
    parser.add_argument("--once", action="store_true", help="Apply current settings once and exit")
    parser.add_argument("--status", action="store_true", help="Print current status and detection")
    args = parser.parse_args()

    if args.status:
        src = get_power_source()
        cfg = STATE_CONFIG[src]
        current_prof = get_current_power_profile()
        panel_name, current_res, current_rate, available_rates = get_panel_info()
        tel = get_power_telemetry(current_rate or 60.0)
        sign = "+" if tel["status"] == "Charging" else ("-" if tel["status"] == "Discharging" else "")
        print("=== AutoPower & Energie-Bilanz ===")
        print(f"Power Source:    {cfg['label']}")
        print(f"Gesamt IN:       {tel['total_in_watts']:.2f} W")
        print(f"├── Davon Akku:  {sign}{tel['bat_watts']:.2f} W ({tel['c_rate']:.2f} C) [{tel['status']}] (Akku: {tel['capacity']}% / Limit: {tel['charge_limit']}%)")
        print(f"└── Davon System:{tel['sys_watts']:6.2f} W (CPU/iGPU: {tel['apu_watts']:.1f}W | RTX 3060: {tel['dgpu_watts']:.1f}W [{tel['dgpu_state']}] | Display/Board: {tel['rest_watts']:.1f}W)")
        print(f"Current Profile: {current_prof}")
        print(f"Panel:           {panel_name} ({current_res}) @ {current_rate} Hz")
        return

    controller = PowerManagerController()
    if args.once:
        controller.apply_state(force=True)
    else:
        run_gui_daemon(controller)


if __name__ == "__main__":
    main()
