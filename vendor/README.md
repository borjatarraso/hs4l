# vendor/

This directory holds the **third-party ARM runtime** used to talk to the
SPYRUS LYNKS Series II. It is intentionally **empty in git** — the SPYRUS /
Guralp binaries are proprietary and are not redistributed by this project
(see [../VENDOR-NOTICE.md](../VENDOR-NOTICE.md)).

Populate it once:

```sh
scripts/fetch-vendor.sh          # pulls vendor/sysroot/ from the public mirror
scripts/fetch-vendor.sh --verify # checks it against ../CHECKSUMS.sha256
```

After that you will have `vendor/sysroot/usr/sbin/spyrus_util` and the
libraries it needs, and `bin/spy.sh` will find them automatically.
