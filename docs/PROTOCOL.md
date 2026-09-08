# SPYCOS on the wire

Notes recovered by reading the **un-stripped** Güralp ARM `spyrus_util` /
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
  W4 RESULT  0000 0000       0000 000a       result code (0x0a here)
  W7 index   0000 0001       0000 0001       key slot (1..9; slot 9 = EC)
  W9.. data  0000 0400 ...   echoed          P (1024b) / Q (160b) / G (1024b)
```

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

Classic slots are **DSA-1024 / SHA-1 (FIPS 186-2)**; slot 9 is EC. The card
validates externally-supplied DSA domain parameters the FIPS 186-2 way (it
wants the generation **seed + counter**), which is why bare OpenSSL-3
parameters are rejected — let the card self-generate. Signatures are DSS:
ASN.1 `SEQUENCE { INTEGER r, INTEGER s }`, each a 160-bit integer.
