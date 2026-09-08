#!/usr/bin/env python3
"""hs4l -- verify a SPYRUS LYNKS signature off-card.

The card signs DSA-1024 / SHA-1 (FIPS 186-2). OpenSSL 3 REFUSES to verify
SHA-1+DSA at policy level ("invalid digest") -- that is a deprecation policy,
not a signature failure, so it cannot be the judge. This script does the DSA
arithmetic itself (FIPS 186-4 section 4.7) with nothing but the Python
standard library, so it runs wherever Python 3.9+ does and carries no
deprecation policy of its own.

    python3 scripts/verify.py examples/pubkey.pem examples/msg.txt examples/sig.bin
    python3 scripts/verify.py --self-test

The public key is read as PEM or DER SubjectPublicKeyInfo (what `--getkey`
prints). The signature is read either DER-encoded, SEQUENCE { INTEGER r,
INTEGER s } (what `--sign --binary` prints), or as raw r || s (2 x 20 bytes);
the encoding is auto-detected unless --format says otherwise.

Exit 0 = valid, 1 = invalid/tampered, 2 = usage or unreadable/malformed input.
"""
import argparse
import base64
import hashlib
import re
import sys

OID_DSA = bytes.fromhex("2a8648ce380401")  # 1.2.840.10040.4.1 (id-dsa)


class FormatError(ValueError):
    """The input is not what it claims to be (bad PEM, DER, key or signature)."""


# --- minimal DER reader (only what SPKI and DSS signatures need) ---------------

def der_tlv(data, pos=0):
    """Return (tag, value, next_pos) for the TLV that starts at pos."""
    if pos + 2 > len(data):
        raise FormatError("DER: truncated")
    tag = data[pos]
    length = data[pos + 1]
    pos += 2
    if length & 0x80:
        nbytes = length & 0x7F
        if nbytes == 0 or nbytes > 4 or pos + nbytes > len(data):
            raise FormatError("DER: bad length")
        length = int.from_bytes(data[pos:pos + nbytes], "big")
        pos += nbytes
    end = pos + length
    if end > len(data):
        raise FormatError("DER: length runs past the end of the data")
    return tag, data[pos:end], end


def der_items(body):
    """Return the (tag, value) TLVs that body is a concatenation of."""
    items, pos = [], 0
    while pos < len(body):
        t, v, pos = der_tlv(body, pos)
        items.append((t, v))
    return items


def der_sequence(data):
    """Return the (tag, value) children of the SEQUENCE that data consists of."""
    tag, body, end = der_tlv(data)
    if tag != 0x30:
        raise FormatError("DER: expected SEQUENCE, got tag 0x%02x" % tag)
    if end != len(data):
        raise FormatError("DER: %d trailing byte(s) after SEQUENCE" % (len(data) - end))
    return der_items(body)


def der_integer(item):
    """Return the non-negative int held by a (tag, value) INTEGER."""
    tag, value = item
    if tag != 0x02 or not value:
        raise FormatError("DER: expected INTEGER")
    if value[0] & 0x80:
        raise FormatError("DER: negative INTEGER where a positive one was expected")
    return int.from_bytes(value, "big")


# --- key and signature decoding -----------------------------------------------

def pem_to_der(data, label="PUBLIC KEY"):
    """Return the DER inside a PEM block, or data unchanged when it is not PEM."""
    if b"-----BEGIN" not in data:
        return data
    m = re.search(rb"-----BEGIN ([A-Z0-9 ]+)-----\s*(.*?)\s*-----END \1-----", data, re.S)
    if not m:
        raise FormatError("PEM: no complete BEGIN/END block")
    found = m.group(1).decode()
    if found != label:
        raise FormatError("PEM: block is '%s', expected '%s'" % (found, label))
    try:
        return base64.b64decode(re.sub(rb"\s+", b"", m.group(2)), validate=True)
    except ValueError as e:
        raise FormatError("PEM: bad base64 (%s)" % e) from None


def load_dsa_public_key(data):
    """Parse a SubjectPublicKeyInfo (PEM or DER) into (p, q, g, y)."""
    spki = der_sequence(pem_to_der(data))
    if len(spki) != 2 or spki[0][0] != 0x30 or spki[1][0] != 0x03:
        raise FormatError("not a SubjectPublicKeyInfo (SEQUENCE { AlgorithmIdentifier, BIT STRING })")
    alg = der_items(spki[0][1])
    if not alg or alg[0][0] != 0x06:
        raise FormatError("AlgorithmIdentifier without an OID")
    if alg[0][1] != OID_DSA:
        raise FormatError("not a DSA public key (the LYNKS signs DSA/SHA-1); algorithm OID is %s"
                          % alg[0][1].hex())
    if len(alg) != 2 or alg[1][0] != 0x30:
        raise FormatError("DSA key without its p, q, g parameters")
    params = der_items(alg[1][1])
    if len(params) != 3:
        raise FormatError("DSA parameters are not SEQUENCE { p, q, g }")
    p, q, g = (der_integer(i) for i in params)
    bits = spki[1][1]
    if not bits or bits[0] != 0:
        raise FormatError("subjectPublicKey BIT STRING has unused bits")
    tag, yval, end = der_tlv(bits, 1)
    if end != len(bits):
        raise FormatError("trailing bytes after y")
    y = der_integer((tag, yval))
    if not (1 < y < p and 1 < g < p and 1 < q < p):
        raise FormatError("DSA key values out of range")
    return p, q, g, y


def decode_signature(sig, q, fmt="auto"):
    """Return (r, s) from a DER DSS signature or a raw r || s blob."""
    n = (q.bit_length() + 7) // 8
    if fmt == "auto":
        fmt = "der" if sig[:1] == b"\x30" else "raw"
    if fmt == "der":
        try:
            items = der_sequence(sig)
        except FormatError as e:
            raise FormatError("signature is not DER SEQUENCE { INTEGER r, INTEGER s }: %s" % e) from None
        if len(items) != 2:
            raise FormatError("signature SEQUENCE has %d element(s), expected 2" % len(items))
        return der_integer(items[0]), der_integer(items[1])
    if fmt == "raw":
        if len(sig) != 2 * n:
            raise FormatError("raw signature is %d bytes, expected %d (r || s, %d bytes each)"
                              % (len(sig), 2 * n, n))
        return int.from_bytes(sig[:n], "big"), int.from_bytes(sig[n:], "big")
    raise FormatError("unknown signature format %r" % fmt)


# --- DSA ----------------------------------------------------------------------

def dsa_verify(p, q, g, y, digest, r, s):
    """FIPS 186-4 section 4.7: True when (r, s) signs digest under (p, q, g, y)."""
    if not (0 < r < q and 0 < s < q):
        return False
    z = int.from_bytes(digest[: (q.bit_length() + 7) // 8], "big")
    w = pow(s, -1, q)
    u1 = (z * w) % q
    u2 = (r * w) % q
    v = ((pow(g, u1, p) * pow(y, u2, p)) % p) % q
    return v == r


def verify_files(pub_path, msg_path, sig_path, fmt="auto"):
    """True/False for the triple; raises FormatError or OSError on bad input."""
    with open(pub_path, "rb") as f:
        p, q, g, y = load_dsa_public_key(f.read())
    with open(msg_path, "rb") as f:
        digest = hashlib.sha1(f.read()).digest()
    with open(sig_path, "rb") as f:
        r, s = decode_signature(f.read(), q, fmt)
    return dsa_verify(p, q, g, y, digest, r, s)


# --- known-answer vector ------------------------------------------------------
# The key, message digest and signature the card produced for examples/
# (pubkey.pem, msg.txt, sig.bin), so the arithmetic can be checked with no
# files at hand.

KAT = {
    "p": int(
        "9cdd8559d991865802de97f62a2748a1ba94f1422ef5101e8578042de4301c38"
        "f16d9f5bdad14721c4668e7da465cef1030439a5d576f844471569fafea205f9"
        "21bdfbd910d964b607abacf404b79cfbf4be6ee77fb762337d8d7c8f0807cdca"
        "3cd11971291dcd84f7d2c21c9a4888c985b38bd311eec400c4717bc2e517c4c1", 16),
    "q": int("a28904de5c3ded88c4d09a9014069efbe2be9fdd", 16),
    "g": int(
        "3f265a4d198626daad81680de9ef097a492377187c67f20e7de84eca4b95d477"
        "cb3da3999ab357e18ea87bb2dee4566a0ebdffc82c3684be3b5febfd77a421c5"
        "b0845e3c3fa12ca54580f91af3f585df0debc009c884ceee0a02eb373ed5906b"
        "10e2468579f2dd0506ac52e38ae743ae2374991b9765f79f216bdcf675ede27b", 16),
    "y": int(
        "089a782024091e0f483b702c41a7e25e8491f5ddb0ab2481894e860e6e88e4fa"
        "a19ad7be4290ea204a407d3107a1486a063fe79e7845549912acf2462c913545"
        "1527ba0dd688e9990bab60e75a9de323e4a0ad921ed1a7bce64197765189ceff"
        "d609e4e6209de6c7ce47d0e3066b98b687a9525592094f8de5c38870064ee7ca", 16),
    "sha1": bytes.fromhex("a91e306721cbd648888e2c2d5a86d1dc49f5a899"),
    "r": int("602782678279bf57494deb6287184ab3294646e3", 16),
    "s": int("878250af7360b33816b2f2bae3b0d5fbed9c3bb7", 16),
}


def self_test():
    """True when the known-answer vector verifies and tampered copies do not."""
    k = KAT
    good = dsa_verify(k["p"], k["q"], k["g"], k["y"], k["sha1"], k["r"], k["s"])
    flipped = bytearray(k["sha1"])
    flipped[0] ^= 0x01
    bad_digest = dsa_verify(k["p"], k["q"], k["g"], k["y"], bytes(flipped), k["r"], k["s"])
    bad_sig = dsa_verify(k["p"], k["q"], k["g"], k["y"], k["sha1"], k["r"], k["s"] ^ 1)
    return good and not bad_digest and not bad_sig


# --- CLI ----------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(
        prog="verify.py",
        description="Verify a SPYRUS LYNKS DSA-1024/SHA-1 signature off-card, standard library only.",
        epilog="exit status: 0 signature valid, 1 signature invalid, 2 usage or unreadable input",
    )
    ap.add_argument("pubkey", nargs="?",
                    help="DSA public key, PEM or DER SubjectPublicKeyInfo (spy.sh --getkey)")
    ap.add_argument("message", nargs="?", help="the signed file (hashed here with SHA-1)")
    ap.add_argument("signature", nargs="?", help="signature file (spy.sh --sign --binary)")
    ap.add_argument("--format", choices=("auto", "der", "raw"), default="auto",
                    help="signature encoding: DER SEQUENCE{r,s} or raw r||s (default: auto-detect)")
    ap.add_argument("--self-test", action="store_true",
                    help="check the verifier against a known-answer vector from the card and exit")
    ap.add_argument("-q", "--quiet", action="store_true", help="print nothing; exit status only")
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    say = (lambda *a, **k: None) if args.quiet else print

    if args.self_test:
        if self_test():
            say("SELFTEST OK -- known-answer vector verifies, tampered copies do not")
            return 0
        print("SELFTEST FAILED -- DSA arithmetic is wrong on this interpreter", file=sys.stderr)
        return 2

    if not (args.pubkey and args.message and args.signature):
        ap.error("need PUBKEY MESSAGE SIGNATURE (or --self-test)")

    try:
        ok = verify_files(args.pubkey, args.message, args.signature, args.format)
    except OSError as e:
        print("hs4l: cannot read %s: %s" % (e.filename, e.strerror), file=sys.stderr)
        return 2
    except FormatError as e:
        print("hs4l: %s" % e, file=sys.stderr)
        return 2

    if not ok:
        say("INVALID  -- signature does not match (tampered or wrong key)")
        return 1
    say("VALID    -- on-card signature verified against the public key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
