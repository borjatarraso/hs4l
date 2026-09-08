# Changelog

All notable changes to hs4l are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are git
tags `vX.Y`.

## [Unreleased]

### Changed
- `scripts/verify.py` no longer needs pyca/cryptography: it parses the
  PEM/DER SubjectPublicKeyInfo and the DSS signature with a minimal DER
  reader and does the FIPS 186-4 verification arithmetic itself, standard
  library only (Python 3.9+). Same verdicts, same exit codes (0 valid,
  1 invalid, 2 usage or malformed input), every parse failure now says what
  was wrong instead of tracing back.
- `make check` builds on `make test` and no longer hides a failed
  `fetch-vendor.sh --verify` behind a pipe into `tail`.

### Added
- `scripts/verify.py`: DER `SEQUENCE { r, s }` and raw `r || s` signatures,
  auto-detected (`--format der|raw` forces one); DER as well as PEM public
  keys; argparse `--help`; `--self-test` against the known-answer vector the
  card produced for `examples/`; `-q` for exit status only.
- `tests/test_verify.py` (unittest, standard library only) and `make test`:
  shellcheck when installed, the verifier self-test and the unit tests.
- `bin/spy.sh --help` / `-h` (and `bin/spy-native.sh`) print the wrapper's
  own environment variables, then `spyrus_util`'s usage; the wrapper help
  works before the vendor runtime is fetched and never escalates to sudo.
- `scripts/fetch-vendor.sh --verify -q` lists only what is missing or
  differs; the summary names the directory and says what to do about
  missing or mismatched files; unknown options exit 2; `--help`.
- `bin/spy-native-getkey.sh -h`; a non-numeric index is rejected up front.

### Fixed
- `scripts/setup-udev.sh` is idempotent: no `usermod` when the user is
  already in `spyrus`, no rule reinstall or udev reload when the installed
  rule is identical, re-login advice only when membership changed; a failed
  `udevadm control --reload-rules` no longer silently skips the trigger.
- `bin/spy-native-getkey.sh` reports `spy-native.sh`'s own failure (no
  corpus, no token, wrong slot) instead of "slot does not hold a PEM": the
  hexdump is captured before parsing, since POSIX `sh` has no `pipefail`.
- `scripts/fetch-corpus.sh` names the module whose download failed instead
  of exiting silently.
- Error hints from the fetchers go to stderr; typo in `bin/spy.sh` header.

## [0.8] - 2026-09-08

### Fixed
- Root cause of `0x0a` on `--keygen --dsaparam` corrected. It is not
  missing FIPS 186-2 seed/counter provenance: OpenSSL 3 emits a 224-bit q for
  1024-bit DSA parameters, `libspyrus` writes the Q block as a fixed 160 bits
  (`BN_bn2bin_fixed(q, 20)`), and the truncated q fails the card's parameter
  check. Parameters generated with `-pkeyopt qbits:160` are accepted.
  README, PROTOCOL.md, TROUBLESHOOTING.md and REINITIALIZE.md updated.

### Added
- `examples/dsaparam-1024-160.pem.accepted`, `examples/pubkey-slot2.pem`,
  `examples/sig-slot2.bin`: host-generated 1024/160 parameters the card
  accepted, and the key and signature it produced from them.
- PROTOCOL.md: full header word layout (offset, length, result) and the Sign
  payload format (SHA-1 in, r and s in 40-byte fields out).

## [0.7] - 2026-09-08

### Added
- `docs/diagrams/architecture.svg`: the whole path from wrapper to token,
  including host state, install-time fetch and off-card verification.
- `docs/diagrams/workflow.svg`: the seven steps from a bare token to a
  verified signature. Both are embedded in the README.
- `Makefile` with `fetch`, `corpus`, `setup`, `status`, `state`, `list`,
  `verify` and `check` (shellcheck + example verification + checksums).
- GitHub issue template for device reports.

## [0.6] - 2026-09-08

### Added
- README "Supported devices" table: the verified LYNKS Series II USB token,
  other Series II USB units, the PCMCIA card path through `spyrus_cs.ko`
  (untested), and the SPYRUS products hs4l does not cover.

### Changed
- README, VENDOR-NOTICE.md, docs/REINITIALIZE.md and docs/TROUBLESHOOTING.md
  now match the code: unprivileged wrappers, the fetch fix, the ARM 2.1.5 vs
  x86-64 2.1.0 caveat, and the in-repo corpus checksums.

## [0.5] - 2026-09-08

### Added
- `CHECKSUMS.corpus.sha256`: SHA-256 of all 158 files the corpus fetch
  pulls (x86-64 and i386 builds, three ARM builds, GPL headers, scripts).
- `docs/CORPUS-INDEX.md`: what each file in the corpus is and where it
  comes from.
- `HS4L_CORPUS` override for the corpus location.

### Changed
- `scripts/fetch-corpus.sh` verifies every file against the in-repo
  checksums and exits non-zero on a mismatch; rsync listing failures are
  reported instead of silently producing an empty tree.

## [0.4] - 2026-09-08

### Added
- `bin/spy-native-getkey.sh`: exports a slot's public key with the x86-64
  build. Its `spyrus_util` is 2.1.0 and its `--getkey` fails with
  "Unable to unpack PEM" on the CRLF PEM that the ARM 2.1.5 build stores;
  the script rebuilds the PEM from the `--get` hexdump instead.

### Fixed
- `scripts/verify.py` rejects non-DSA keys with a clear message and exits 2
  on unreadable input instead of raising a traceback.

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
