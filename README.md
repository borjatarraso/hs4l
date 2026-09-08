# hs4l — HSM-SPYRUS-4-Linux

**Drive an orphaned SPYRUS LYNKS Series II hardware security module from
Linux — no Windows, no vendor middleware, no known PIN.** Reinitialise it,
generate keys on-chip, sign, and verify, using the manufacturer's own ARM
firmware run under `qemu-arm-static` against the raw USB pipe via `libusb`.

> SPYRUS is defunct (absorbed by Route1 in 2021). There is no Linux driver
> and the Windows middleware is gone from the public web. The one thing that
> still works turned out to be a **seismograph vendor's firmware** — Güralp
> Systems ship an ARM Linux tool, `spyrus_util`, that speaks the undocumented
> SPYCOS protocol. hs4l wraps it so it runs on any Linux box.

| | |
|---|---|
| Device | SPYRUS LYNKS Series II · USB `08df:0a00` · part `3003-F0` ©2005 |
| Validation | FIPS 140-2 Level 2 · NIST CMVP #679 · OS: SPYCOS |
| Crypto | on-chip DSA-1024 / SHA-1 (FIPS 186-2); slot 9 = EC |
| Proven | keygen · sign · verify · CSR · reinitialise-from-scratch |
| Host tested | x86-64 Fedora + `qemu-arm-static` + `libusb` |

## ⚠️ Read first: the vendor binaries are not in this repo

`spyrus_util` and `libspyrus` are **SPYRUS/Güralp proprietary** and are **not
redistributed here**. `scripts/fetch-vendor.sh` pulls them from Güralp's
**public** rsync mirror and checksums them. See
**[VENDOR-NOTICE.md](VENDOR-NOTICE.md)**. Everything original in this repo
(wrappers, docs, diagrams, examples) is BSD-3-Clause.

## Quickstart

```sh
git clone https://github.com/borjatarraso/hs4l && cd hs4l
scripts/fetch-vendor.sh            # populate vendor/sysroot/ + verify checksums
scripts/setup-udev.sh              # optional: group access to the token
sudo apt install qemu-user-static  # or your distro's equivalent

bin/spy.sh --status                # talk to the card (read-only)
```

Reinitialise and use it from scratch:

```sh
bin/spy.sh --init --loose --sso-pin 1234 --user-pin 1234   # wipes it; type 'yes'
bin/spy.sh --keygen --index 1                              # NO --dsaparam, NO --pin
bin/spy.sh --getkey --index 1 > pub.pem
printf 'hello from the LYNKS' > msg
bin/spy.sh --sign msg --index 1 --binary > sig.bin
python3 scripts/verify.py pub.pem msg sig.bin             # VALID
```

Full walkthrough: **[docs/REINITIALIZE.md](docs/REINITIALIZE.md)**.

## How it works

The token's USB interface is vendor-specific with **no kernel driver**, so
`libusb` claims it from userspace. `spyrus_util` is a 32-bit ARM binary that
links `libusb` (not a kernel module), so running it under `qemu-arm-static` —
which forwards syscalls straight to the host kernel — lets its USB I/O reach
the real device node unchanged.

![Emulation path](docs/diagrams/emulation-path.svg)

### The one real bug: `Execution Failure`

Every `--keygen` returned result code `0x0a` (Execution Failure) — but the
full command/response round-trip completed each time, so it was never a
transport problem. The card validates externally supplied DSA parameters the
**FIPS 186-2** way (it wants the generation seed + counter), and modern
OpenSSL emits bare parameters. **Fix: don't pass `--dsaparam`; let the card
self-generate.** Only word 4 of the response differs between fail and pass:

![Response decode](docs/diagrams/response-decode.svg)

Details: **[docs/PROTOCOL.md](docs/PROTOCOL.md)** ·
**[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.

## The signature, byte for byte

The card returns a textbook DSS signature — ASN.1 `SEQUENCE { INTEGER r,
INTEGER s }`, 47 bytes. `r` starts `0x60` (20 bytes, no pad); `s` starts
`0x87` so DER prepends a `0x00` sign pad (21 bytes):

![Signature byte-map](docs/diagrams/signature-bytemap.svg)

Verify with the public key alone (a one-byte change is rejected):

![DSA verify](docs/diagrams/dsa-verify.svg)

`examples/` holds a real `pubkey.pem`, `msg.txt`, `sig.bin` you can verify
now, plus `dsaparam.pem.rejected` — the counter-example that draws `0x0a`.

## Layout

```
bin/spy.sh              wrapper: spyrus_util under qemu-user + libusb
scripts/fetch-vendor.sh fetch vendor/sysroot from the public Guralp mirror
scripts/verify.py       off-card SHA-1 DSA verify (pyca cryptography)
scripts/setup-udev.sh   install the udev rule (group access)
udev/                   the udev rule
docs/                   PROTOCOL · REINITIALIZE · TROUBLESHOOTING + diagrams/
examples/               real pubkey / message / signature + rejected params
CHECKSUMS.sha256        SHA-256 of the vendor build these docs target
VENDOR-NOTICE.md        what is not shipped, and why
```

## Requirements

`qemu-user-static` (`qemu-arm-static`), `rsync`, Python 3 + `cryptography`,
`libusb` on the host, and a SPYRUS LYNKS Series II on USB.

## Legality

This operates a device **you physically own and are entitled to use**. The
reinitialise path is a **documented** SPYCOS function; hs4l extracts no key
material and bypasses no authentication. See VENDOR-NOTICE.md.

## License

BSD-3-Clause for the original work here (see [LICENSE](LICENSE)). Vendor
binaries are not included and remain the property of their owners.
