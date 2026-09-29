# hs4l -- convenience targets; every one is a plain script call you can run by hand.
#
#   make          verify the toolchain (idempotent; nothing auto-installed)
#   make run      environment status, or forward args to bin/spy.sh (same as ./run)
#   make check    toolchain + test + verify + vendor checksum self-test
.DEFAULT_GOAL := all
.PHONY: help all deps run fetch corpus setup status state list verify test check clean
all: deps
	@chmod +x run 2>/dev/null || true
	@echo "ready -- ./run prints the environment status; './run --status' talks to the token"
deps:
	@command -v python3 >/dev/null 2>&1 || { echo "deps: python3 not found -- install python3 (every hs4l script needs it)"; exit 1; }
	@if command -v qemu-arm-static >/dev/null 2>&1; then echo "deps: qemu-arm-static found"; \
	else echo "deps: qemu-arm-static not found -- needed to run the vendor ARM tool (install qemu-user-static)"; fi
	@if [ -x vendor/sysroot/usr/sbin/spyrus_util ]; then echo "deps: vendor runtime present (vendor/sysroot)"; \
	else echo "deps: vendor runtime not fetched -- run scripts/fetch-vendor.sh (network; see VENDOR-NOTICE.md)"; fi
run:
	@./run
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
check: deps test verify
	@if [ -d vendor/sysroot ]; then scripts/fetch-vendor.sh --verify -q; else echo "vendor/sysroot not fetched (make fetch); checksum self-test skipped"; fi
clean:
	rm -rf vendor/sysroot vendor/spyrus-corpus
