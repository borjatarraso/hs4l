# Vendor notice & licensing

**hs4l does not redistribute any SPYRUS or firmware-vendor proprietary
software.** This is a deliberate choice, for your protection and theirs.

## What is *not* in this repository

The tool that actually speaks the SPYCOS protocol is the vendor's own ARM
binary and library:

| file | role | ~size |
|------|------|-------|
| `usr/sbin/spyrus_util` | the CLI that inits / keygens / signs (2.1.5) | 36 KB |
| `usr/lib/libspyrus.so.3(.1)` | the SPYCOS protocol engine | 243 KB |
| `usr/sbin/spyrus_test`, `cd11-spyrus-tool.sh` | vendor helpers | — |
| `usr/lib/libgslutil`, `libioline-*`, `lib/libiso8601` | vendor support libs | — |
| `usr/lib/libusb-1.0`, `libusb-0.1`, `libssl/ libcrypto 1.0.0`, `lib/libz`, `/lib/*` glibc | runtime | — |

These originate in a **seismic-instrument vendor's "Platinum" digitiser firmware** and
embed **SPYRUS, Inc.** intellectual property. SPYRUS was acquired by
**Route1 Inc.** (2021-09-15); the firmware vendor publishes it on a public
mirror. None of it is licensed for redistribution by this project, so it is
kept out of git.

## How you get it anyway

`scripts/fetch-vendor.sh` downloads exactly those files from the vendor's own
**public** rsync mirror into `vendor/sysroot/`, then verifies them against
[`CHECKSUMS.sha256`](CHECKSUMS.sha256) (20 files; SHA-256 of the June-2024 Platinum
"stable" build these docs were written against). You are pulling the vendor's
own published bytes, not a re-hosted copy.

```sh
scripts/fetch-vendor.sh
```

If the mirror layout has moved, the script prints how to place the files by
hand; any Platinum ARM rootfs (release ≥ 15781) will do.

## Legality of what this toolkit *does*

Everything here operates a device **you physically own and are entitled to
use**. The reinitialise-from-scratch path (`--init`) is a **documented**
SPYCOS function; hs4l extracts no key material and bypasses no
authentication.

## If you have the right to bundle the blobs

If you have confirmed you may redistribute the vendor files (e.g. a licence,
or they are already GPL/LGPL where applicable), drop them into
`vendor/sysroot/` and delete the matching line from `.gitignore`. That is
your call to make, not this project's default.

## Source-form GPL files (in the repo)

Only files carrying their own GPL notice are committed, under
`third_party/spyrus-gpl/`, with licence texts and provenance. Everything
binary, and every file without a licence notice, remains fetch-at-install
via `scripts/fetch-vendor.sh` / `scripts/fetch-corpus.sh` (the corpus is
verified against `CHECKSUMS.corpus.sha256`).

## Identification checksums for the Windows middleware (not redistributed, not required)

For provenance: the final Windows middleware release, **En-Sign 8.0.0.9**
(SPYRUS, 2005-2010), was located on original optical media and analysed
statically for the documentation in `docs/SPEX2.md` and `docs/HARDWARE.md`.
Its files are **not** in this repository and are not needed to run hs4l.
The SHA-256 values below exist so anyone who finds a copy can verify what
they have:

| artifact | SHA-256 |
|---|---|
| `ensign-8.0.0.9.iso` (disc image, 45,613,056 B) | `72f53123aab4fb772945d69a36f96f7a8d3bc6e7b471ffcde04baf1346cc9d46` |
| `En-Sign.msi` | `ca0df58757e4f0a79c7db4ab4c10f57a847c39d699bde59ae323fefc7df33580` |
| `SpyPK11.dll` (PKCS#11 v2.x module) | `b6f370a61164ba2a03037bb863f3651ec45420af7ff9cd1dddae422b7a81c868` |
| `Spex32.dll` | `015a32d4f3b6924ee1067c0d21c805bc96ba3675f06a63ee51d6277a0c26a4a3` |
| `Cilib32.dll` | `661f0f239a32330f4749b9474a4eca55cddfa424691a4989666a68b9041a452d` |
| `lynksusbio.dll` (USB session handler) | `9d199d14809d6f9e95b3b905a713211c22f3c27904a9e5458da9740dedd1c0c0` |
| `cmdproc.dll` | `d9d2bc6f7f196e7993a78253a7bf950193de8d34eaa7841c51843e2f5a40aaba` |
| `SCDaemon.exe` | `6e1a938ee231248dd5b5801f1ed8d8205361ae0354963b27336bbbd8d532f286` |
| `SpyRSAhw.dll` (RSA CSP) | `b77cd254f3260e3c03905d37c814e82e23da9ba653ccae744d4d6662c7034a53` |

The USB kernel driver on the disc (`SCARDLYNKSUSBW.sys`, v1.1.0.6,
2005-01-20) is byte-identical to the copy downloadable from Microsoft's
Update Catalog; the analysis of it predates the disc.
