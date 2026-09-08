# Vendor notice & licensing

**hs4l does not redistribute any SPYRUS or Güralp Systems proprietary
software.** This is a deliberate choice, for your protection and theirs.

## What is *not* in this repository

The tool that actually speaks the SPYCOS protocol is the vendor's own ARM
binary and library:

| file | role | ~size |
|------|------|-------|
| `usr/sbin/spyrus_util` | the CLI that inits / keygens / signs | 36 KB |
| `usr/lib/libspyrus.so.3(.1)` | the SPYCOS protocol engine | 243 KB |
| `usr/sbin/spyrus_test`, `cd11-spyrus-tool.sh` | vendor helpers | — |
| `usr/lib/libgslutil`, `libiso8601`, `libioline-*` | Güralp support libs | — |
| `usr/lib/libusb-1.0`, `libssl/ libcrypto 1.0.0`, `/lib/*` glibc | runtime | — |

These originate in **Güralp Systems' "Platinum" digitiser firmware** and
embed **SPYRUS, Inc.** intellectual property. SPYRUS was acquired by
**Route1 Inc.** (2021-09-15); Güralp publish their firmware on a public
mirror. None of it is licensed for redistribution by this project, so it is
kept out of git.

## How you get it anyway

`scripts/fetch-vendor.sh` downloads exactly those files from Güralp's own
**public** rsync mirror into `vendor/sysroot/`, then verifies them against
[`CHECKSUMS.sha256`](CHECKSUMS.sha256) (SHA-256 of the June-2024 Platinum
"stable" build these docs were written against). You are pulling the vendor's
own published bytes, not a re-hosted copy.

```sh
scripts/fetch-vendor.sh
```

If the mirror layout has moved, the script prints how to place the files by
hand; any Güralp Platinum ARM rootfs (release ≥ 15781) will do.

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
