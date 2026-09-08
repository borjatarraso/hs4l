#!/usr/bin/env python3
"""hs4l -- verify a SPYRUS LYNKS signature off-card.

The card signs DSA-1024 / SHA-1 (FIPS 186-2) on slots 1..8 and ECDSA P-256 /
SHA-256 on slot 9. OpenSSL 3 REFUSES to verify SHA-1+DSA at policy level
("invalid digest") -- that is a deprecation policy, not a signature failure,
so it cannot be the judge. This script does the DSA and ECDSA arithmetic
itself (FIPS 186-4 sections 4.7 and 6.4.2) with nothing but the Python
standard library, so it runs wherever Python 3.9+ does and carries no
deprecation policy of its own.

    python3 scripts/verify.py examples/pubkey.pem examples/msg.txt examples/sig.bin
    python3 scripts/verify.py examples/pubkey-slot9.pem examples/tbs-slot9.der examples/sig-slot9.bin
    python3 scripts/verify.py --self-test

The public key is read as PEM or DER SubjectPublicKeyInfo (what `--getkey`
prints); its algorithm OID decides everything else. A DSA key means the
message is hashed with SHA-1, an EC key (prime256v1 only) means SHA-256 --
that is what the card does, and there is no switch to make the verifier say
otherwise. The signature is read either DER-encoded, SEQUENCE { INTEGER r,
INTEGER s } (what `--sign --binary` prints), or as raw r || s (2 x 20 bytes
for DSA, 2 x 32 for P-256); the encoding is auto-detected unless --format
says otherwise.

Exit 0 = valid, 1 = invalid/tampered, 2 = usage or unreadable/malformed input.
"""
import argparse
import base64
import hashlib
import re
import sys

OID_DSA = bytes.fromhex("2a8648ce380401")        # 1.2.840.10040.4.1 (id-dsa)
OID_EC_PUBKEY = bytes.fromhex("2a8648ce3d0201")  # 1.2.840.10045.2.1 (id-ecPublicKey)
OID_P256 = bytes.fromhex("2a8648ce3d030107")     # 1.2.840.10045.3.1.7 (prime256v1)


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


def load_public_key(data):
    """Parse a SubjectPublicKeyInfo (PEM or DER).

    Returns ("dsa", p, q, g, y) for an id-dsa key (slots 1..8) or
    ("ec", Qx, Qy) for a prime256v1 id-ecPublicKey key (slot 9).
    """
    spki = der_sequence(pem_to_der(data))
    if len(spki) != 2 or spki[0][0] != 0x30 or spki[1][0] != 0x03:
        raise FormatError("not a SubjectPublicKeyInfo (SEQUENCE { AlgorithmIdentifier, BIT STRING })")
    alg = der_items(spki[0][1])
    if not alg or alg[0][0] != 0x06:
        raise FormatError("AlgorithmIdentifier without an OID")
    bits = spki[1][1]
    if not bits or bits[0] != 0:
        raise FormatError("subjectPublicKey BIT STRING has unused bits")
    if alg[0][1] == OID_DSA:
        if len(alg) != 2 or alg[1][0] != 0x30:
            raise FormatError("DSA key without its p, q, g parameters")
        params = der_items(alg[1][1])
        if len(params) != 3:
            raise FormatError("DSA parameters are not SEQUENCE { p, q, g }")
        p, q, g = (der_integer(i) for i in params)
        tag, yval, end = der_tlv(bits, 1)
        if end != len(bits):
            raise FormatError("trailing bytes after y")
        y = der_integer((tag, yval))
        if not (1 < y < p and 1 < g < p and 1 < q < p):
            raise FormatError("DSA key values out of range")
        return "dsa", p, q, g, y
    if alg[0][1] == OID_EC_PUBKEY:
        if len(alg) != 2 or alg[1][0] != 0x06:
            raise FormatError("EC key without a named curve")
        if alg[1][1] != OID_P256:
            raise FormatError("EC key is not prime256v1 (the LYNKS slot 9 is P-256); curve OID is %s"
                              % alg[1][1].hex())
        point = bits[1:]
        if len(point) != 65 or point[0] != 0x04:
            raise FormatError("EC public key is not a 65-byte uncompressed point (04 || X || Y)")
        qx = int.from_bytes(point[1:33], "big")
        qy = int.from_bytes(point[33:], "big")
        if not ec_on_curve(qx, qy):
            raise FormatError("EC public key is not a point on P-256")
        return "ec", qx, qy
    raise FormatError("not a DSA or EC public key (the LYNKS signs DSA/SHA-1 on slots 1..8, "
                      "ECDSA P-256/SHA-256 on slot 9); algorithm OID is %s" % alg[0][1].hex())


def load_dsa_public_key(data):
    """Parse a SubjectPublicKeyInfo (PEM or DER) into (p, q, g, y); DSA only."""
    key = load_public_key(data)
    if key[0] != "dsa":
        raise FormatError("not a DSA public key")
    return key[1:]


def decode_signature(sig, q, fmt="auto"):
    """Return (r, s) from a DER DSS signature or a raw r || s blob.

    q is the subgroup order (DSA q or the P-256 order n); it sizes raw r and s.
    """
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


# --- ECDSA on P-256 (secp256r1, FIPS 186-4 D.1.2.3) ----------------------------
# Jacobian coordinates, plain double-and-add. This is a verifier: there is no
# private key here, so constant time is not a requirement.

P256_P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
P256_A = P256_P - 3
P256_B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
P256_GX = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
P256_GY = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
P256_N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551


def ec_on_curve(x, y):
    """True when (x, y) satisfies y^2 = x^3 - 3x + b over GF(p)."""
    if not (0 <= x < P256_P and 0 <= y < P256_P):
        return False
    return (y * y - (x * x * x + P256_A * x + P256_B)) % P256_P == 0


def _jac_double(X1, Y1, Z1):
    if Y1 == 0 or Z1 == 0:
        return 0, 1, 0
    p = P256_P
    S = (4 * X1 * Y1 * Y1) % p
    Z1sq = (Z1 * Z1) % p
    M = (3 * (X1 - Z1sq) * (X1 + Z1sq)) % p          # 3X^2 + aZ^4 with a = -3
    X3 = (M * M - 2 * S) % p
    Y3 = (M * (S - X3) - 8 * Y1 * Y1 * Y1 * Y1) % p
    Z3 = (2 * Y1 * Z1) % p
    return X3, Y3, Z3


def _jac_add(X1, Y1, Z1, X2, Y2, Z2):
    if Z1 == 0:
        return X2, Y2, Z2
    if Z2 == 0:
        return X1, Y1, Z1
    p = P256_P
    Z1sq, Z2sq = (Z1 * Z1) % p, (Z2 * Z2) % p
    U1, U2 = (X1 * Z2sq) % p, (X2 * Z1sq) % p
    S1, S2 = (Y1 * Z2sq * Z2) % p, (Y2 * Z1sq * Z1) % p
    if U1 == U2:
        if S1 != S2:
            return 0, 1, 0
        return _jac_double(X1, Y1, Z1)
    H = (U2 - U1) % p
    R = (S2 - S1) % p
    Hsq = (H * H) % p
    Hcu = (Hsq * H) % p
    U1Hsq = (U1 * Hsq) % p
    X3 = (R * R - Hcu - 2 * U1Hsq) % p
    Y3 = (R * (U1Hsq - X3) - S1 * Hcu) % p
    Z3 = (H * Z1 * Z2) % p
    return X3, Y3, Z3


def _jac_mul(k, X, Y):
    """k * (X, Y) in Jacobian coordinates; (0, 1, 0) is the point at infinity."""
    RX, RY, RZ = 0, 1, 0
    QX, QY, QZ = X, Y, 1
    while k:
        if k & 1:
            RX, RY, RZ = _jac_add(RX, RY, RZ, QX, QY, QZ)
        QX, QY, QZ = _jac_double(QX, QY, QZ)
        k >>= 1
    return RX, RY, RZ


def ecdsa_verify(qx, qy, digest, r, s):
    """FIPS 186-4 section 6.4.2: True when (r, s) signs digest under (qx, qy) on P-256."""
    n = P256_N
    if not (0 < r < n and 0 < s < n):
        return False
    if not ec_on_curve(qx, qy):
        return False
    z = int.from_bytes(digest[:32], "big")
    w = pow(s, -1, n)
    u1 = (z * w) % n
    u2 = (r * w) % n
    AX, AY, AZ = _jac_mul(u1, P256_GX, P256_GY)
    BX, BY, BZ = _jac_mul(u2, qx, qy)
    RX, RY, RZ = _jac_add(AX, AY, AZ, BX, BY, BZ)
    if RZ == 0:
        return False
    zinv = pow(RZ, -1, P256_P)
    x = (RX * zinv * zinv) % P256_P
    return x % n == r


# --- files --------------------------------------------------------------------

def verify_files(pub_path, msg_path, sig_path, fmt="auto"):
    """(ok, kind) for the triple; raises FormatError or OSError on bad input.

    kind is "dsa" (message hashed with SHA-1) or "ec" (SHA-256): the key's
    algorithm decides, because that is how the card decides.
    """
    with open(pub_path, "rb") as f:
        key = load_public_key(f.read())
    with open(msg_path, "rb") as f:
        message = f.read()
    with open(sig_path, "rb") as f:
        sig = f.read()
    if key[0] == "dsa":
        _, p, q, g, y = key
        r, s = decode_signature(sig, q, fmt)
        return dsa_verify(p, q, g, y, hashlib.sha1(message).digest(), r, s), "dsa"
    _, qx, qy = key
    r, s = decode_signature(sig, P256_N, fmt)
    return ecdsa_verify(qx, qy, hashlib.sha256(message).digest(), r, s), "ec"


# --- known-answer vectors -----------------------------------------------------
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

# Slot 9 (P-256): the card's own signature over the 374-byte TBSCertificate of
# the self-signed root it issued on 2026-09-08 (examples/pubkey-slot9.pem,
# tbs-slot9.der, sig-slot9.bin). The digest is SHA-256: that is the only hash
# the signature verifies under, so it is what the card computes.

KAT_EC = {
    "qx": int("c936958f05d5cf50dfe07af1681bbf32c8bbe65f1974de3d553d957da5badc41", 16),
    "qy": int("c3c48a30d08d561d990966fd524e5ecd384275f5bddf90d1cd5e77256ba3319c", 16),
    "sha256": bytes.fromhex("607083fbeff88c431ef5ca03addfe6fe1d6caf8536ee7a3f4d3a9d3b18e57e1c"),
    "r": int("4a921e65c0bc3f5a74e6a6b9fc0fa291cf693d342ab946f5cd91391c3a23f116", 16),
    "s": int("a1d72c855350b09efad32a4b071deed9b13208434169f7b29c5f430f10eb9ed6", 16),
}


def self_test():
    """True when both known-answer vectors verify and tampered copies do not."""
    k = KAT
    good = dsa_verify(k["p"], k["q"], k["g"], k["y"], k["sha1"], k["r"], k["s"])
    flipped = bytearray(k["sha1"])
    flipped[0] ^= 0x01
    bad_digest = dsa_verify(k["p"], k["q"], k["g"], k["y"], bytes(flipped), k["r"], k["s"])
    bad_sig = dsa_verify(k["p"], k["q"], k["g"], k["y"], k["sha1"], k["r"], k["s"] ^ 1)

    e = KAT_EC
    good_ec = ecdsa_verify(e["qx"], e["qy"], e["sha256"], e["r"], e["s"])
    flipped = bytearray(e["sha256"])
    flipped[0] ^= 0x01
    bad_digest_ec = ecdsa_verify(e["qx"], e["qy"], bytes(flipped), e["r"], e["s"])
    bad_sig_ec = ecdsa_verify(e["qx"], e["qy"], e["sha256"], e["r"], e["s"] ^ 1)

    return (good and not bad_digest and not bad_sig
            and good_ec and not bad_digest_ec and not bad_sig_ec)


# --- CLI ----------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(
        prog="verify.py",
        description="Verify a SPYRUS LYNKS signature off-card, standard library only: "
                    "DSA-1024/SHA-1 (slots 1..8) or ECDSA P-256/SHA-256 (slot 9), "
                    "chosen by the public key's algorithm.",
        epilog="exit status: 0 signature valid, 1 signature invalid, 2 usage or unreadable input",
    )
    ap.add_argument("pubkey", nargs="?",
                    help="DSA or EC public key, PEM or DER SubjectPublicKeyInfo (spy.sh --getkey)")
    ap.add_argument("message", nargs="?",
                    help="the signed file (hashed here with SHA-1 for a DSA key, SHA-256 for an EC key)")
    ap.add_argument("signature", nargs="?", help="signature file (spy.sh --sign --binary)")
    ap.add_argument("--format", choices=("auto", "der", "raw"), default="auto",
                    help="signature encoding: DER SEQUENCE{r,s} or raw r||s (default: auto-detect)")
    ap.add_argument("--self-test", action="store_true",
                    help="check the verifier against the DSA and P-256 known-answer vectors from the card and exit")
    ap.add_argument("-q", "--quiet", action="store_true", help="print nothing; exit status only")
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    say = (lambda *a, **k: None) if args.quiet else print

    if args.self_test:
        if self_test():
            say("SELFTEST OK -- DSA and P-256 known-answer vectors verify, tampered copies do not")
            return 0
        print("SELFTEST FAILED -- signature arithmetic is wrong on this interpreter", file=sys.stderr)
        return 2

    if not (args.pubkey and args.message and args.signature):
        ap.error("need PUBKEY MESSAGE SIGNATURE (or --self-test)")

    try:
        ok, kind = verify_files(args.pubkey, args.message, args.signature, args.format)
    except OSError as e:
        print("hs4l: cannot read %s: %s" % (e.filename, e.strerror), file=sys.stderr)
        return 2
    except FormatError as e:
        print("hs4l: %s" % e, file=sys.stderr)
        return 2

    scheme = "SHA-1/DSA" if kind == "dsa" else "SHA-256/ECDSA P-256"
    if not ok:
        say("INVALID  -- %s signature does not match (tampered or wrong key)" % scheme)
        return 1
    say("VALID    -- on-card %s signature verified against the public key" % scheme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
