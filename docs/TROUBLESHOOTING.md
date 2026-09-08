# Troubleshooting & gotchas

Each of these cost real time; each is traced to a root cause.

- **`--keygen` → `Execution Failure` (0x0a).** You passed `--dsaparam` from
  OpenSSL 3, whose `dsaparam 1024` / `genpkey -pkeyopt pbits:1024` emit a
  **224-bit q**. `libspyrus` only knows FIPS 186-2 (N = 160) and writes the Q
  block as `0x000000a0` + `BN_bn2bin_fixed(q, 20)`, so the card receives the
  low 160 bits of q, which no longer divide p−1, and refuses. **Fix: omit
  `--dsaparam`** (the card generates its own parameters), or generate with
  `openssl genpkey -genparam -algorithm DSA -pkeyopt pbits:1024 -pkeyopt qbits:160`
  (verified: accepted in under 2 s, key signs and verifies —
  `examples/dsaparam-1024-160.pem.accepted`, `examples/pubkey-slot2.pem`,
  `examples/sig-slot2.bin`). OpenSSL 1.0.2, which the firmware ships, always
  produced a 160-bit q, which is why the vendor's own init script could call
  plain `openssl dsaparam 1024`. The round-trip completing but W4 = `0x0a` is
  the signature of this, not a transport fault. Earlier versions of these
  docs blamed missing FIPS 186-2 seed/counter provenance; that was wrong.

- **`--pin` on keygen fails on a fresh card.** It triggers a cert/slot
  validation path that trips on an empty loose-mode card. **Omit `--pin` for
  keygen;** it auto-loads a `TEMPXXXX` placeholder cert with the new pubkey.

- **"Zero length certificate".** You used standard/`--use` mode, which wants a
  cert in every slot. Use `--init --loose` for the from-scratch path.

- **`--init` seems to ignore piped `yes`.** The confirmation is read from
  `/dev/tty`, not stdin. Answer interactively, or run fully non-interactively.

- **OpenSSL 3 says `do_sigver_init: invalid digest` when verifying.** That is
  a **deprecation policy** blocking SHA-1+DSA, not a signature failure — it
  errors before doing any math, on good and bad input alike. Use a
  legacy-tolerant verifier (`scripts/verify.py`, pyca/cryptography).

- **`errno 22` on a status read.** Benign quirk of qemu's ioctl translation;
  the payload still comes back.

- **`Opening device 0 failed. Unix error 13 (Permission denied)`.** Usually
  not the USB node: run with `-D -D` and you see `Failed to create lock file` —
  `/var/lock/spyrus.lck` or `/etc/spyrus/` is root-owned from an earlier sudo
  run. `scripts/setup-udev.sh` fixes both (plus the udev rule and the `spyrus`
  group), or let the wrapper fall back to sudo (`HS4L_SUDO=1` forces it).
  libusb itself needs **read+write** on the node; the rule (`uaccess` tag +
  group) grants that across re-plugs, so no per-boot chmod.

- **Native build: `--getkey` prints nothing, exit 1.** With `-D`:
  `spyrus_get_key: Unable to unpack PEM` / `Failed to find public key`. The
  x86-64 `spyrus_util` is 2.1.0 and cannot parse the CRLF PEM that the 2.1.5
  ARM build stores in the slot. Use `bin/spy-native-getkey.sh N > pub.pem`,
  which rebuilds it from `--get --index N`.

- **`spyrus_util` under qemu cannot load `libiso8601.so.1` / `libz.so.1`.**
  Sysroot from an older `fetch-vendor.sh`, which missed the two libraries
  living in `lib/` (not `usr/lib`). Re-run `scripts/fetch-vendor.sh`;
  `CHECKSUMS.sha256` now covers all 20 files.

- **`verify.py` refuses the key.** It only accepts DSA public keys and says
  so; a missing file exits 2.

- **`qemu-arm-static: not found`.** Install the `qemu-user-static` package.

- **Vendor binary not found.** Run `scripts/fetch-vendor.sh` first.
