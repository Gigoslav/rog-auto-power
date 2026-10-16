#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Berghaus (Gigoslav) <berghaus.marcel@gmail.com>
# Project: https://github.com/Gigoslav/rog-auto-power

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Installing ROG Auto-Power & Live Watt Indicator (v0.1.1) ==="

mkdir -p ~/.local/bin ~/.config/systemd/user ~/.local/share/applications
ln -sf "$REPO_DIR/auto-power-profile.py" ~/.local/bin/auto-power-profile.py
cp "$REPO_DIR/auto-power-profile.service" ~/.config/systemd/user/auto-power-profile.service
cp "$REPO_DIR/rog-auto-power.desktop" ~/.local/share/applications/rog-auto-power.desktop

if command -v kwriteconfig6 >/dev/null 2>&1; then
    kwriteconfig6 --file powerdevilrc --group AC --group PowerProfile --key profile performance
    kwriteconfig6 --file powerdevilrc --group Battery --group PowerProfile --key profile power-saver
fi

echo "=== Installing selective root GPU/Power helper (/usr/local/bin/rog-gpu-mux-helper) ==="
sudo install -Dm755 "$REPO_DIR/rog-gpu-mux-helper" /usr/local/bin/rog-gpu-mux-helper

SUDOERS_FILE="/etc/sudoers.d/$USER-rog-mux"
echo "$USER ALL=(root) NOPASSWD: /usr/local/bin/rog-gpu-mux-helper" | sudo tee "$SUDOERS_FILE" >/dev/null
sudo chmod 440 "$SUDOERS_FILE"
sudo visudo -cf "$SUDOERS_FILE"

systemctl --user daemon-reload
systemctl --user enable --now auto-power-profile.service
systemctl --user restart auto-power-profile.service

echo "=== Installation complete! ==="
~/.local/bin/auto-power-profile.py --version
~/.local/bin/auto-power-profile.py --status
