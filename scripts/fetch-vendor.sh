#!/usr/bin/env bash
# hs4l -- fetch the vendor ARM runtime from the PUBLIC Platinum firmware mirror.
#
# This repo deliberately does NOT redistribute SPYRUS / vendor proprietary
# binaries (see VENDOR-NOTICE.md). Instead it pulls them, at your request,
# from the same public rsync mirror the vendor publishes the firmware on, and
# verifies them against CHECKSUMS.sha256 so you know you got the exact build
# these instructions were written for.
#
#   scripts/fetch-vendor.sh            # fetch, then verify
#   scripts/fetch-vendor.sh --verify   # verify an existing vendor/sysroot only
set -euo pipefail

# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="${HS4L_SYSROOT:-$ROOT/vendor/sysroot}"   # same override bin/spy.sh honours
SUMS="$ROOT/CHECKSUMS.sha256"
MIRROR="${HS4L_MIRROR:-rsync://rsync.guralp.com/platinum-stable/CMG-DCM-mk4-eabi}"

verify() {
  [ -f "$SUMS" ] || { echo "hs4l: $SUMS missing"; return 1; }
  local ok=0 miss=0 bad=0 sum rel path got
  while read -r sum rel; do
    case "$sum" in ''|\#*) continue ;; esac
    path="$DEST/$rel"
    if [ ! -f "$path" ]; then
      echo "  MISSING  $rel"; miss=$((miss+1)); continue
    fi
    got=$(sha256sum "$path" | awk '{print $1}')
    if [ "$got" = "$sum" ]; then
      echo "  OK       $rel"; ok=$((ok+1))
    else
      echo "  MISMATCH $rel"; bad=$((bad+1))
    fi
  done < "$SUMS"
  echo
  echo "hs4l: verify -- $ok ok, $miss missing, $bad mismatched"
  [ "$bad" -eq 0 ] && [ "$miss" -eq 0 ]
}

if [ "${1:-}" = "--verify" ]; then
  verify; exit $?
fi

echo "hs4l: fetching Platinum ARM rootfs (release >= 15781)"
echo "hs4l:   from   $MIRROR"
echo "hs4l:   into   $DEST"
echo
command -v rsync >/dev/null 2>&1 || { echo "hs4l: rsync required." >&2; exit 127; }
mkdir -p "$DEST"

# Only the paths spyrus_util actually needs (readelf -d on it, libspyrus,
# libioline-*, libusb-1.0, libssl/libcrypto): note libz and libiso8601 live in
# lib/, not usr/lib/, on this rootfs. Pulling the whole rootfs also works; this
# keeps it small. Add --include lines if a NEEDED library turns out to be
# missing on your release.
rsync -av --prune-empty-dirs \
  --include='usr/' --include='usr/sbin/' \
  --include='usr/sbin/spyrus_util' --include='usr/sbin/spyrus_test' \
  --include='usr/sbin/cd11-spyrus-tool.sh' \
  --include='usr/lib/' \
  --include='usr/lib/libspyrus.so.*' --include='usr/lib/libgslutil.so.*' \
  --include='usr/lib/libiso8601.so.*' --include='usr/lib/libioline-*.so.*' \
  --include='usr/lib/libusb-1.0.so.*' --include='usr/lib/libusb-0.1.so*' \
  --include='usr/lib/libssl.so.1.0.0' --include='usr/lib/libcrypto.so.1.0.0' \
  --include='lib/' --include='lib/ld-linux.so.3' --include='lib/ld-*.so' \
  --include='lib/libc.so.6' --include='lib/libc-*.so' \
  --include='lib/libdl.so.2' --include='lib/libdl-*.so' \
  --include='lib/libm.so.6' --include='lib/libm-*.so' \
  --include='lib/libpthread.so.0' --include='lib/libpthread-*.so' \
  --include='lib/librt.so.1' --include='lib/librt-*.so' \
  --include='lib/libgcc_s.so.1' \
  --include='lib/libz.so.1' --include='lib/libz.so.1.*' \
  --include='lib/libiso8601.so.*' \
  --include='lib/libncursesw.so.5*' --include='lib/libreadline.so.*' \
  --include='lib/libhistory.so.*' --include='lib/libtinfo.so.*' \
  --exclude='*' \
  "$MIRROR/" "$DEST/" || {
    echo
    echo "hs4l: rsync failed -- the mirror path or release layout may have moved."
    echo "hs4l: browse $MIRROR, copy usr/sbin/spyrus_util plus every NEEDED lib"
    echo "hs4l: (run 'readelf -d spyrus_util') into vendor/sysroot/, then:"
    echo "hs4l:   scripts/fetch-vendor.sh --verify"
    exit 1
  }

echo
echo "hs4l: fetched. Verifying against CHECKSUMS.sha256 ..."
verify
