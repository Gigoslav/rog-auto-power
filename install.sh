#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Installing ROG Auto-Power & Live Watt Indicator ==="

mkdir -p ~/.local/bin ~/.config/systemd/user
ln -sf "$REPO_DIR/auto-power-profile.py" ~/.local/bin/auto-power-profile.py
cp "$REPO_DIR/auto-power-profile.service" ~/.config/systemd/user/auto-power-profile.service

if command -v kwriteconfig6 >/dev/null 2>&1; then
    kwriteconfig6 --file powerdevilrc --group AC --group PowerProfile --key profile performance
    kwriteconfig6 --file powerdevilrc --group Battery --group PowerProfile --key profile power-saver
fi

echo "=== Installing selective root GPU MUX helper (/usr/local/bin/rog-gpu-mux-helper) ==="
sudo cp "$REPO_DIR/rog-gpu-mux-helper" /usr/local/bin/rog-gpu-mux-helper
sudo chown root:root /usr/local/bin/rog-gpu-mux-helper
sudo chmod 755 /usr/local/bin/rog-gpu-mux-helper

SUDOERS_FILE="/etc/sudoers.d/$USER-rog-mux"
echo "$USER ALL=(root) NOPASSWD: /usr/local/bin/rog-gpu-mux-helper" | sudo tee "$SUDOERS_FILE" >/dev/null
sudo chmod 440 "$SUDOERS_FILE"
sudo visudo -cf "$SUDOERS_FILE"

systemctl --user daemon-reload
systemctl --user enable --now auto-power-profile.service
systemctl --user restart auto-power-profile.service

echo "=== Installation complete! ==="
~/.local/bin/auto-power-profile.py --status
