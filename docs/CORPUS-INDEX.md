# SPYRUS firmware corpus — what is here and why

Mirrored 2026-09-08 from the vendor's open firmware mirror (no auth) by
`scripts/fetch-corpus.sh`. Layout: `<module>/<platform>/<original path>`.
Checksums for every file ship in the repo as `CHECKSUMS.corpus.sha256`. The corpus dir is git-ignored: vendor binaries stay out of
the public repo (see [VENDOR-NOTICE.md](../VENDOR-NOTICE.md)).

## Modules
| module               | what                                             |
|----------------------|--------------------------------------------------|
| platinum-stable      | shipped rootfs, 7 platforms                      |
| platinum-prerelease  | CMG-DAS only, newer (2025-02) spyrus_util build  |
| platinum-crosslib    | SDK: headers, dev .so symlinks, *-config scripts |
| ctbto-prerelease     | CTBTO variant of CMG-DAS + mk4-eabi              |
| platinum-builder     | source tree — DENIED ("invalid uid webmirror")   |

## Platforms and CPU
| platform          | arch            | spyrus_util | spyrus_cs.ko kernel   |
|-------------------|-----------------|-------------|------------------------|
| CMG-NAM64         | x86-64 (native) | yes, debug  | 2.6.36-gsl-nam64       |
| CMG-NAM           | i386            | yes         | 2.6.36-gsl-nam (VIA C7)|
| CMG-NAM-mk2       | i386            | yes         | —                      |
| CMG-DCM-mk4-eabi  | ARM EABI5       | yes         | 2.6.36-cm-x270         |
| CMG-DCM-mk4       | ARM OABI        | yes         | 2.6.31-cm-x270         |
| CMG-DAS           | ARM EABI5       | yes         | —                      |
| CMG-DCM-mk2x      | ARM             | no (wrapper only) | —                |

## Highest-value files
- `platinum-crosslib/CMG-DCM-mk4/include/spyrus_int.h` — full wire protocol:
  every command opcode (Zeroize 0x6D, Generate_X 0x85, Load_Certificate 0x2F,
  Change_Pin_Phrase 0x6E, Firmware_Upgrade 0x70 ...), request/response structs,
  PIN types (SSO 0x25 / USER 0x2A), lengths. GPL-2, (C) the vendor 2008-2011.
- `platinum-crosslib/*/include/spyrus.h`, `spyrus_dss.h` — public C API of
  libspyrus (open/login/keygen/sign/verify/cert/hash, strerror table).
- `platinum-stable/CMG-NAM64/usr/sbin/spyrus_util` + `usr/lib64/`, `lib64/` —
  native x86-64 CLI with debug symbols and its full library closure. Runs on a
  PC via `bin/spy-native.sh` (verified against serial 01:00:00:00:f0:00:18:4f).
- `platinum-stable/*/lib*/modules/*/drivers/char/pcmcia/spyrus_cs.ko` — GPL
  kernel driver for the PCMCIA/CardBus LYNKS card (pcmcia id 0244:0300).
  Binary only, old kernels; useful as a reference for the card-slot variant.
- `platinum-stable/*/etc/udev/rules.d/81-spyrus.rules` — the vendor's udev match
  (manufacturer "Spyrus Inc", product "Lynks USB Interface", group spyrus).
- `platinum-stable/*/etc/init.d/spyrus`, `usr/lib/upgrade/0140-EAM-hw-config-usb-spyrus.sh`
  — how the digitiser provisions /etc/spyrus (spyrus.local, dsaparam.pem.local).
- `platinum-stable/*/srv/http/cgi-bin.auth/spyrus.cgi` — the web-UI backend.
- `platinum-stable/*/usr/sbin/spyrus_test` — the vendor's self-test tool.
- `*/share/build.md5sums/spyrus-utils`, `usr/share/platinum-versions/spyrus-utils`
  — package build ids (git sha 2cb58d1f...) for the spyrus-utils package.

## Not found on the server
No source tarball for spyrus-utils/libspyrus (GPL) — the crosslib README says
open-source package code "is distributed from the platinum website"; the
builder module is access-denied. No SPYRUS-original (SPEX+/CSP/PKCS#11) files.

## Runtime notes for the native build
libspyrus locks `/var/lock/spyrus.lck` and reads `/etc/spyrus/spyrus.local`;
both must be writable/readable by the invoking user, and the USB node needs RW.
