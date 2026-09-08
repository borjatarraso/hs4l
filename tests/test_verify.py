"""Unit tests for scripts/verify.py -- standard library only.

    python3 -m unittest discover -s tests -v        (or: make test)

The DSA arithmetic is exercised on a fixed 1024/160 key built in-test from
the FIPS 186-2 parameters the card generated for examples/pubkey.pem; the
signing side lives here, in a few lines, because verify.py only verifies.
The CLI is exercised through subprocess for its exit-status contract.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import verify  # noqa: E402

VERIFY = os.path.join(ROOT, "scripts", "verify.py")
EXAMPLES = os.path.join(ROOT, "examples")

P, Q, G = verify.KAT["p"], verify.KAT["q"], verify.KAT["g"]
# Deterministic private key and per-message nonces: fixed digests reduced
# mod q. Not secret, not for use on anything real.
X = int.from_bytes(hashlib.sha256(b"hs4l test private key").digest(), "big") % Q
Y = pow(G, X, P)


def nonce(msg):
    k = int.from_bytes(hashlib.sha256(b"hs4l test nonce " + msg).digest(), "big") % Q
    return k or 1


def dsa_sign(digest, x, k):
    """FIPS 186-4 section 4.6, textbook, for test vectors only."""
    z = int.from_bytes(digest[:20], "big")
    r = pow(G, k, P) % Q
    s = (pow(k, -1, Q) * (z + x * r)) % Q
    assert r and s
    return r, s


# --- tiny DER writer so the tests can build keys and signatures -----------------

def tlv(tag, body):
    n = len(body)
    if n < 0x80:
        return bytes([tag, n]) + body
    lb = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(lb)]) + lb + body


def integer(n):
    b = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
    if b[0] & 0x80:
        b = b"\x00" + b
    return tlv(0x02, b)


def sig_der(r, s):
    return tlv(0x30, integer(r) + integer(s))


def sig_raw(r, s):
    return r.to_bytes(20, "big") + s.to_bytes(20, "big")


def spki_der(p, q, g, y, oid=verify.OID_DSA):
    alg = tlv(0x30, tlv(0x06, oid) + tlv(0x30, integer(p) + integer(q) + integer(g)))
    return tlv(0x30, alg + tlv(0x03, b"\x00" + integer(y)))


def pem(der, label="PUBLIC KEY"):
    import base64
    b64 = base64.encodebytes(der).replace(b"\n", b"")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return b"-----BEGIN %s-----\n%s\n-----END %s-----\n" % (
        label.encode(), b"\n".join(lines), label.encode())


def sha1(msg):
    return hashlib.sha1(msg).digest()


class KnownAnswer(unittest.TestCase):
    def test_card_vector_verifies(self):
        k = verify.KAT
        self.assertTrue(verify.dsa_verify(k["p"], k["q"], k["g"], k["y"], k["sha1"], k["r"], k["s"]))

    def test_self_test_passes(self):
        self.assertTrue(verify.self_test())

    def test_kat_matches_example_files(self):
        with open(os.path.join(EXAMPLES, "pubkey.pem"), "rb") as f:
            self.assertEqual(verify.load_dsa_public_key(f.read()), (P, Q, G, verify.KAT["y"]))
        with open(os.path.join(EXAMPLES, "msg.txt"), "rb") as f:
            self.assertEqual(sha1(f.read()), verify.KAT["sha1"])
        with open(os.path.join(EXAMPLES, "sig.bin"), "rb") as f:
            self.assertEqual(verify.decode_signature(f.read(), Q), (verify.KAT["r"], verify.KAT["s"]))


class Arithmetic(unittest.TestCase):
    def test_roundtrip_on_fixed_key(self):
        for msg in (b"", b"hello from the LYNKS", b"\x00" * 100, bytes(range(256))):
            r, s = dsa_sign(sha1(msg), X, nonce(msg))
            self.assertTrue(verify.dsa_verify(P, Q, G, Y, sha1(msg), r, s), msg)

    def test_tampered_message_rejected(self):
        msg = b"pay 10"
        r, s = dsa_sign(sha1(msg), X, nonce(msg))
        self.assertFalse(verify.dsa_verify(P, Q, G, Y, sha1(b"pay 100"), r, s))

    def test_tampered_signature_rejected(self):
        msg = b"x"
        r, s = dsa_sign(sha1(msg), X, nonce(msg))
        self.assertFalse(verify.dsa_verify(P, Q, G, Y, sha1(msg), r ^ 1, s))
        self.assertFalse(verify.dsa_verify(P, Q, G, Y, sha1(msg), r, s ^ 1))

    def test_wrong_key_rejected(self):
        msg = b"x"
        r, s = dsa_sign(sha1(msg), X, nonce(msg))
        self.assertFalse(verify.dsa_verify(P, Q, G, pow(G, X + 1, P), sha1(msg), r, s))

    def test_out_of_range_r_s_rejected(self):
        msg = b"x"
        r, s = dsa_sign(sha1(msg), X, nonce(msg))
        for bad_r, bad_s in ((0, s), (Q, s), (r, 0), (r, Q), (r + Q, s)):
            self.assertFalse(verify.dsa_verify(P, Q, G, Y, sha1(msg), bad_r, bad_s))

    def test_high_bit_s_needs_der_pad(self):
        # The card's own sig.bin has s >= 2^159 (DER pads it to 21 bytes);
        # both encodings must decode to the same integers.
        s = verify.KAT["s"]
        self.assertTrue(s >> 159 & 1)
        der = sig_der(verify.KAT["r"], s)
        self.assertEqual(len(der), 47)
        self.assertEqual(verify.decode_signature(der, Q), verify.decode_signature(sig_raw(verify.KAT["r"], s), Q))


class Decoding(unittest.TestCase):
    def test_signature_auto_detect(self):
        r, s = dsa_sign(sha1(b"m"), X, nonce(b"m"))
        self.assertEqual(verify.decode_signature(sig_der(r, s), Q), (r, s))
        self.assertEqual(verify.decode_signature(sig_raw(r, s), Q), (r, s))
        self.assertEqual(verify.decode_signature(sig_der(r, s), Q, "der"), (r, s))
        self.assertEqual(verify.decode_signature(sig_raw(r, s), Q, "raw"), (r, s))

    def test_signature_format_mismatch(self):
        r, s = dsa_sign(sha1(b"m"), X, nonce(b"m"))
        with self.assertRaises(verify.FormatError):
            verify.decode_signature(sig_der(r, s), Q, "raw")
        with self.assertRaises(verify.FormatError):
            verify.decode_signature(sig_raw(r, s), Q, "der")
        with self.assertRaises(verify.FormatError):
            verify.decode_signature(sig_der(r, s) + b"\x00", Q)   # trailing byte
        with self.assertRaises(verify.FormatError):
            verify.decode_signature(sig_der(r, s)[:-1], Q)        # truncated
        with self.assertRaises(verify.FormatError):
            verify.decode_signature(sig_raw(r, s)[:-1], Q)        # 39 bytes

    def test_key_pem_and_der(self):
        der = spki_der(P, Q, G, Y)
        self.assertEqual(verify.load_dsa_public_key(der), (P, Q, G, Y))
        self.assertEqual(verify.load_dsa_public_key(pem(der)), (P, Q, G, Y))
        self.assertEqual(verify.load_dsa_public_key(pem(der).replace(b"\n", b"\r\n")), (P, Q, G, Y))

    def test_key_rejections(self):
        der = spki_der(P, Q, G, Y)
        rsa_oid = bytes.fromhex("2a864886f70d010101")
        cases = {
            "rsa oid": spki_der(P, Q, G, Y, oid=rsa_oid),
            "wrong pem label": pem(der, "DSA PARAMETERS"),
            "no end line": pem(der).split(b"-----END")[0],
            "trailing": der + b"\x00",
            "truncated": der[:-3],
            "not a sequence": b"\x02\x01\x05",
            "y out of range": spki_der(P, Q, G, P + 1),
        }
        for name, data in cases.items():
            with self.subTest(name):
                with self.assertRaises(verify.FormatError):
                    verify.load_dsa_public_key(data)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, VERIFY, *args], capture_output=True, text=True)

    def test_examples_valid(self):
        r = self.run_cli(os.path.join(EXAMPLES, "pubkey.pem"), os.path.join(EXAMPLES, "msg.txt"),
                         os.path.join(EXAMPLES, "sig.bin"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("VALID", r.stdout)

    def test_wrong_key_exits_1(self):
        r = self.run_cli(os.path.join(EXAMPLES, "pubkey-slot2.pem"), os.path.join(EXAMPLES, "msg.txt"),
                         os.path.join(EXAMPLES, "sig.bin"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("INVALID", r.stdout)

    def test_missing_file_exits_2(self):
        r = self.run_cli(os.path.join(EXAMPLES, "no-such-key.pem"), os.path.join(EXAMPLES, "msg.txt"),
                         os.path.join(EXAMPLES, "sig.bin"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot read", r.stderr)

    def test_bad_key_exits_2(self):
        r = self.run_cli(os.path.join(EXAMPLES, "dsaparam.pem.rejected"), os.path.join(EXAMPLES, "msg.txt"),
                         os.path.join(EXAMPLES, "sig.bin"))
        self.assertEqual(r.returncode, 2)

    def test_usage_exits_2(self):
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli(os.path.join(EXAMPLES, "pubkey.pem")).returncode, 2)

    def test_help_and_self_test(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        r = self.run_cli("--self-test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SELFTEST OK", r.stdout)
        self.assertEqual(self.run_cli("-q", "--self-test").stdout, "")

    def test_raw_signature_file(self):
        with open(os.path.join(EXAMPLES, "msg.txt"), "rb") as f:
            msg = f.read()
        r, s = dsa_sign(sha1(msg), X, nonce(msg))
        with tempfile.TemporaryDirectory() as d:
            key, sig = os.path.join(d, "k.pem"), os.path.join(d, "s.raw")
            with open(key, "wb") as f:
                f.write(pem(spki_der(P, Q, G, Y)))
            with open(sig, "wb") as f:
                f.write(sig_raw(r, s))
            self.assertEqual(self.run_cli(key, os.path.join(EXAMPLES, "msg.txt"), sig).returncode, 0)
            self.assertEqual(self.run_cli("--format", "der", key, os.path.join(EXAMPLES, "msg.txt"), sig).returncode, 2)
            with open(sig, "wb") as f:
                f.write(sig_raw(r, s ^ 1))
            self.assertEqual(self.run_cli(key, os.path.join(EXAMPLES, "msg.txt"), sig).returncode, 1)


if __name__ == "__main__":
    unittest.main()
