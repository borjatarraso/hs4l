# Changelog

All notable changes to hs4l are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are git
tags `vX.Y`.

## [0.1] - 2026-09-08

Initial public release.

### Added
- `bin/spy.sh`: run the vendor's ARM `spyrus_util` under `qemu-arm-static`
  against a SPYRUS LYNKS Series II on USB (`08df:0a00`).
- `bin/spy-native.sh`: run the vendor's x86-64 build directly, no qemu.
- `scripts/fetch-vendor.sh`: fetch the ARM runtime from the public firmware
  mirror and verify it against `CHECKSUMS.sha256`.
- `scripts/fetch-corpus.sh`: mirror every SPYRUS-related file for all seven
  firmware platforms, including the x86-64 library closure.
- `scripts/setup-udev.sh` and `udev/81-hs4l-spyrus.rules`: group access to
  the token.
- `scripts/verify.py`: off-card DSA-1024 / SHA-1 signature verification with
  pyca/cryptography (OpenSSL 3 refuses the pairing by policy).
- `third_party/spyrus-gpl/`: the GPL-licensed C headers (public API, 2008
  wire-protocol header with every opcode) and provisioning scripts of the
  vendor's spyrus-utils package, unmodified, with per-file provenance.
- Docs: protocol notes, reinitialise-from-scratch walkthrough,
  troubleshooting, four SVG diagrams, and real example key / message /
  signature.
- `VENDOR-NOTICE.md`: what is deliberately not redistributed and why.
