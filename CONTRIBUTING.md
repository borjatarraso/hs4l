# Contributing

hs4l is small on purpose: a few shell wrappers, a fetcher, a verifier and
notes. Contributions that keep it that way are welcome.

## Reporting a device

The most useful contribution is a report from a token that is not in the
"Supported devices" table of the README. Open an issue with:

- `lsusb -v -d 08df:` (or the PCMCIA id if it is a card),
- `bin/spy.sh --status -D` and `bin/spy.sh --state -D`,
- what worked and what did not (`--init`, `--keygen`, `--getkey`, `--sign`).

Never paste PINs, and be aware that `--status` prints the serial number.

## Changes

- Shell must pass `shellcheck` (`bin/*.sh` and `scripts/fetch-corpus.sh`
  are POSIX `sh`; the rest is bash). Python must run on 3.9+ with the
  standard library only. `make test` runs both plus `tests/`; keep it green
  and add a test when you touch `scripts/verify.py`.
- Do not add vendor binaries, or anything without an explicit licence
  notice, to the tree. See `VENDOR-NOTICE.md`; fetch-at-install is the rule.
- Files under `third_party/spyrus-gpl/` are redistributed verbatim. Do not
  edit them; their headers carry the copyright and licence that apply.
- Keep the README claims tied to something you ran on a real token, and
  say which build (`spyrus_util --version`).
- One change per commit, with a message that says why.

## Licence of contributions

By contributing you agree that your original work is released under the
BSD-3-Clause licence in `LICENSE`.
