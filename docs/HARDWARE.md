# SPYRUS hardware family — identification guide

How to recognise every device in the LYNKS / Rosetta / FORTEZZA family that
the SPYRUS middleware once drove, so you can tell what that unmarked card or
token on the used market actually is. Compiled from the driver INF files and
the CSP registry data of the final SPYRUS middleware release (En-Sign
8.0.0.9, 2010); hs4l itself only needs the `08df:0a00` row.

No SPYRUS material is redistributed here — only device identifiers, ATRs and
other facts. Checksums identifying the vendor files we compared against are
in [`VENDOR-NOTICE.md`](../VENDOR-NOTICE.md).

## USB devices (vendor ID `08df` = SPYRUS Inc.)

| VID:PID | Device | Driver INF | Notes |
|---|---|---|---|
| `08df:0a00` | **SPYRUS Lynks USB Interface** — LYNKS Series II USB HSM | `ScardLynksUsb.inf` | The device hs4l drives. Part no. `3003-F0` (© 2005). Vendor-specific bulk USB, **not** USB-CCID |
| `08df:0001` | SPYRUS Rosetta USB Token V1 | `RoseUsbw.inf` | Serial-bridge family (`EFOB.Dev` section) |
| `08df:0002` | SPYRUS Rosetta USB Token V2 | `RoseUsbw.inf` | x86 / amd64 / ia64 driver sections |
| `08df:0003` | SPYRUS Rosetta USB Token V3 | `RoseUsbw.inf` | Last Rosetta USB generation |
| USB class `0b` subclass `00` | any **CCID** smart-card reader | `usbccid.inf` | The middleware's generic fallback reader |

Tip: on Linux, `lsusb -d 08df:` finds any of them; `08df:0a00` with the
string descriptor "Lynks USB Interface" is the LYNKS HSM.

## PCMCIA cards (service `CryptCrd` / `LynksCard`)

| PCMCIA version string | Card |
|---|---|
| `SPYRUS-Lynks_Privacy_Crypto_Card_____-805D` | LYNKS Privacy Card (PCMCIA sibling of the USB HSM) |
| `SPYRUS-Lynks_Privacy_Crypto_Card_____-6FE6` | LYNKS Privacy Card (earlier CIS) |
| `SPYRUS-Lynks/EES_Crypto_Card-6FE6` | LYNKS/EES (escrowed-encryption variant) |
| `SPYRUS-Lynks_CA_Crypto_Card_-5551` | LYNKS CA Crypto Card |
| `SPYRUS-Lynks_PrivCOM_Crypto_Card_____-43F6` | LYNKS PrivCOM |
| `SPYRUS-FORTEZZA_CRYPTO_CARD-0244-0300` / `-EB16` / `-5Ab7` | FORTEZZA Crypto Card (several CIS revisions) |
| `SPYRUS-000` | unidentified early card |

On Linux, `pccardctl ident` prints these strings from the card CIS. The
PCMCIA LYNKS cards are also reachable from Linux through the GPL `spyrus_cs`
driver (`/dev/spyrus0`) — see the README section on the wider firmware
corpus.

## Readers

- **SPYRUS PAR2** — serial reader with a **secure PIN-entry keypad**; the
  vendor tools can route PIN entry through it so PINs never touch the host.
- Generic **USB-CCID** readers (class `0b`) worked with the middleware for
  Rosetta smart cards.
- The USB tokens above are readers themselves — no separate hardware.

## ATRs (from the middleware's smart-card registry)

| Card (registry name) | ATR | Notes |
|---|---|---|
| SPYRUS LYNKS USB / SPYRUS Rosetta LYNKS | `3b fb 11 00 00 0e 28 80 59 53 50 59 52 55 53 ae 00 b5` | The hs4l device. ASCII run spells `SPYRUS`. **TD1 = `0x0e` → protocol T=14** (proprietary): this is why stock PC/SC stacks refuse the card with `SCARD_E_PROTO_MISMATCH` and why a custom transport (libusb / `/dev/spyrus0`) is required |
| SPYRUS Rosetta | `3b fb 10 00 00 40 00 80 59 53 50 59 52 55 53 ae 00 00` | |
| SPYRUS HYDRA PC Enterprise | `3b fb 10 00 00 40 00 80 59 53 50 59 52 55 53 02 00 00` | |
| five CAC entries (Axalto, Gemalto, Gemplus, Oberthur ×3, Schlumberger) | see the registry export | US Common Access Cards |

## Provenance

All identifiers above were read out of: `drivers/*/*.inf` (device IDs) and
`RSA_CSP_RP.reg` (ATR → CSP wiring) on the En-Sign 8.0.0.9 CD (SPYRUS,
2005-2010, last known middleware release). SPYRUS Inc. was acquired by
Route1 Inc. in 2021; the product line is discontinued. This guide is
independent documentation of hardware identifiers, not an affiliate
publication.
