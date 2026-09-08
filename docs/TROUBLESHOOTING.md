# Troubleshooting & gotchas

Each of these cost real time; each is traced to a root cause.

- **`--keygen` → `Execution Failure` (0x0a).** You passed `--dsaparam` from
  modern OpenSSL. The card validates DSA parameters FIPS-186-2-style (seed +
  counter provenance) and OpenSSL 3 emits none. **Fix: omit `--dsaparam`** and
  let the card self-generate. The round-trip completing but W4 = `0x0a` is the
  signature of this, not a transport fault.

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

- **Permission denied opening the device.** libusb needs **read+write** on the
  USB node. Re-apply the chmod / re-plug after every re-enumeration, or install
  the udev rule (`scripts/setup-udev.sh`).

- **`qemu-arm-static: not found`.** Install the `qemu-user-static` package.

- **Vendor binary not found.** Run `scripts/fetch-vendor.sh` first.
