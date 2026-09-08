#!/bin/sh
# bin/spy-native.sh -- run the vendor's x86-64 build of spyrus_util (CMG-NAM64
# platform) directly on a 64-bit PC. No qemu; uses the NAM64 sysroot's own
# dynamic loader and libraries. Fetch them with scripts/fetch-corpus.sh.
#
# This build is spyrus_util 2.1.0 (the ARM one behind bin/spy.sh is 2.1.5).
# Its --getkey cannot parse the PEM that 2.1.5 writes into the slot; use
# bin/spy-native-getkey.sh for that. Everything else behaves the same.
#
# Runs unprivileged when the token node, /var/lock/spyrus.lck and /etc/spyrus
# are writable by you (scripts/setup-udev.sh); otherwise falls back to sudo.
# HS4L_SUDO=1 forces sudo, HS4L_SUDO=0 forbids it. -h / --help prints the
# wrapper's own environment knobs, then spyrus_util's help.
set -eu
# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=bin/hs4l-common.sh
. "$ROOT/bin/hs4l-common.sh"

SYS="${HS4L_NAM64:-$ROOT/vendor/spyrus-corpus/platinum-stable/CMG-NAM64}"
UTIL="$SYS/usr/sbin/spyrus_util"
LDSO="$SYS/lib64/ld-linux-x86-64.so.2"
HELP=0
if hs4l_wants_help "$@"; then
  HELP=1
  hs4l_help bin/spy-native.sh \
    "HS4L_NAM64      x86-64 CMG-NAM64 tree holding usr/sbin/spyrus_util (default vendor/spyrus-corpus/platinum-stable/CMG-NAM64)" \
    "HS4L_RSYNC      rsync host for scripts/fetch-corpus.sh (default rsync://rsync.guralp.com); HS4L_CORPUS its destination"
  if [ ! -e "$UTIL" ]; then
    echo "spyrus_util's own help follows once the corpus is fetched (scripts/fetch-corpus.sh)."
    exit 0
  fi
fi
for f in "$UTIL" "$LDSO" "$SYS/usr/lib64/libspyrus.so.3"; do
  if [ ! -e "$f" ]; then
    echo "hs4l: $f missing; run scripts/fetch-corpus.sh" >&2
    exit 127
  fi
done

# --help does not touch the token, so never escalate for it.
SUDO=
[ "$HELP" = 1 ] || SUDO=$(hs4l_sudo)
# shellcheck disable=SC2086  # $SUDO is empty or the single word "sudo"
exec $SUDO "$LDSO" --library-path "$SYS/lib64:$SYS/usr/lib64" "$UTIL" "$@"
