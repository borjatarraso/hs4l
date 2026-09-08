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
#
# Every file is checked against CHECKSUMS.corpus.sha256 (in the repo); see
# docs/CORPUS-INDEX.md for what each file is.  HS4L_RSYNC overrides the host.
set -eu
# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="${HS4L_CORPUS:-$ROOT/vendor/spyrus-corpus}"
SUMS="$ROOT/CHECKSUMS.corpus.sha256"
HOST="${HS4L_RSYNC:-rsync://rsync.guralp.com}"
NAM64_LIBS='^(usr/)?lib64/(ld-|libc[.-]|libm[.-]|libdl|librt|libpthread|libgcc_s|libz\.so|libssl\.so\.1\.0\.0|libcrypto\.so\.1\.0\.0|libusb-1\.0|libgslutil|libiso8601|libioline-(consumer|pcd)|libspyrus|libcurl|libidn|libssh|libgssapi|libkrb|libk5|libcom_err|libldap|liblber|libsasl)'

command -v rsync >/dev/null 2>&1 || { echo "hs4l: rsync required." >&2; exit 127; }
mkdir -p "$DEST"

# rsync's listing is "perms size date time name"; take the name (field 5 on)
# and skip directories.
names() { awk '!/^d/ { $1=$2=$3=$4=""; sub(/^ +/, ""); print }'; }

for m in platinum-stable platinum-prerelease platinum-crosslib ctbto-prerelease; do
  echo "hs4l: listing $m ..."
  LIST="$DEST/.files-$m"
  rsync -r "$HOST/$m/" > "$LIST.raw" || { echo "hs4l: cannot list $HOST/$m" >&2; exit 1; }
  names < "$LIST.raw" | grep -iE 'spyrus|fortezza|lynks' > "$LIST" || true
  case "$m" in
    platinum-crosslib) printf 'README\nfix-paths.sh\nrsync-pull.sh\n' >> "$LIST" ;;
    platinum-stable)
      rsync -r "$HOST/$m/CMG-NAM64/" > "$LIST.nam64" || { echo "hs4l: cannot list CMG-NAM64" >&2; exit 1; }
      names < "$LIST.nam64" | grep -E "$NAM64_LIBS" | sed 's#^#CMG-NAM64/#' >> "$LIST"
      rm -f "$LIST.nam64" ;;
  esac
  rm -f "$LIST.raw"
  mkdir -p "$DEST/$m"
  rsync -a --files-from="$LIST" "$HOST/$m/" "$DEST/$m/"
  echo "hs4l:   $(wc -l < "$LIST") files"
done

if [ -f "$SUMS" ]; then
  echo "hs4l: verifying against CHECKSUMS.corpus.sha256 ..."
  if (cd "$DEST" && sha256sum --quiet -c "$SUMS"); then
    echo "hs4l: corpus OK"
  else
    echo "hs4l: some files differ from the build these notes were written against (mirror updated?); they may still work" >&2
    exit 1
  fi
fi
