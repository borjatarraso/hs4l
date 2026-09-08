# Güralp spyrus-utils — the GPL source parts

These files are copyright Güralp Systems Ltd (authors Bob Dunlop and Laurence
Withers) and are redistributed here unmodified under the licence each file
states in its own header. They were retrieved on 2026-09-08 from Güralp's open
rsync mirror, which is how Güralp distributes the Platinum firmware. Licence
texts: `COPYING.GPL-2` and `COPYING.GPL-3`.

| file here | licence (from its own header) | origin on rsync://rsync.guralp.com | sha256 |
|---|---|---|---|
| include/spyrus.h | GPL-2 (2008-2020) | platinum-crosslib/CMG-DAS/include/spyrus.h | 288728c467a503c7… |
| include/spyrus_dss.h | GPL-3 (2008-2012) | platinum-crosslib/CMG-DAS/include/spyrus_dss.h | cb1de89f8ad8b9a4… |
| include/legacy-2008/spyrus.h | GPL-2 (2008) | platinum-crosslib/CMG-DCM-mk4/include/spyrus.h | 4ab0e844d41ccde4… |
| include/legacy-2008/spyrus_int.h | GPL-2 (2008) | platinum-crosslib/CMG-DCM-mk4/include/spyrus_int.h | c6d853ba3bbe5b4e… |
| scripts/cd11-spyrus-tool.sh | GPL-3 (2010) | platinum-stable/CMG-NAM64/usr/sbin/cd11-spyrus-tool.sh | 1d8b846c02164765… |
| scripts/0140-EAM-hw-config-usb-spyrus.sh | GPL-3 (2011-2012) | platinum-stable/CMG-DCM-mk4-eabi/usr/lib/upgrade/0140-EAM-hw-config-usb-spyrus.sh | a900c2ed93f32aa0… |

## What each file gives you

- **include/spyrus.h** — the public C API of `libspyrus`: open/close, login,
  key generation, get key, certificate load/get/delete, hash, sign, verify, the
  `spyrus_strerror` table of card response codes, and the error constants.
  The 2020 revision adds the EC slot constants and the zero-length-certificate
  error you will hit on a freshly initialised token.
- **include/spyrus_dss.h** — DSA/DSS helpers (parameter handling, signature
  encoding) on top of OpenSSL.
- **include/legacy-2008/spyrus_int.h** — the internal header of the 2008
  library: every card command opcode, every request and response struct, PIN
  types and lengths, the label used for stored keys. This is the wire protocol
  of the LYNKS Series II as Güralp implemented it. `legacy-2008/spyrus.h` is
  the matching public header of that revision.
- **scripts/cd11-spyrus-tool.sh** — the wrapper the Platinum web UI calls
  (`init_card`, `generate_keypair`, `start_keypair`); shows the exact
  `spyrus_util` invocations and PIN handling Güralp uses.
- **scripts/0140-EAM-hw-config-usb-spyrus.sh** — first-boot provisioning of
  `/etc/spyrus` (creates `spyrus.local` and the 1024-bit DSA parameters).

## What is deliberately not here

- Binaries (`spyrus_util`, `spyrus_test`, `libspyrus.so`, `spyrus.cgi`,
  `spyrus_cs.ko`). They are built from the same GPL package but Güralp ships
  no corresponding source or written offer, so redistributing them would
  breach GPL section 3. `scripts/fetch-corpus.sh` fetches them from Güralp at
  install time instead.
- Files with no licence notice (`etc/init.d/spyrus`, the udev rule, the web
  menu entry). The udev match is reproduced in this repo's own `udev/` rules.
- Güralp helper libraries `libgslutil` and `libioline`: no licence markers,
  no published source; treated as proprietary.

Güralp has not published the `spyrus-utils` source tree itself. Since the
library is GPL-2, a request to Güralp support is the route to a fully
self-built, binary-free `libspyrus`; see the main README.
