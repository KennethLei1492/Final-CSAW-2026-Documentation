"""Ascon-AEAD128 reference (NIST SP 800-232), used to (a) generate golden vectors
for the Verilog testbench and (b) model Trojan payloads at the algorithm level.

Constants per the ASCON guide reference source (IV 0x00001000808c0001, pa=12,
pb=8, rotation pairs and round constants as documented).
"""
from __future__ import annotations

IV = 0x00001000808c0001
RC = [0xf0, 0xe1, 0xd2, 0xc3, 0xb4, 0xa5, 0x96, 0x87, 0x78, 0x69, 0x5a, 0x4b]
ROT = [(19, 28), (61, 39), (1, 6), (10, 17), (7, 41)]
MASK = (1 << 64) - 1


def rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & MASK


def permutation(S, rounds):
    x = list(S)
    start = 12 - rounds
    for r in range(start, 12):
        # addition of round constant into x2
        x[2] ^= RC[r]
        # substitution layer (bit-sliced 5-bit S-box)
        x[0] ^= x[4]; x[4] ^= x[3]; x[2] ^= x[1]
        t = [(~x[i]) & MASK & x[(i + 1) % 5] for i in range(5)]
        for i in range(5):
            x[i] ^= t[(i + 1) % 5]
        x[1] ^= x[0]; x[0] ^= x[4]; x[3] ^= x[2]; x[2] ^= MASK
        # linear diffusion
        for i in range(5):
            a, b = ROT[i]
            x[i] ^= rotr(x[i], a) ^ rotr(x[i], b)
    return x


def _b2w(b):
    return int.from_bytes(b, "big")


def _w2b(w):
    return w.to_bytes(8, "big")


def _init_state(key, nonce):
    k0, k1 = _b2w(key[:8]), _b2w(key[8:])
    n0, n1 = _b2w(nonce[:8]), _b2w(nonce[8:])
    S = [IV, k0, k1, n0, n1]
    S = permutation(S, 12)
    S[3] ^= k0; S[4] ^= k1
    return S, k0, k1


def _absorb_ad(S, ad):
    if ad:
        padded = ad + b"\x01" + b"\x00" * ((16 - (len(ad) + 1) % 16) % 16)
        for i in range(0, len(padded), 16):
            S[0] ^= _b2w(padded[i:i + 8]); S[1] ^= _b2w(padded[i + 8:i + 16])
            S = permutation(S, 8)
    S[4] ^= (1 << 63)  # domain separation (NIST SP 800-232)
    return S


def encrypt(key, nonce, ad, pt):
    S, k0, k1 = _init_state(key, nonce)
    S = _absorb_ad(S, ad)
    ct = bytearray()
    padded = pt + b"\x01" + b"\x00" * ((16 - (len(pt) + 1) % 16) % 16)
    nblk = len(padded) // 16
    for b in range(nblk):
        i = b * 16
        S[0] ^= _b2w(padded[i:i + 8]); S[1] ^= _b2w(padded[i + 8:i + 16])
        ct += _w2b(S[0]) + _w2b(S[1])
        if b < nblk - 1:
            S = permutation(S, 8)
    ct = bytes(ct[:len(pt)])
    # finalization
    S[2] ^= k0; S[3] ^= k1
    S = permutation(S, 12)
    S[3] ^= k0; S[4] ^= k1
    tag = _w2b(S[3]) + _w2b(S[4])
    return ct, tag


def decrypt(key, nonce, ad, ct, tag):
    S, k0, k1 = _init_state(key, nonce)
    S = _absorb_ad(S, ad)
    pt = bytearray()
    full = len(ct) // 16
    for b in range(full):
        i = b * 16
        c0 = _b2w(ct[i:i + 8]); c1 = _b2w(ct[i + 8:i + 16])
        pt += _w2b(S[0] ^ c0) + _w2b(S[1] ^ c1)
        S[0] = c0; S[1] = c1
        S = permutation(S, 8)
    rem = len(ct) - full * 16
    if True:
        i = full * 16
        clast = ct[i:] + b"\x00" * (16 - rem)
        c0 = _b2w(clast[:8]); c1 = _b2w(clast[8:])
        p0 = S[0] ^ c0; p1 = S[1] ^ c1
        pblk = (_w2b(p0) + _w2b(p1))
        pt += pblk[:rem]
        # overwrite rate with ciphertext bits + padding bit on plaintext tail
        ptail = bytearray(pblk[:rem]) + bytearray(b"\x01") + bytearray(15 - rem)
        S[0] ^= (_b2w(bytes(ptail[:8])))
        S[1] ^= (_b2w(bytes(ptail[8:])))
    S[2] ^= k0; S[3] ^= k1
    S = permutation(S, 12)
    S[3] ^= k0; S[4] ^= k1
    calc = _w2b(S[3]) + _w2b(S[4])
    return bytes(pt[:len(ct)]) if calc == tag else None


if __name__ == "__main__":
    import os
    key = bytes(range(16)); nonce = bytes(range(16))
    # roundtrip + tamper checks mirroring fpga_selftest.py
    ad = b"hackster-selftest"; msg = b"The quick brown fox jumps over the lazy dog."
    ct, tag = encrypt(key, nonce, ad, msg)
    assert len(ct) == len(msg) and ct != msg and len(tag) == 16
    assert decrypt(key, nonce, ad, ct, tag) == msg, "roundtrip failed"
    bad = bytearray(ct); bad[0] ^= 1
    assert decrypt(key, nonce, ad, bytes(bad), tag) is None, "tamper ct not rejected"
    btag = bytearray(tag); btag[0] ^= 1
    assert decrypt(key, nonce, ad, ct, bytes(btag)) is None, "tamper tag not rejected"
    assert decrypt(key, nonce, b"wrong-ad", ct, tag) is None, "wrong AD not rejected"
    ct2, tag2 = encrypt(key, nonce, ad, msg)
    assert ct2 == ct and tag2 == tag, "not deterministic"
    ect, etag = encrypt(key, nonce, b"", b"")
    assert decrypt(key, nonce, b"", ect, etag) == b"", "empty failed"
    # randomized roundtrip
    for _ in range(200):
        k = os.urandom(16); n = os.urandom(16)
        a = os.urandom(os.urandom(1)[0] % 40); m = os.urandom(os.urandom(1)[0] % 80)
        c, t = encrypt(k, n, a, m)
        assert decrypt(k, n, a, c, t) == m
    print("Ascon-AEAD128 reference: ALL self-consistency + self-test-equivalent checks PASS")
    print("ct =", ct.hex())
    print("tag=", tag.hex())
