"""Build the 64-byte EEPROM key image (magic/version/CRC + key/nonce/secret)
matching the recovered format in ice40_crypto_ip.md, and emit it as hex.
"""
from pathlib import Path

KEY    = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
NONCE  = bytes.fromhex("101112131415161718191a1b1c1d1e1f")
SECRET = bytes.fromhex("5365637265744b6579313233343536ff")
MAGIC  = b"ASCN"     # recovered cipher hint (spells toward ASCON)
VER    = 0x01

def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc

img = bytearray(64)
img[0:4] = MAGIC
img[4] = VER
# 0x05..0x0D reserved zero
img[0x10:0x20] = KEY
img[0x20:0x30] = NONCE
img[0x30:0x40] = SECRET
crc = crc16_ccitt_false(bytes(img[0x10:0x40]))
img[0x0E] = (crc >> 8) & 0xFF
img[0x0F] = crc & 0xFF

out = Path(__file__).resolve().parents[2] / "pipeline" / "eeprom_image.hex"
out.parent.mkdir(exist_ok=True)
out.write_text("\n".join("%02x" % b for b in img) + "\n", encoding="utf-8")
print("CRC16 =", hex(crc))
print("wrote", out)
print("image:", bytes(img).hex())
