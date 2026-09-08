# hs4l -- convenience targets; every one is a plain script call you can run by hand.
.PHONY: help fetch corpus setup status state list verify test check clean
help:
	@echo "make fetch    scripts/fetch-vendor.sh   ARM runtime -> vendor/sysroot (checksummed)"
	@echo "make corpus   scripts/fetch-corpus.sh   every SPYRUS file, all platforms, x86-64 closure"
	@echo "make setup    scripts/setup-udev.sh     udev rule, spyrus group, lock + /etc/spyrus (sudo)"
	@echo "make status   bin/spy.sh --status       talk to the token (read-only)"
	@echo "make state    bin/spy.sh --state"
	@echo "make list     bin/spy.sh --list         key slots"
	@echo "make verify   scripts/verify.py on the shipped example triple"
	@echo "make test     shellcheck (if installed) + verify.py self-test + tests/ (unittest)"
	@echo "make check    make test + verify + vendor checksum self-test"
fetch:   ; scripts/fetch-vendor.sh
corpus:  ; scripts/fetch-corpus.sh
setup:   ; scripts/setup-udev.sh
status:  ; bin/spy.sh --status
state:   ; bin/spy.sh --state
list:    ; bin/spy.sh --list
verify:  ; python3 scripts/verify.py examples/pubkey.pem examples/msg.txt examples/sig.bin
test:
	@if command -v shellcheck >/dev/null 2>&1; then \
	  shellcheck -x -s sh bin/*.sh scripts/fetch-corpus.sh && \
	  shellcheck -x scripts/fetch-vendor.sh scripts/setup-udev.sh && echo "shellcheck: ok"; \
	else echo "shellcheck: not installed, skipped"; fi
	python3 scripts/verify.py --self-test
	python3 -m unittest discover -s tests
check: test verify
	@[ -d vendor/sysroot ] && scripts/fetch-vendor.sh --verify | tail -1 || echo "vendor/sysroot not fetched (make fetch)"
clean:
	rm -rf vendor/sysroot vendor/spyrus-corpus
