#!/bin/sh
# bin/spy-native.sh -- run Guralp's x86-64 build of spyrus_util (CMG-NAM64
# platform) directly on a 64-bit PC. No qemu; uses the NAM64 sysroot's own
# dynamic loader and libraries. Fetch them with scripts/fetch-corpus.sh.
#
# Needs: RW on the token's /dev/bus/usb node (udev/ rules or chmod 666), and
# write access to /var/lock/spyrus.lck and /etc/spyrus/ (libspyrus keeps its
# use-lock and config there; run once as root or grant an ACL to your user).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SYS="${HS4L_NAM64:-$ROOT/vendor/guralp-spyrus-corpus/platinum-stable/CMG-NAM64}"
[ -x "$SYS/usr/sbin/spyrus_util" ] || { echo "hs4l: $SYS/usr/sbin/spyrus_util missing; run scripts/fetch-corpus.sh" >&2; exit 1; }
exec "$SYS/lib64/ld-linux-x86-64.so.2" --library-path "$SYS/lib64:$SYS/usr/lib64" \
     "$SYS/usr/sbin/spyrus_util" "$@"
