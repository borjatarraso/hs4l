#!/usr/bin/env python3
"""hs4l -- verify a SPYRUS LYNKS signature off-card.

The card signs DSA-1024 / SHA-1 (FIPS 186-2). OpenSSL 3 REFUSES to verify
SHA-1+DSA at policy level ("invalid digest") -- that is a deprecation policy,
not a signature failure, so it cannot be the judge. pyca/cryptography still
permits the legacy pairing and gives the real verdict.

    python3 scripts/verify.py examples/pubkey.pem examples/msg.txt examples/sig.bin

Exit 0 = valid, 1 = invalid/tampered, 2 = usage/error.
Requires:  pip install cryptography
"""
import sys

def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    pub_path, msg_path, sig_path = argv[1:]
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        print("hs4l: missing dependency -- pip install cryptography", file=sys.stderr)
        return 2

    with open(pub_path, "rb") as f:
        pub = serialization.load_pem_public_key(f.read())
    with open(msg_path, "rb") as f:
        msg = f.read()
    with open(sig_path, "rb") as f:
        sig = f.read()

    try:
        pub.verify(sig, msg, hashes.SHA1())  # DER-encoded r,s
    except InvalidSignature:
        print("INVALID  -- signature does not match (tampered or wrong key)")
        return 1
    print("VALID    -- on-card signature verified against the public key")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
