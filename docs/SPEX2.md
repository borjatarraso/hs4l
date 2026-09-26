# The Windows SPEX/2 middleware, mapped

What the vendor's own Windows stack looked like inside, reconstructed by
static analysis (radare2) of the En-Sign 8.0.0.9 middleware DLLs. Useful
two ways: as the reference for anyone tracing the vendor stack in a Windows
VM, and as the design map for a native Unix replacement — the session-handler
contract below is the layer a Linux implementation has to reproduce (or, in
hs4l's case, sidestep by driving the card directly).

Analysis status: exports, imports, strings and the export thunks — i.e.
structure, not full decompilation. Depths still unmapped: the ioctl codes
`lynksusbio` sends (it resolves kernel32 calls dynamically, so there are no
static import cross-references), and the command tables inside `cmdproc`.

## The stack

```
SpyPK11.dll            PKCS#11 v2.x module (68 C_* exports)
SpyRSAhw.dll,          CryptoAPI CSPs ("SPYRUS HARDWARE RSA CSP",
SpyECDH.dll             ECDSA CSP)
        │  WinSCard + SPEX32
SpexSrvr.dll,           SPEX/2 server + daemon (SCDaemon.exe,
Scmgr.dll               smart-card manager, tray UI)
        │
cmdproc.dll             command processor — re-exports the same
        │               SH_* API one level up
        │
<Spyx>io.dll            transport backends, one per bus:
  lynksusbio.dll          LYNKS USB HSM  ← the hs4l device
  isa95io / isantio /
  isaxpio.dll             ISA-bus reader variants
  mpl2kio.dll             MultiPort-2000 reader
  spexbio.dll             serial / biometric path
```

Below the io layer sits the kernel driver (`SCARDLYNKSUSBW.sys` for USB —
Microsoft's standard WDM smart-card class driver with five SPYRUS vendor
callbacks; plain bulk-USB, T=0-shaped APDUs out EP `0x01`, replies in EP
`0x82`).

## The SH_* session-handler contract

Every transport backend exports the same six `stdcall` functions plus one
multiplexer — one DLL per bus, identical interface:

| Export | Stack | Role |
|---|---|---|
| `SH_Initialize` | 8 | bring the provider up |
| `SH_Terminate` | 4 | shut down |
| `SH_OpenSession` | 12 | open a session to a device ("socket") |
| `SH_CloseSession` | 12 | close it |
| `SH_Information` | 4 | query provider/device info |
| `SH_Process` | 16 | **the exchange primitive**: send a request buffer, get the reply |
| `SxCallModule` | 12 | module multiplexer |

`cmdproc.dll` — the command processor above the transports — exports the
same seven names again: the SPEX/2 stack is a chain of SH_* providers. Its
internal trace strings show the session model it enforces:
`SW_X_Lock (1) CI_SOCKET_IN_USE`, `SW_X_UnSetLogin (1) CI_SOCKET_IN_USE`,
and a PIN-handling step (`ManglePINForPinfile` / `ManglePINForCheck`).

## The USB backend: `lynksusbio.dll`

- Opens the device by name: `\\.\SpyrusLynksUsb-<n>` (n = instance), then
  talks to it with `DeviceIoControl`.
- **No static kernel32 imports** — API names are resolved at runtime
  (GetProcAddress on a name table), so don't expect import-table xrefs when
  disassembling; walk the name-table initialisers instead.
- `SH_Process` (thunk at `0x10001090` → body at `0x100013d0` in the
  58,688-byte file) is the single best trace point for a Windows-VM capture:
  it is the user-mode counterpart of the bulk-out/bulk-in exchange, so
  logging its buffers while the vendor tools run yields the complete
  session bring-up and command corpus, including whatever negotiation gates
  the card before it accepts commands.

## SpyPK11.dll — the PKCS#11 layer

A full standard PKCS#11 v2.x module (68 `C_*` exports) stacked on WinSCard
and SPEX32, plus five exports from the FORTEZZA lineage. It is the natural
behavioral oracle for a native hs4l PKCS#11 provider: slot/token model,
login state, object attributes and the mechanism→command mapping can all be
read off it (or captured live) instead of designed from scratch.

## Operational facts documented by this middleware's manuals

- A wrong-PIN counter blocks the **User PIN** (vendor docs give 5 tries in
  one manual, 10 in another — assume the lower).
- The vendor unblock flow (Admin PIN required) **resets the User PIN to the
  default reset value `1234`**.
- A blocked **Admin PIN is unrecoverable and zeroizes the card** — never
  brute-force the Admin PIN.
- "Change PIN" never worked on LYNKS devices; the vendor path is
  reset-PIN-with-Admin-PIN.
- PIN policy default: 4–8 characters, alphanumeric allowed.
- The stack could **import PFX/P12 key pairs and CER/CRT certificates onto
  the token** as the logged-in User — i.e. on-card key provisioning exists,
  it just needs recovering for Linux.
- The RSA CSP release notes claim **private keys are exportable from the
  LYNKS card** (unlike Rosetta tokens). Unverified against a live card;
  treat as a lead, not a fact.

## Provenance and legality

Findings are from static inspection of the En-Sign 8.0.0.9 CD (SPYRUS,
2005-2010). No SPYRUS code or documentation text is redistributed in this
repository; see [`VENDOR-NOTICE.md`](../VENDOR-NOTICE.md) for the
identification checksums. SPYRUS was absorbed by Route1 Inc. (2021) and the
product line is abandoned — this map exists because no other documentation
of this middleware survives anywhere public.
