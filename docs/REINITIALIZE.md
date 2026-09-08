# Reinitialise & use, from zero

A device you own but whose PIN you do not have can be **reinitialised from
scratch** — a documented SPYCOS function that destroys all keys/certs and
sets fresh PINs. No old secret is needed. (If you *do* have keys on it you
care about, stop: reinit erases them.)

## 0. Prerequisites

```sh
scripts/fetch-vendor.sh          # get vendor/sysroot/ (see VENDOR-NOTICE.md)
scripts/setup-udev.sh            # run without sudo: udev rule, spyrus group, lock + /etc/spyrus
# or skip it: bin/spy.sh falls back to sudo when the USB node, /var/lock/spyrus.lck
# or /etc/spyrus are not writable by you (HS4L_SUDO=1 forces sudo, =0 forbids it)
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
its counter and `h`). If you want host-generated parameters, they must have
a **160-bit q**:

```sh
openssl genpkey -genparam -algorithm DSA -pkeyopt pbits:1024 -pkeyopt qbits:160 -out dsa.pem
bin/spy.sh --keygen --index 1 --dsaparam dsa.pem
```

OpenSSL 3's default for 1024-bit parameters is a 224-bit q, which the
library truncates and the card rejects with `0x0a`.

## 4. Export the public key

```sh
bin/spy.sh --getkey --index 1 > pub.pem
# native 2.1.0 build: bin/spy-native-getkey.sh 1 > pub.pem  (its --getkey fails)
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
verify immediately, `examples/dsaparam.pem.rejected` (224-bit q, draws
`0x0a`) and `examples/dsaparam-1024-160.pem.accepted` (160-bit q, accepted).
