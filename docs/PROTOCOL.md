# SPYCOS on the wire

Notes recovered by reading the **un-stripped** vendor ARM `spyrus_util` /
`libspyrus.so.3` and watching the USB traffic. Enough to understand what the
tool is doing; not a full protocol spec.

## Transport

- USB `08df:0a00`, single **vendor-specific (class 0)** interface, two bulk
  endpoints: `0x01 OUT` (command), `0x82 IN` (response), 64-byte packets.
- No kernel driver binds it (`driver = NONE`), so `libusb` claims the
  interface directly from userspace. There is **no daemon** — one process
  owns the pipe for the length of a single command.

## Command / response blocks

Blocks are sequences of **big-endian 32-bit words**: an opcode, framing /
lengths, a **result slot** the card fills in, then the payload. The response
sets header **byte 0 to `0x90`** (`0x80` "response" | `0x10`) and echoes the
opcode; the **result code lands in word 4 (W4)**.

```
             sent            response        meaning
  W0 opcode  0000 0085       9000 0085       0x85 GenerateDSAKeyPair; 0x90 marker
  W1         0000 0000       0000 0000       reserved
  W2 offset  0000 0018       0000 0018       payload starts after the 24-byte header
  W3 length  0000 0144       0000 0144       total block length (324 bytes)
  W4 RESULT  0000 0000       0000 000a       result code (0x0a here)
  W5         0000 0000       0000 0000       reserved
  W6 len     0000 012c       echoed          payload length (300)
  W7 index   0000 0002       echoed          key slot (1..9; slot 9 = EC P-256)
  W8 type    0000 000a       echoed          key type 0x0a = DSA
  W9.. data  0000 0400 ...   echoed          P (1024b) / Q (0xa0 = 160b) / G (1024b)
```

Commands with no input payload (`0x26` Get_Status, `0x25` personality list)
send W2 = 0 and W3 = `0x18`; the card appends its output after the header.

Opcodes seen: **`0x85` GenerateDSAKeyPair**, **`0x2f` LoadCertificate**
(keygen auto-loads a `TEMPXXXX` placeholder cert carrying the new pubkey).

## Result codes (`spyrus_strerror`, indexed from 0)

| code | meaning | | code | meaning |
|---|---|---|---|---|
| 0 | Spyrus command failed | | 7 | Invalid Data Size |
| 1 | **Passed** | | 8 | Invalid Header |
| 2 | Checkword Failure | | 9 | Invalid State |
| 3 | Invalid Type | | **10 (0x0a)** | **Execution Failure** |
| 4 | Invalid Mode | | 11 | No Key Loaded |
| 5 | Invalid Key Index | | 21 | NO PQG Loaded |
| 6 | Invalid Cert Index | | | |

`0x0a` is **generic** — "the card tried and could not". It is *not* a
structural rejection (Invalid Header / State / NO PQG). See
[the byte-map and decode diagrams](diagrams/) and TROUBLESHOOTING.md.

## Status registers

`--state` returns a 9-byte status word plus **SR** and **PRR**. SR reads
`25` on an initialised-but-empty card and steps to `26` after a fresh
`--init`.

## Crypto profile

| slots | key | hash | signature |
|---|---|---|---|
| 1..8 | DSA-1024, q 160-bit (FIPS 186-2) | SHA-1 (20-byte digest in the Sign payload) | DER `SEQUENCE { r, s }`, 160-bit each |
| 9 | EC P-256 (secp256r1 / prime256v1, id-ecPublicKey) | **SHA-256** (measured 2026-09-08) | DER `SEQUENCE { r, s }`, 256-bit each; verifies with `openssl dgst -sha256 -verify` |

Slot 9 is the one surprise in the profile. Every document about the device
says SHA-1, and the DSA slots do hash SHA-1; but the signature the P-256 slot
puts on a body verifies under **SHA-256 only**. It was tested against SHA-1,
SHA-224, SHA-256, SHA-384 and SHA-512, a SHA-1 digest zero-padded to 32
bytes, and swapped r/s: exactly one candidate matched. The self-signed X.509
root the card produced on that slot (declared `ecdsa-with-SHA256`,
1.2.840.10045.4.3.2) verifies with plain `openssl verify`, no legacy
tolerance needed; `examples/pubkey-slot9.pem`, `tbs-slot9.der` and
`sig-slot9.bin` are that key, that certificate body and that signature.
`scripts/verify.py` picks the hash from the key's algorithm OID for the
same reason: the card gives no choice.

The DSA profile is fixed at **L = 1024, N = 160**. `libspyrus` hard-codes it: the
Q block of the Generate_X payload is always written as `0x000000a0` (160
bits) followed by `BN_bn2bin_fixed(q, buf, 20)`. OpenSSL 3 generates a
**224-bit q** for 1024-bit parameters by default, so only the low 160 bits
of q reach the card; that q' no longer divides p−1, the card's parameter
check fails and it answers `0x0a`. Either let the card self-generate, or
generate with `-pkeyopt qbits:160` (verified accepted; see
TROUBLESHOOTING.md). Signatures are DSS: ASN.1 `SEQUENCE { INTEGER r,
INTEGER s }`, each a 160-bit integer.

The Sign command (`0x5b`) takes the 20-byte SHA-1 in the payload and
returns `r` and `s` in two 40-byte fields (20 bytes used each); the library
DER-wraps them. The Generate_X payload is `len, index, type (0x0a = DSA)`
followed by three `bits, bytes...` blocks for P, Q, G.
