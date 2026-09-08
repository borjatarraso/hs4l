#!/bin/sh
# hs4l -- spyrus_util wrapper
#
# Runs the the vendor ARM build of spyrus_util under qemu-user against a
# SPYRUS LYNKS Series II token (USB 08df:0a00) on any Linux host.
#
# The vendor binaries are NOT shipped in this repo (see VENDOR-NOTICE.md).
# Run  scripts/fetch-vendor.sh  once to populate  vendor/sysroot/  from the
# public Platinum firmware mirror, then use this wrapper exactly like the
# real spyrus_util:
#
#     bin/spy.sh --state
#     bin/spy.sh --init --loose --sso-pin 1234 --user-pin 1234
#     bin/spy.sh --keygen --index 1
#     bin/spy.sh --getkey --index 1 > pub.pem
#     bin/spy.sh --sign msg --index 1 --binary > sig.bin
#
# Requires: qemu-arm-static (qemu-user-static) and read+write on the USB node
# (see scripts/setup-udev.sh, or: sudo chmod 666 /dev/bus/usb/BBB/DDD).

set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/.." && pwd)

# override with:  HS4L_SYSROOT=/some/rootfs bin/spy.sh ...
SYS=${HS4L_SYSROOT:-"$ROOT/vendor/sysroot"}
UTIL="$SYS/usr/sbin/spyrus_util"

if [ ! -x "$UTIL" ]; then
  echo "hs4l: vendor binary not found at $UTIL" >&2
  echo "hs4l: run  scripts/fetch-vendor.sh  first (see VENDOR-NOTICE.md)." >&2
  exit 127
fi
if ! command -v qemu-arm-static >/dev/null 2>&1; then
  echo "hs4l: qemu-arm-static not found. Install the qemu-user-static package." >&2
  exit 127
fi

exec sudo env \
  QEMU_LD_PREFIX="$SYS" \
  LD_LIBRARY_PATH="$SYS/lib:$SYS/usr/lib" \
  qemu-arm-static "$UTIL" "$@"
