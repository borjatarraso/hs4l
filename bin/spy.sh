#!/bin/sh
# hs4l -- spyrus_util wrapper
#
# Runs the vendor ARM build of spyrus_util under qemu-user against a
# SPYRUS LYNKS Series II token (USB 08df:0a00) on any Linux host.
#
# The vendor binaries are NOT shipped in this repo (see VENDOR-NOTICE.md).
# Run  scripts/fetch-vendor.sh  once to populate  vendor/sysroot/  from the
# public Platinum firmware mirror, then use this wrapper exactly like the
# real spyrus_util:
#
#     bin/spy.sh --status
#     bin/spy.sh --init --loose --sso-pin 1234 --user-pin 1234
#     bin/spy.sh --keygen --index 1
#     bin/spy.sh --getkey --index 1 > pub.pem
#     bin/spy.sh --sign msg --index 1 --binary > sig.bin
#
# Requires: qemu-arm-static (qemu-user-static). Runs unprivileged when the
# token node, /var/lock/spyrus.lck and /etc/spyrus are writable by you
# (scripts/setup-udev.sh sets that up); otherwise falls back to sudo.
# HS4L_SUDO=1 forces sudo, HS4L_SUDO=0 forbids it. -h / --help prints the
# wrapper's own environment knobs, then spyrus_util's help.

set -eu

# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=bin/hs4l-common.sh
. "$ROOT/bin/hs4l-common.sh"

# override with:  HS4L_SYSROOT=/some/rootfs bin/spy.sh ...
SYS=${HS4L_SYSROOT:-"$ROOT/vendor/sysroot"}
UTIL="$SYS/usr/sbin/spyrus_util"

HELP=0
if hs4l_wants_help "$@"; then
  HELP=1
  hs4l_help bin/spy.sh \
    "HS4L_SYSROOT    ARM rootfs holding usr/sbin/spyrus_util (default vendor/sysroot)" \
    "HS4L_MIRROR     rsync source for scripts/fetch-vendor.sh (default rsync://rsync.guralp.com/platinum-stable/CMG-DCM-mk4-eabi)"
  if [ ! -x "$UTIL" ]; then
    echo "spyrus_util's own help follows once the vendor runtime is fetched (scripts/fetch-vendor.sh)."
    exit 0
  fi
fi

if [ ! -x "$UTIL" ]; then
  echo "hs4l: vendor binary not found at $UTIL" >&2
  echo "hs4l: run  scripts/fetch-vendor.sh  first (see VENDOR-NOTICE.md)." >&2
  exit 127
fi
for lib in lib/ld-linux.so.3 lib/libz.so.1 lib/libiso8601.so.1 usr/lib/libspyrus.so.3; do
  if [ ! -e "$SYS/$lib" ]; then
    echo "hs4l: $SYS/$lib missing (incomplete sysroot); re-run scripts/fetch-vendor.sh" >&2
    exit 127
  fi
done
if ! command -v qemu-arm-static >/dev/null 2>&1; then
  echo "hs4l: qemu-arm-static not found. Install the qemu-user-static package." >&2
  exit 127
fi

# --help does not touch the token, so never escalate for it.
SUDO=
[ "$HELP" = 1 ] || SUDO=$(hs4l_sudo)
# shellcheck disable=SC2086  # $SUDO is empty or the single word "sudo"
exec $SUDO env \
  QEMU_LD_PREFIX="$SYS" \
  LD_LIBRARY_PATH="$SYS/lib:$SYS/usr/lib" \
  qemu-arm-static "$UTIL" "$@"
