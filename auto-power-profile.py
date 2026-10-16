#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Berghaus (Gigoslav) <berghaus.marcel@gmail.com>
# Website: https://lexchaos.de
# Project: https://github.com/Gigoslav/rog-auto-power
"""
ROG Auto-Power & Live Wattage Tray Indicator (rog-auto-power)
- AC (Barrel Plug):    Performance profile + 240 Hz
- USB-C PD Charger:    Balanced profile    + 60 Hz
- Battery (Unplugged): Power-saver profile + 60 Hz
Includes a live KDE System Tray icon showing Total IN, Battery IN/OUT (with C-rate),
System Watts, Battery Protection modes, and GPU/MUX switching.
Supports automatic German (de) and English (en) localization based on system locale.
"""

import os
import sys
import glob
import locale
import subprocess
import re
import argparse

import dbus
from dbus.mainloop.glib import DBusGMainLoop

APP_NAME = "rog-auto-power"
APP_VERSION = "0.1.2"
APP_AUTHOR = "Marcel Berghaus (Gigoslav)"
APP_EMAIL = "berghaus.marcel@gmail.com"
APP_WEBSITE = "https://lexchaos.de"
APP_URL = "https://github.com/Gigoslav/rog-auto-power"
APP_LICENSE = "GPL-3.0-or-later"


def detect_language() -> str:
    """Detect whether system language is German ('de') or default to English ('en')."""
    for env_var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(env_var, "")
        if val:
            return "de" if val.lower().startswith("de") else "en"
    try:
        loc = locale.getdefaultlocale()[0] or ""
        if loc.lower().startswith("de"):
            return "de"
    except Exception:
        pass
    return "en"


LANG = detect_language()

I18N = {
    "de": {
        "bat_label": "Akkubetrieb",
        "bat_title": "⚡ Akkubetrieb aktiviert",
        "bat_msg": "Stromsparmodus | 60 Hz | 50% Helligkeit | Eco-Modus",
        "usbc_label": "USB-C PD (Ladebetrieb)",
        "usbc_title": "🔌 USB-C Laden aktiviert",
        "usbc_msg": "Ausgeglichen | 60 Hz | 75% Helligkeit",
        "ac_label": "Netzteil 240W (Netzbetrieb)",
        "ac_title": "🚀 Netzbetrieb (240W) aktiviert",
        "ac_msg": "Höchstleistung | 240 Hz | 100% Helligkeit",
        "menu_header": "⚡ Aktuelle Energie-Bilanz",
        "auto_mode": "🔄 Automatik-Modus",
        "manual_title": "⚙️ Manuelles Profil",
        "menu_ps": "🌱 Stromsparmodus + 60 Hz",
        "menu_bal": "⚖️ Ausgeglichen + 60 Hz",
        "menu_perf": "🚀 Höchstleistung + 240 Hz",
        "gpu_active": "⚡ Aktiv",
        "gpu_sleep": "💤 0W Schlafmodus",
        "gpu_mux_nv_title": "🎮 GPU-Umschaltung (MUX -> NVIDIA)",
        "gpu_mux_nv_msg": "Hardware-MUX für nächsten Neustart auf dedizierte NVIDIA gestellt. Bitte neu starten!",
        "gpu_mux_prep_title": "🎮 GPU-Umschaltung (MUX -> {mode})",
        "gpu_mux_prep_msg": "Hardware-MUX auf {mode} vorbereitet. Bitte Laptop einmal neu starten!",
        "gpu_super_title": "🎮 GPU-Umschaltung (supergfxctl)",
        "gpu_super_msg": "GPU-Modus '{mode}' gesetzt. Bitte einmal ab- und wieder anmelden!",
        "gpu_err_title": "⚠️ GPU-Umschaltung Fehler",
        "gpu_int_menu": "🔋 GPU: Integriert (Nur AMD, 0W NVIDIA)",
        "gpu_hyb_menu": "⚡ GPU: Hybrid (AMD + NVIDIA für Spiele)",
        "gpu_ded_menu": "🔥 GPU: Dediziert (MUX Direkt NVIDIA)",
        "bat_prot_title": "🛡️ Akku-Schutzmodus",
        "bat_prot_msg": "{label} aktiviert (Lade-Limit: {limit}%)",
        "bat_prot_err": "⚠️ Akku-Schutz Fehler",
        "stop_now_msg": "Laden sofort gestoppt (0.0 C Direktbetrieb bei {cap}%)",
        "menu_lim_stop": "⏸️ Laden sofort stoppen (0.0 C Direktbetrieb)",
        "menu_lim_60": "🛡️ Ultra-Schutz: Max 60% (Schreibtisch)",
        "menu_lim_80": "⚖️ Standard-Schutz: Max 80% (Alltag)",
        "menu_lim_100": "🎒 Reise-Modus: Max 100% (Vollladung)",
        "lbl_lim_60": "Ultra-Schutz (60%)",
        "lbl_lim_80": "Standard-Schutz (80%)",
        "lbl_lim_100": "Reise-Modus (100%)",
        "eta_to_limit": "~{h:.1f}h bis {limit}%",
        "eta_almost": "Fast {limit}%",
        "eta_rem": "~{h:.1f}h Restlaufzeit",
        "no_charger": "Kein Netzteil",
        "line_in": "🔌 Eingang Gesamt:{total_in:5.1f} W  [{src_label}{usbc_extra}]",
        "line_in_none": "🔌 Eingang Gesamt:  0.0 W  [Kein Netzteil]",
        "line_bat_chg": "├── 🔋 Akku:     +{bat_w:5.1f} W  ({c_rate:.2f} C • Lädt • {cap}%/{limit}% • {eta})",
        "line_bat_dis": "├── 🔋 Akku:     -{bat_w:5.1f} W  ({c_rate:.2f} C • Entlädt • {cap}% • {eta})",
        "line_bat_byp": "├── 🔋 Akku:        0.0 W  (0.00 C • {cap}% • Direktbetrieb bei {limit}% Limit)",
        "line_sys_run": "└── 💻 System:    {sys_w:5.1f} W  (Laufender Betrieb)",
        "line_sys_bat": "└── 💻 System:    {sys_w:5.1f} W  (Aus dem Akku)",
        "line_sys_ac": "└── 💻 System:    {sys_w:5.1f} W  (Direkt vom Netzteil)",
        "line_detail": "       ↳ CPU/iGPU: {apu_w:.1f}W | RTX 3060: {dgpu_w:.1f}W | Bildschirm/Mainboard: {rest_w:.1f}W",
        "menu_profile": "⚙️ Profil: {prof} | {panel} @ {rate}",
        "menu_gpu": "🎮 GPU-Modus: {gpu}",
        "menu_bat_prot": "🛡️ Akku-Schutz: Limit {limit}% ({c_rate:.2f} C)",
        "tt_header": "⚡ Energie-Bilanz (Echtzeit)",
        "tt_limit": "🛡️ Akku-Limit: {limit}% | Laderate: {c_rate:.2f} C",
        "tt_profile": "⚙️ Profil: {prof} | Bildschirm: {rate}",
        "tt_gpu": "🎮 GPU: {gpu}",
        "cli_header": "=== ROG Auto-Power & Energie-Bilanz ===",
        "cli_source": "Stromquelle:     {label}",
        "cli_total_in": "Eingang Gesamt:  {w:.2f} W",
        "cli_bat": "├── Davon Akku:  {sign}{w:.2f} W ({c:.2f} C) [{st}] (Stand: {cap}% / Limit: {lim}%)",
        "cli_sys": "└── Davon System:{w:6.2f} W (CPU/iGPU: {apu:.1f}W | RTX 3060: {dgpu:.1f}W [{dst}] | Bildschirm/Mainboard: {rest:.1f}W)",
        "cli_prof": "Aktives Profil:  {prof}",
        "cli_panel": "Bildschirm:      {panel} ({res}) @ {rate} Hz",
        "menu_about": "ℹ️ Über & Credits (v{ver} • Gigoslav • lexchaos.de)",
        "about_title": "⚡ ROG Auto-Power v{ver}",
        "about_msg": "Entwickelt von {author} • Web: {web} • Lizenz: {lic} • {url}",
        "ver_free": "Dies ist freie Software: Sie können sie unter den Bedingungen der GPLv3+ ändern und weitergeben.",
        "ver_attr": "Autoren-Credits (Marcel Berghaus / Gigoslav • lexchaos.de) müssen in allen Kopien erhalten bleiben.",
        "prof_power-saver": "Stromsparmodus",
        "prof_balanced": "Ausgeglichen",
        "prof_performance": "Höchstleistung",
        "st_Charging": "Lädt",
        "st_Discharging": "Entlädt",
        "st_Not charging": "Direktbetrieb / Lädt nicht",
        "st_Full": "Voll",
        "dst_suspended": "Schlafmodus",
        "dst_active": "Aktiv",
    },
    "en": {
        "bat_label": "Battery (Unplugged)",
        "bat_title": "⚡ Battery Mode Activated",
        "bat_msg": "Power-Saver | 60 Hz | 50% Brightness | Eco-Mode",
        "usbc_label": "USB-C PD (Charging)",
        "usbc_title": "🔌 USB-C Charging Activated",
        "usbc_msg": "Balanced | 60 Hz | 75% Brightness",
        "ac_label": "AC 240W (Plugged In)",
        "ac_title": "🚀 AC Mode (240W) Activated",
        "ac_msg": "Performance | 240 Hz | 100% Brightness",
        "menu_header": "⚡ Live Energy Balance",
        "auto_mode": "🔄 Automatic Mode",
        "manual_title": "⚙️ Manual Profile",
        "menu_ps": "🌱 Power-Saver + 60 Hz",
        "menu_bal": "⚖️ Balanced + 60 Hz",
        "menu_perf": "🚀 Performance + 240 Hz",
        "gpu_active": "⚡ Active",
        "gpu_sleep": "💤 0W Suspended",
        "gpu_mux_nv_title": "🎮 GPU Switch (MUX -> NVIDIA)",
        "gpu_mux_nv_msg": "Hardware MUX set to Dedicated NVIDIA for next boot. Please reboot!",
        "gpu_mux_prep_title": "🎮 GPU Switch (MUX -> {mode})",
        "gpu_mux_prep_msg": "Hardware MUX prepared for {mode}. Please reboot your laptop!",
        "gpu_super_title": "🎮 GPU Switch (supergfxctl)",
        "gpu_super_msg": "GPU mode '{mode}' set. Please log out and log back in!",
        "gpu_err_title": "⚠️ GPU Switch Error",
        "gpu_int_menu": "🔋 GPU: Integrated (AMD Only, 0W NVIDIA)",
        "gpu_hyb_menu": "⚡ GPU: Hybrid (AMD + NVIDIA for Games)",
        "gpu_ded_menu": "🔥 GPU: Dedicated (Direct NVIDIA MUX)",
        "bat_prot_title": "🛡️ Battery Protection Mode",
        "bat_prot_msg": "{label} enabled (Charge Limit: {limit}%)",
        "bat_prot_err": "⚠️ Battery Protection Error",
        "stop_now_msg": "Charging stopped immediately (0.0 C Bypass at {cap}%)",
        "menu_lim_stop": "⏸️ Stop Charging Now (0.0 C Bypass)",
        "menu_lim_60": "🛡️ Ultra Protection: Max 60% (Desk Mode)",
        "menu_lim_80": "⚖️ Standard Protection: Max 80% (Daily)",
        "menu_lim_100": "🎒 Travel Mode: Max 100% (Full Charge)",
        "lbl_lim_60": "Ultra Protection (60%)",
        "lbl_lim_80": "Standard Protection (80%)",
        "lbl_lim_100": "Travel Mode (100%)",
        "eta_to_limit": "~{h:.1f}h to {limit}%",
        "eta_almost": "Almost {limit}%",
        "eta_rem": "~{h:.1f}h remaining",
        "no_charger": "Unplugged",
        "line_in": "🔌 Total IN:    {total_in:5.1f} W  [{src_label}{usbc_extra}]",
        "line_in_none": "🔌 Total IN:      0.0 W  [Unplugged]",
        "line_bat_chg": "├── 🔋 Battery: +{bat_w:5.1f} W  ({c_rate:.2f} C • Charging • {cap}%/{limit}% • {eta})",
        "line_bat_dis": "├── 🔋 Battery: -{bat_w:5.1f} W  ({c_rate:.2f} C • Discharging • {cap}% • {eta})",
        "line_bat_byp": "├── 🔋 Battery:    0.0 W  (0.00 C • {cap}% • Bypass at {limit}% Limit)",
        "line_sys_run": "└── 💻 System:  {sys_w:5.1f} W  (Active Load)",
        "line_sys_bat": "└── 💻 System:  {sys_w:5.1f} W  (From Battery)",
        "line_sys_ac": "└── 💻 System:  {sys_w:5.1f} W  (Direct AC Bypass)",
        "line_detail": "       ↳ CPU/iGPU: {apu_w:.1f}W | RTX 3060: {dgpu_w:.1f}W | Display/Board: {rest_w:.1f}W",
        "menu_profile": "⚙️ Profile: {prof} | {panel} @ {rate}",
        "menu_gpu": "🎮 GPU Mode: {gpu}",
        "menu_bat_prot": "🛡️ Battery Limit: {limit}% ({c_rate:.2f} C)",
        "tt_header": "⚡ Energy Balance (Live)",
        "tt_limit": "🛡️ Charge Limit: {limit}% | Rate: {c_rate:.2f} C",
        "tt_profile": "⚙️ Profile: {prof} | Display: {rate}",
        "tt_gpu": "🎮 GPU: {gpu}",
        "cli_header": "=== ROG Auto-Power & Energy Balance ===",
        "cli_source": "Power Source:    {label}",
        "cli_total_in": "Total IN:        {w:.2f} W",
        "cli_bat": "├── Battery:     {sign}{w:.2f} W ({c:.2f} C) [{st}] (Level: {cap}% / Limit: {lim}%)",
        "cli_sys": "└── System Load: {w:6.2f} W (CPU/iGPU: {apu:.1f}W | RTX 3060: {dgpu:.1f}W [{dst}] | Display/Board: {rest:.1f}W)",
        "cli_prof": "Active Profile:  {prof}",
        "cli_panel": "Display:         {panel} ({res}) @ {rate} Hz",
        "menu_about": "ℹ️ About & Credits (v{ver} • Gigoslav • lexchaos.de)",
        "about_title": "⚡ ROG Auto-Power v{ver}",
        "about_msg": "Created by {author} • Web: {web} • License: {lic} • {url}",
        "ver_free": "This is free software: you are free to change and redistribute it under the terms of the GPLv3+.",
        "ver_attr": "Author attribution (Marcel Berghaus / Gigoslav • lexchaos.de) must be preserved in all copies.",
        "prof_power-saver": "Power-Saver",
        "prof_balanced": "Balanced",
        "prof_performance": "Performance",
        "st_Charging": "Charging",
        "st_Discharging": "Discharging",
        "st_Not charging": "Not charging (AC Bypass)",
        "st_Full": "Full",
        "dst_suspended": "suspended",
        "dst_active": "active",
    },
}


def tr(key: str, **kwargs) -> str:
    """Translate key using current language dictionary."""
    text = I18N.get(LANG, I18N["en"]).get(key, I18N["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


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

    bl_ratio = get_backlight_ratio()
    hz_extra = 2.2 if (current_hz and current_hz > 100) else 0.0
    estimated_rest = 3.2 + (3.8 * bl_ratio) + hz_extra

    if status == "Discharging":
        sys_watts = bat_watts
        rest_watts = max(0.5, sys_watts - apu_watts - dgpu_watts)
        total_in_watts = 0.0
    elif status == "Charging":
        rest_watts = estimated_rest
        sys_watts = apu_watts + dgpu_watts + rest_watts
        total_in_watts = bat_watts + sys_watts
    else:
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


def get_state_config() -> dict:
    return {
        "battery": {
            "profile": "power-saver",
            "hz": 60,
            "brightness": 50,
            "kbd": 1,
            "label": tr("bat_label"),
            "title": tr("bat_title"),
            "msg": tr("bat_msg"),
            "icon": "battery-good",
        },
        "usbc": {
            "profile": "balanced",
            "hz": 60,
            "brightness": 75,
            "kbd": 1,
            "label": tr("usbc_label"),
            "title": tr("usbc_title"),
            "msg": tr("usbc_msg"),
            "icon": "ac-adapter",
        },
        "ac": {
            "profile": "performance",
            "hz": 240,
            "brightness": 100,
            "kbd": 3,
            "label": tr("ac_label"),
            "title": tr("ac_title"),
            "msg": tr("ac_msg"),
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
        cfg = get_state_config()[new_state]
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
            bot_text = "OUT"
        else:
            bg_color = QColor(30, 64, 175, 235)      # Blue (Limit / Full)
            border_color = QColor(96, 165, 250)
            top_text = f"{sys_w}W"
            bot_text = f"0|{sys_w}"

        painter.setBrush(bg_color)
        painter.setPen(border_color)
        painter.drawRoundedRect(2, 2, size - 4, size - 4, 12, 12)

        font_top = QFont("Sans Serif", 16 if len(top_text) <= 4 else 13, QFont.Weight.Bold)
        painter.setFont(font_top)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRect(0, 4, size, 32), int(Qt.AlignmentFlag.AlignCenter), top_text)

        font_bot = QFont("Sans Serif", 10 if len(bot_text) > 4 else 11, QFont.Weight.Bold)
        painter.setFont(font_bot)
        painter.setPen(border_color)
        painter.drawText(QRect(0, 34, size, 24), int(Qt.AlignmentFlag.AlignCenter), bot_text)

        painter.end()
        return QIcon(pix)

    menu = QMenu()
    act_header = QAction(tr("menu_header"), menu)
    act_header.setEnabled(False)
    menu.addAction(act_header)

    act_total_in = QAction("...", menu)
    act_total_in.setEnabled(False)
    menu.addAction(act_total_in)

    act_bat = QAction("...", menu)
    act_bat.setEnabled(False)
    menu.addAction(act_bat)

    act_sys = QAction("...", menu)
    act_sys.setEnabled(False)
    menu.addAction(act_sys)

    act_sys_detail = QAction("...", menu)
    act_sys_detail.setEnabled(False)
    menu.addAction(act_sys_detail)

    menu.addSeparator()

    act_state = QAction("...", menu)
    act_state.setEnabled(False)
    menu.addAction(act_state)

    act_auto = QAction(tr("auto_mode"), menu)
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
        send_notification(tr("manual_title"), f"{tr(f'prof_{prof}')} | {hz} Hz")
        update_tray()

    act_ps = QAction(tr("menu_ps"), menu)
    act_ps.triggered.connect(lambda: manual_set("power-saver", 60))
    menu.addAction(act_ps)

    act_bal = QAction(tr("menu_bal"), menu)
    act_bal.triggered.connect(lambda: manual_set("balanced", 60))
    menu.addAction(act_bal)

    act_perf = QAction(tr("menu_perf"), menu)
    act_perf.triggered.connect(lambda: manual_set("performance", 240))
    menu.addAction(act_perf)

    menu.addSeparator()
    act_gpu_status = QAction("...", menu)
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
                    return f"{res} (RTX 3060: {tr('gpu_sleep')})"
                elif pm == "active":
                    return f"{res} (RTX 3060: {tr('gpu_active')})"
            except Exception:
                pass
        return res

    def switch_gpu_mode(mode: str):
        current = get_gpu_mode()
        try:
            if mode == "AsusMuxDgpu":
                subprocess.check_call(["sudo", "/usr/local/bin/rog-gpu-mux-helper", "AsusMuxDgpu"])
                send_notification(tr("gpu_mux_nv_title"), tr("gpu_mux_nv_msg"))
            elif current.startswith("AsusMuxDgpu"):
                subprocess.check_call(["sudo", "/usr/local/bin/rog-gpu-mux-helper", mode])
                send_notification(tr("gpu_mux_prep_title", mode=mode), tr("gpu_mux_prep_msg", mode=mode))
            else:
                subprocess.check_call(["supergfxctl", "-m", mode])
                send_notification(tr("gpu_super_title"), tr("gpu_super_msg", mode=mode))
        except Exception as e:
            send_notification(tr("gpu_err_title"), str(e))
        update_tray()

    act_gpu_int = QAction(tr("gpu_int_menu"), menu)
    act_gpu_int.triggered.connect(lambda: switch_gpu_mode("Integrated"))
    menu.addAction(act_gpu_int)

    act_gpu_hyb = QAction(tr("gpu_hyb_menu"), menu)
    act_gpu_hyb.triggered.connect(lambda: switch_gpu_mode("Hybrid"))
    menu.addAction(act_gpu_hyb)

    act_gpu_ded = QAction(tr("gpu_ded_menu"), menu)
    act_gpu_ded.triggered.connect(lambda: switch_gpu_mode("AsusMuxDgpu"))
    menu.addAction(act_gpu_ded)

    menu.addSeparator()
    act_bat_prot = QAction("...", menu)
    act_bat_prot.setEnabled(False)
    menu.addAction(act_bat_prot)

    def set_charge_limit(limit: int, label: str):
        try:
            subprocess.check_call(["sudo", "-n", "/usr/local/bin/rog-gpu-mux-helper", "charge-limit", str(limit)])
            send_notification(tr("bat_prot_title"), tr("bat_prot_msg", label=label, limit=limit))
        except Exception as e:
            send_notification(tr("bat_prot_err"), str(e))
        update_tray()

    def stop_charging_now():
        tel_now = get_power_telemetry()
        cur_cap = max(20, min(100, tel_now["capacity"]))
        set_charge_limit(cur_cap, tr("stop_now_msg", cap=cur_cap))

    act_lim_stop = QAction(tr("menu_lim_stop"), menu)
    act_lim_stop.triggered.connect(stop_charging_now)
    menu.addAction(act_lim_stop)

    act_lim_60 = QAction(tr("menu_lim_60"), menu)
    act_lim_60.triggered.connect(lambda: set_charge_limit(60, tr("lbl_lim_60")))
    menu.addAction(act_lim_60)

    act_lim_80 = QAction(tr("menu_lim_80"), menu)
    act_lim_80.triggered.connect(lambda: set_charge_limit(80, tr("lbl_lim_80")))
    menu.addAction(act_lim_80)

    act_lim_100 = QAction(tr("menu_lim_100"), menu)
    act_lim_100.triggered.connect(lambda: set_charge_limit(100, tr("lbl_lim_100")))
    menu.addAction(act_lim_100)

    menu.addSeparator()

    def show_about():
        send_notification(
            tr("about_title", ver=APP_VERSION),
            tr("about_msg", author=APP_AUTHOR, web=APP_WEBSITE, lic=APP_LICENSE, url=APP_URL),
        )
        try:
            subprocess.Popen(["xdg-open", APP_WEBSITE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    act_about = QAction(tr("menu_about", ver=APP_VERSION), menu)
    act_about.triggered.connect(show_about)
    menu.addAction(act_about)

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
        prof_disp = tr(f"prof_{prof}")
        panel_name, _, rate, _ = controller.cached_panel
        rate_val = rate if rate else 60.0
        rate_str = f"{int(rate_val)} Hz"

        tel = get_power_telemetry(rate_val)
        status = tel["status"]
        cap = tel["capacity"]
        limit = tel["charge_limit"]
        c_rate = tel["c_rate"]
        src = get_power_source()
        src_label = get_state_config()[src]["label"]

        total_in = tel["total_in_watts"]
        bat_w = tel["bat_watts"]
        sys_w = tel["sys_watts"]
        apu_w = tel["apu_watts"]
        dgpu_w = tel["dgpu_watts"]
        rest_w = tel["rest_watts"]

        usbc_extra = f" (Max {tel['usbc_max_watts']:.0f}W)" if src == "usbc" and tel["usbc_max_watts"] > 0 else ""

        if status == "Charging":
            rem_wh = max(0.0, tel["energy_full_wh"] * (limit / 100.0) - tel["energy_now_wh"])
            eta = tr("eta_to_limit", h=rem_wh / bat_w, limit=limit) if bat_w > 1.0 and rem_wh > 0 else tr("eta_almost", limit=limit)
            line_in = tr("line_in", total_in=total_in, src_label=src_label, usbc_extra=usbc_extra)
            line_bat = tr("line_bat_chg", bat_w=bat_w, c_rate=c_rate, cap=cap, limit=limit, eta=eta)
            line_sys = tr("line_sys_run", sys_w=sys_w)
        elif status == "Discharging":
            eta = tr("eta_rem", h=tel["energy_now_wh"] / bat_w) if bat_w > 1.0 else ""
            line_in = tr("line_in_none")
            line_bat = tr("line_bat_dis", bat_w=bat_w, c_rate=c_rate, cap=cap, eta=eta)
            line_sys = tr("line_sys_bat", sys_w=sys_w)
        else:
            line_in = tr("line_in", total_in=total_in, src_label=src_label, usbc_extra=usbc_extra)
            line_bat = tr("line_bat_byp", cap=cap, limit=limit)
            line_sys = tr("line_sys_ac", sys_w=sys_w)

        line_detail = tr("line_detail", apu_w=apu_w, dgpu_w=dgpu_w, rest_w=rest_w)

        tray.setIcon(create_watt_icon(tel))

        act_total_in.setText(line_in)
        act_bat.setText(line_bat)
        act_sys.setText(line_sys)
        act_sys_detail.setText(line_detail)
        act_state.setText(tr("menu_profile", prof=prof_disp, panel=panel_name, rate=rate_str))
        act_gpu_status.setText(tr("menu_gpu", gpu=cached_gpu_mode))
        act_bat_prot.setText(tr("menu_bat_prot", limit=limit, c_rate=c_rate))

        tooltip = (
            f"{tr('tt_header')}\n"
            f"{line_in}\n"
            f"{line_bat}\n"
            f"{line_sys}\n"
            f"{line_detail}\n"
            f"──────────────────────────\n"
            f"{tr('tt_limit', limit=limit, c_rate=c_rate)}\n"
            f"{tr('tt_profile', prof=prof_disp, rate=rate_str)}\n"
            f"{tr('tt_gpu', gpu=cached_gpu_mode)}"
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

    print(f"[AutoPower] Tray indicator & daemon started (Language: {LANG}).")
    sys.exit(app.exec())


def main():
    global LANG
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="ASUS ROG Strix Auto Power Profile, Refresh Rate Switcher & Live Wattage Tray Indicator",
        epilog=f"Created by {APP_AUTHOR} <{APP_EMAIL}> ({APP_WEBSITE} | {APP_URL})",
    )
    parser.add_argument("-v", "--version", action="store_true", help="Print version, copyright and license information")
    parser.add_argument("--once", action="store_true", help="Apply current settings once and exit")
    parser.add_argument("--status", action="store_true", help="Print current status and detection")
    parser.add_argument("--lang", choices=["de", "en"], help="Override display language (de/en)")
    args = parser.parse_args()

    if args.lang:
        LANG = args.lang

    if args.version:
        print(f"{APP_NAME} {APP_VERSION}")
        print(f"Copyright (C) 2026 {APP_AUTHOR} <{APP_EMAIL}>")
        print(f"Website:    {APP_WEBSITE}")
        print(f"Repository: {APP_URL}")
        print(f"License:    {APP_LICENSE} <https://www.gnu.org/licenses/gpl-3.0.html>")
        print(tr("ver_free"))
        print(tr("ver_attr"))
        return

    if args.status:
        src = get_power_source()
        cfg = get_state_config()[src]
        current_prof = get_current_power_profile()
        prof_disp = tr(f"prof_{current_prof}")
        panel_name, current_res, current_rate, available_rates = get_panel_info()
        tel = get_power_telemetry(current_rate or 60.0)
        st_disp = tr(f"st_{tel['status']}")
        dst_disp = tr(f"dst_{tel['dgpu_state']}")
        sign = "+" if tel["status"] == "Charging" else ("-" if tel["status"] == "Discharging" else "")
        print(tr("cli_header"))
        print(tr("cli_source", label=cfg["label"]))
        print(tr("cli_total_in", w=tel["total_in_watts"]))
        print(tr("cli_bat", sign=sign, w=tel["bat_watts"], c=tel["c_rate"], st=st_disp, cap=tel["capacity"], lim=tel["charge_limit"]))
        print(tr("cli_sys", w=tel["sys_watts"], apu=tel["apu_watts"], dgpu=tel["dgpu_watts"], dst=dst_disp, rest=tel["rest_watts"]))
        print(tr("cli_prof", prof=prof_disp))
        print(tr("cli_panel", panel=panel_name, res=current_res, rate=current_rate))
        return

    controller = PowerManagerController()
    if args.once:
        controller.apply_state(force=True)
    else:
        run_gui_daemon(controller)


if __name__ == "__main__":
    main()
