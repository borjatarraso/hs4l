# Changelog

All notable changes to hs4l are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are git
tags `vX.Y`.

## [0.3] - 2026-09-08

### Added
- `bin/hs4l-common.sh`: finds the token's `/dev/bus/usb` node from sysfs and
  decides whether sudo is needed (`HS4L_SUDO=0/1` overrides).
- `scripts/setup-udev.sh`: `spyrus` group, udev rule with `TAG+="uaccess"`,
  group-writable `/etc/spyrus` (2775) and `/var/lock/spyrus.lck`, and a
  `tmpfiles.d` entry so the lock survives a reboot (`/var/lock` is a tmpfs).

### Changed
- `bin/spy.sh` and `bin/spy-native.sh` run unprivileged once the setup
  script has been run; sudo is used only when the node, lock or config are
  not writable, with a hint pointing at the setup script.

### Fixed
- An earlier sudo run left `/var/lock/spyrus.lck` and `/etc/spyrus` owned
  by root, which broke every later unprivileged run with "Permission denied".

## [0.2] - 2026-09-08

### Fixed
- `scripts/fetch-vendor.sh` did not fetch `lib/libz.so.1` and
  `lib/libiso8601.so.1`, both `NEEDED` by `spyrus_util`/`libspyrus` and
  living in `lib/` rather than `usr/lib/`; a fresh sysroot could not start.
- `CHECKSUMS.sha256` now covers all 20 runtime files.

### Added
- `HS4L_SYSROOT` override for the sysroot location.

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
