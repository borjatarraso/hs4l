#!/bin/sh
# scripts/fetch-corpus.sh -- mirror every SPYRUS-related file the firmware vendor publishes
# on its open rsync server, for ALL Platinum platforms and modules, into
# vendor/spyrus-corpus/<module>/<platform>/... (git-ignored).
#
# What you get (per platform, where present):
#   usr/sbin/spyrus_util, spyrus_test, cd11-spyrus-tool.sh   CLI tools
#   usr/lib*/libspyrus.so.*                                   token library
#   include/spyrus.h, spyrus_dss.h, spyrus_int.h              C API + wire protocol (GPL-2)
#   lib*/modules/*/drivers/char/pcmcia/spyrus_cs.ko           PCMCIA/CardBus kernel driver (GPL)
#   etc/udev/rules.d/81-spyrus.rules, etc/init.d/spyrus       host integration
#   usr/lib/upgrade/0140-EAM-hw-config-usb-spyrus.sh          first-boot config (GPL-3)
#   srv/http/cgi-bin.auth/spyrus.cgi, webconfig/menu/spyrus   web UI
# plus, for CMG-NAM64 (x86-64), the shared-library closure needed to run
# spyrus_util natively on a 64-bit PC without qemu (see bin/spy-native.sh).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="$ROOT/vendor/spyrus-corpus"
HOST="${HS4L_RSYNC:-rsync://rsync.guralp.com}"
command -v rsync >/dev/null 2>&1 || { echo "hs4l: rsync required." >&2; exit 127; }
mkdir -p "$DEST"
for m in platinum-stable platinum-prerelease platinum-crosslib ctbto-prerelease; do
  echo "hs4l: listing $m ..."
  rsync -r "$HOST/$m/" | grep -v '^d' | awk '{print $NF}' \
    | grep -iE 'spyrus|fortezza|lynks' > "$DEST/.files-$m" || true
  if [ "$m" = platinum-crosslib ]; then printf 'README\nfix-paths.sh\nrsync-pull.sh\n' >> "$DEST/.files-$m"; fi
  if [ "$m" = platinum-stable ]; then
    rsync -r "$HOST/$m/CMG-NAM64/" | grep -v '^d' | awk '{print $NF}' \
      | grep -E '^(usr/)?lib64/(ld-|libc[.-]|libm[.-]|libdl|librt|libpthread|libgcc_s|libz\.so|libssl\.so\.1\.0\.0|libcrypto\.so\.1\.0\.0|libusb-1\.0|libgslutil|libiso8601|libioline-(consumer|pcd)|libspyrus|libcurl|libidn|libssh|libgssapi|libkrb|libk5|libcom_err|libldap|liblber|libsasl)' \
      | sed 's#^#CMG-NAM64/#' >> "$DEST/.files-$m"
  fi
  mkdir -p "$DEST/$m"
  rsync -a --files-from="$DEST/.files-$m" "$HOST/$m/" "$DEST/$m/"
  echo "hs4l:   $(wc -l < "$DEST/.files-$m") files"
done
if [ -f "$DEST/CHECKSUMS.sha256" ]; then
  echo "hs4l: verifying against vendor/spyrus-corpus/CHECKSUMS.sha256"
  (cd "$DEST" && sha256sum --quiet -c CHECKSUMS.sha256) && echo "hs4l: corpus OK"
fi
