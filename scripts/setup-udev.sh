#!/usr/bin/env bash
# hs4l -- install a udev rule so the token is group-accessible (no per-boot chmod).
# Creates a 'spyrus' group, adds you to it, installs udev/81-hs4l-spyrus.rules.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RULE="$ROOT/udev/81-hs4l-spyrus.rules"
getent group spyrus >/dev/null || sudo groupadd spyrus
sudo usermod -aG spyrus "${SUDO_USER:-$USER}"
sudo install -m 0644 "$RULE" /etc/udev/rules.d/81-hs4l-spyrus.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
echo "hs4l: udev rule installed. Log out/in (or re-plug the token) for group membership."
echo "hs4l: quick check -- ls -l /dev/bus/usb/*/*  should show group 'spyrus' on 08df:0a00"
