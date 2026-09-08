# Reinitialise & use, from zero

A device you own but whose PIN you do not have can be **reinitialised from
scratch** — a documented SPYCOS function that destroys all keys/certs and
sets fresh PINs. No old secret is needed. (If you *do* have keys on it you
care about, stop: reinit erases them.)

## 0. Prerequisites

```sh
scripts/fetch-vendor.sh          # get vendor/sysroot/ (see VENDOR-NOTICE.md)
scripts/setup-udev.sh            # optional: group access, no per-boot chmod
# or, ad hoc, find the node and open it:
lsusb -d 08df:0a00               # note the bus/device numbers
sudo chmod 666 /dev/bus/usb/BBB/DDD
```

## 1. Read state (read-only, safe)

```sh
bin/spy.sh --state
bin/spy.sh --status              # serial, key/cert counts + flags
```

## 2. Wipe & take ownership

```sh
bin/spy.sh --init --loose --sso-pin 1234 --user-pin 1234
# WARNING: erases all keys/certs. Type 'yes' at the prompt (read from the tty).
```

`--loose` = init-only mode. Standard/`--use` mode expects a certificate in
every slot.

## 3. Generate a keypair on-chip

```sh
bin/spy.sh --keygen --index 1    # NO --dsaparam, NO --pin  (see TROUBLESHOOTING.md)
```

The card runs the FIPS 186-2 domain-parameter routine itself (~1 min; prints
its counter and `h`).

## 4. Export the public key

```sh
bin/spy.sh --getkey --index 1 > pub.pem
openssl dsa -pubin -in pub.pem -text -noout   # inspect P/Q/G/Y
```

## 5. Sign, and 6. verify

```sh
printf 'hello from the LYNKS' > msg
bin/spy.sh --sign msg --index 1 --binary > sig.bin
python3 scripts/verify.py pub.pem msg sig.bin      # VALID / INVALID
```

There is also `--request --index N --out csr.pem` for a CSR if you want a
certificate over the on-card key.

See `examples/` for a real `pubkey.pem` + `msg.txt` + `sig.bin` you can
verify immediately, and `examples/dsaparam.pem.rejected` (the counter-example
that draws `0x0a`).
