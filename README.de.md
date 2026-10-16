# ⚡ ROG Auto-Power & Echtzeit-Watt-Anzeige (`rog-auto-power`)

🇬🇧 **[English](README.md)** | 🇩🇪 **Deutsch**

[![Lizenz: GPL v3+](https://img.shields.io/badge/Lizenz-GPLv3%2B-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/Version-0.1.2-brightgreen.svg)](https://github.com/Gigoslav/rog-auto-power/releases)
[![Plattform](https://img.shields.io/badge/Plattform-Linux%20%7C%20Arch%20%7C%20KDE%20Plasma%206-informational.svg)](https://github.com/Gigoslav/rog-auto-power)

Intelligente 3-Stufen-Energieverwaltung, automatische Bildwiederholraten-Umschaltung (`60 Hz` ↔ `240 Hz`), **Echtzeit-Watt-Anzeige in der KDE-Systemleiste (`Eingang Gesamt = Akku + System`)**, **Akku-Schutzmodus mit C-Raten-Anzeige** sowie **GPU-/Hardware-MUX-Umschalter** (`supergfxctl` + `asus-nb-wmi`) für **ASUS ROG Strix (G17 G713RM)** Laptops unter Linux & KDE Plasma 6 (Wayland & X11).

Erkennt automatisch die eingestellte Systemsprache (**Deutsch `de`** und **Englisch `en`** integriert).

---

## ✨ Funktionen

1. **Automatische 3-Stufen-Energie-, Helligkeits- & Bildwiederholraten-Umschaltung**
   Erkennt über `UPower` D-Bus-Signale & `sysfs`, ob der Laptop im **Akkubetrieb**, über **USB-C Power Delivery (`ucsi-source-psy`)** oder am **240W-Netzteil (`ADP0`)** läuft:

   | Stromquelle | Energieprofil | Bildwiederholrate | Bildschirmhelligkeit | Tastatur-LED | Hardware-Optimierung |
   | :--- | :--- | :--- | :--- | :--- | :--- |
   | **⚡ Akkubetrieb (`battery`)** | `Stromsparmodus` | **60 Hz** | **50%** | Stufe 1 | Turbo Aus, Panel-Overdrive Aus, PCIe-Stromsparen `auto`, WLAN-Sparmodus `ein` (**~12,4 W Leerlauf**) |
   | **🔌 USB-C PD (`usbc`)** | `Ausgeglichen` | **60 Hz** | **75%** | Stufe 1 | Schützt 45W/65W USB-C-Ladegeräte vor Überlastung (**~0,45 C schonendes Laden**) |
   | **🚀 240W-Netzteil (`ac`)** | `Höchstleistung` | **240 Hz** | **100%** | Stufe 3 | Voller CPU-Turbo & Panel-Overdrive (**~0,95 C Schnellladen**) |

2. **Echtzeit-Watt-Anzeige im KDE-Systemabschnitt (`Eingang Gesamt = Akku + System`)**
   * **Zweizeiliges dynamisches Tray-Symbol** (Aktualisierung alle 2 Sekunden):
     * **Lädt (Grün):** Obere Zeile zeigt **`Eingang Gesamt`** (`89W`), untere Zeile zeigt **`+Akku|System`** (`+64|25`).
     * **Entlädt (Orange/Rot):** Obere Zeile zeigt **`-SystemW`** (`-12W`), untere Zeile zeigt **`OUT`**.
     * **Direktbetrieb / Lade-Limit erreicht (Blau):** Obere Zeile zeigt **`SystemW`**, untere Zeile zeigt **`0|SystemW`**.
   * **Übersichtliches Kontextmenü & Kurzinfo:**
     ```text
     ⚡ Energie-Bilanz (Echtzeit)
     🔌 Eingang Gesamt: 54.5 W  [USB-C PD (Ladebetrieb) (Max 60W)]
     ├── 🔋 Akku:      +30.3 W  (0.38 C • Lädt • 45%/80% • ~0.8h bis 80%)
     └── 💻 System:     24.2 W  (Laufender Betrieb)
            ↳ CPU/iGPU: 17.2W | RTX 3060: 0.0W | Bildschirm/Mainboard: 7.0W
     ```
   * **Kein Aufwecken der NVIDIA-Grafikkarte (`D3cold`):** Liest die AMD-Ryzen-APU-Leistungsaufnahme (`PPT`) über `/sys/class/hwmon` (`amdgpu`) und prüft den Schlafzustand der NVIDIA RTX 3060 rein über `/sys/bus/pci/devices/0000:01:00.0/power/runtime_status` **ohne `nvidia-smi` aufzurufen** (wodurch die NVIDIA-GPU im `0,0 W` Tiefschlaf bleibt).

3. **Akku-Schutzmodus & Echtzeit-C-Raten-Kontrolle**
   * Zeigt die aktuelle Lade-/Entladerate als **C-Rate** (`Watt / 80 Wh`).
   * **⏸️ Laden sofort stoppen (`0.0 C` Direktbetrieb):** Setzt das Lade-Limit sofort auf den aktuellen Akkustand, sodass der Laptop zu 100 % direkt über das Netzteil läuft (`0,0 W` Akku-Belastung).
   * **🛡️ Lade-Limits:** Ein-Klick-Umschaltung zwischen **60 % (Ultra-Schutz / Schreibtisch)**, **80 % (Standard-Schutz / Alltag)** und **100 % (Reise-Modus / Vollladung)**.

4. **Integrierter GPU- & Hardware-MUX-Umschalter**
   * **🔋 Integriert (`Integrated`):** Nur AMD Radeon 680M (`0,0 W` NVIDIA).
   * **⚡ Hybrid (`Hybrid`):** AMD Radeon 680M für den Desktop + NVIDIA RTX 3060 bei Bedarf (`prime-run`), im Leerlauf im `0,0 W` Schlafmodus.
   * **🔥 Dediziert (`AsusMuxDgpu`):** Schaltet den Hardware-MUX (`gpu_mux_mode = 0`) direkt auf die NVIDIA RTX 3060.

---

## 🚀 Installation

### Voraussetzungen (Arch / EndeavourOS)
```bash
sudo pacman -S power-profiles-daemon python-pyqt6 python-dbus nvidia-prime switcheroo-control iw
yay -S supergfxctl
sudo systemctl enable --now supergfxd switcheroo-control
```

### Option A: Benutzer- & System-Helper-Installation (Empfohlen)
```bash
git clone https://github.com/Gigoslav/rog-auto-power.git
cd rog-auto-power
./install.sh
```

### Option B: Arch-Linux-Paket (`makepkg`)
```bash
git clone https://github.com/Gigoslav/rog-auto-power.git
cd rog-auto-power
makepkg -si
```

---

## 🛠️ Befehlszeile (CLI)

```bash
# Aktuelle Stromquelle, Energie-Bilanz, C-Rate & Bildschirmstatus anzeigen:
auto-power-profile.py --status

# Sprache manuell erzwingen (Deutsch oder Englisch):
auto-power-profile.py --lang de --status
auto-power-profile.py --lang en --status

# Version, Autoren-Credits & Lizenz anzeigen:
auto-power-profile.py --version

# Passendes Profil & Bildwiederholrate einmalig anwenden und beenden:
auto-power-profile.py --once
```

---

## 👤 Autor, Credits & Lizenz

* **Autor & Maintainer:** **Marcel Berghaus ([Gigoslav](https://github.com/Gigoslav))** — `<berghaus.marcel@gmail.com>`
* **Lizenz:** Veröffentlicht unter der **GNU General Public License v3.0 oder höher (`GPL-3.0-or-later`)** — siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
* **Pflicht zur Namensnennung (GPLv3 § 7b):** Alle Kopien, Pakete, Forks oder abgeleiteten Werke **müssen** den ursprünglichen Copyright-Vermerk, die Autoren-Nennung (`Marcel Berghaus / Gigoslav`) sowie den Repository-Link beibehalten.
