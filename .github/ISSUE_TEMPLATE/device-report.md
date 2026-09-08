---
name: Device report
about: Tell us how hs4l behaves with your SPYRUS unit
title: "Device report: <model / interface>"
labels: device-report
---

**Unit** (model, USB or PCMCIA, label on the back):

**Host** (distro, arch, `qemu-arm-static` or native, `spyrus_util --version`):

**Identification** (do not paste PINs; `--status` shows the serial, redact it if you prefer):

```
lsusb -v -d 08df:
bin/spy.sh --status -D
bin/spy.sh --state -D
```

**What worked** (`--status`, `--init`, `--keygen`, `--getkey`, `--sign`, `verify.py`):

**What did not** (exact output, add `-D -D` for the wire-level trace):
