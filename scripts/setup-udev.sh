#!/usr/bin/env bash
# hs4l -- make the token usable WITHOUT sudo, persistently.
#
#  1. udev rule: the LYNKS USB node becomes group 'spyrus', mode 0660, and
#     the logged-in seat user gets an ACL (TAG+="uaccess").
#  2. 'spyrus' group created, you are added to it.
#  3. libspyrus needs to write its use-lock /var/lock/spyrus.lck and its config
#     dir /etc/spyrus (spyrus.local): both made group 'spyrus' writable, and a
#     tmpfiles.d entry recreates the lock file at boot (/var/lock is tmpfs).
#
# Safe to re-run: every step checks first and only changes what is not yet
# in place, so it doubles as a repair tool after a sudo run left root-owned
# files behind.
set -euo pipefail
# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RULE="$ROOT/udev/81-hs4l-spyrus.rules"
ME="${SUDO_USER:-${USER:-$(id -un)}}"
[ -f "$RULE" ] || { echo "hs4l: $RULE missing; run from a full checkout" >&2; exit 1; }
command -v udevadm >/dev/null 2>&1 || { echo "hs4l: udevadm not found; this script needs a udev-based Linux" >&2; exit 1; }

RELOGIN=0
getent group spyrus >/dev/null || sudo groupadd spyrus
if id -nG "$ME" | tr ' ' '\n' | grep -qx spyrus; then
  echo "hs4l: $ME already in group spyrus"
else
  sudo usermod -aG spyrus "$ME"
  RELOGIN=1
fi

if cmp -s "$RULE" /etc/udev/rules.d/81-hs4l-spyrus.rules; then
  echo "hs4l: udev rule already installed"
else
  sudo install -m 0644 "$RULE" /etc/udev/rules.d/81-hs4l-spyrus.rules
  sudo udevadm control --reload-rules
  sudo udevadm trigger --subsystem-match=usb
fi

sudo mkdir -p /etc/spyrus
sudo chgrp -R spyrus /etc/spyrus
sudo chmod 2775 /etc/spyrus
sudo find /etc/spyrus -type f -exec chmod g+rw {} +
sudo touch /var/lock/spyrus.lck
sudo chgrp spyrus /var/lock/spyrus.lck
sudo chmod 0664 /var/lock/spyrus.lck
if [ -d /etc/tmpfiles.d ]; then
  printf 'd /etc/spyrus 2775 root spyrus -\nf /run/lock/spyrus.lck 0664 root spyrus -\n' \
    | sudo tee /etc/tmpfiles.d/hs4l-spyrus.conf >/dev/null
fi

if [ "$RELOGIN" = 1 ]; then
  echo "hs4l: done. Log out/in (or 'newgrp spyrus') so group membership applies, then re-plug the token."
else
  echo "hs4l: done; nothing else to do. Re-plug the token if it was already connected."
fi
echo "hs4l: check:  ls -l /dev/bus/usb/*/*  shows group 'spyrus' on 08df:0a00;  bin/spy.sh --status  runs without sudo"
