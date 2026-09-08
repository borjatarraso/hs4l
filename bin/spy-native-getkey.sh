#!/bin/sh
# bin/spy-native-getkey.sh -- public key of a slot via the native x86-64 build.
#
# spyrus_util 2.1.0 (the CMG-NAM64 build behind bin/spy-native.sh) fails
# "--getkey" with "Unable to unpack PEM" on keys written by the 2.1.5 ARM
# build: the slot holds a CRLF-terminated PUBLIC KEY PEM it does not accept.
# "--get" still dumps the raw slot as a hexdump, so rebuild the PEM from that.
#
#     bin/spy-native-getkey.sh [index] > pub.pem        (index defaults to 1)
set -eu
# shellcheck disable=SC1007  # CDPATH= is intentional: keep cd silent
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IDX=${1:-1}
case "$IDX" in
  -h|--help) echo "usage: bin/spy-native-getkey.sh [index] > pub.pem   (index defaults to 1)"; exit 0 ;;
  ''|*[!0-9]*) echo "hs4l: index must be a number, got '$IDX'" >&2; exit 2 ;;
esac
# Capture first so a failing spy-native.sh (no token, no corpus, wrong slot)
# stops here with its own message, instead of the parser blaming the slot.
DUMP=$("$HERE/spy-native.sh" --get --index "$IDX")
printf '%s\n' "$DUMP" | python3 -c '
import re, sys
out = bytearray()
for line in sys.stdin:
    m = re.match(r"^[0-9a-fA-F]+:  (.{0,49})", line)   # 16 bytes = 49 hex columns
    if not m:
        continue
    out += bytes.fromhex(re.sub(r"[^0-9a-fA-F]", "", m.group(1)))
pem = out.replace(b"\r", b"").rstrip(b"\0")
if b"-----BEGIN" not in pem:
    sys.stderr.write("hs4l: slot does not hold a PEM (empty slot? try --list to see which slots are used)\n")
    sys.exit(1)
sys.stdout.buffer.write(pem)
'
