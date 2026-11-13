"""Decoder generality and failure checks using independent synthetic packets."""
import binascii
import random
import tempfile
import unittest
from pathlib import Path
from decode import decode
from prepare import wav


class RecoveryTests(unittest.TestCase):
    def test_crc_reference(self):
        self.assertEqual(binascii.crc_hqx(b'123456789',0xffff),0x29b1)

    def test_unknown_payload_offset_noise_and_inversion(self):
        rng=random.Random(20261113)
        for message,offset,polarity in [(b'\x00\xff\x81',13,1),(bytes(range(16)),29,-1)]:
            body=bytes([len(message)])+message
            packet=bytes.fromhex('d391c5a7')+body+binascii.crc_hqx(body,0xffff).to_bytes(2,'big')
            signal=[0]*offset
            for byte in packet:
                for bit in format(byte,'08b'):
                    half=2 if bit=='1' else 4
                    signal += [polarity*(3000 if (n//half)%2==0 else -3000)+rng.randint(-150,150) for n in range(32)]
            signal += [0]*64
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'unseen.wav'; wav(path,signal,31250)
                result=decode(path)
            self.assertEqual(len(result['frames']),1)
            self.assertTrue(result['frames'][0]['crc_valid'])
            self.assertEqual(result['frames'][0]['payload_hex'],message.hex())

    def test_noise_is_not_recovery(self):
        rng=random.Random(9)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'noise.wav'; wav(path,[rng.randint(-100,100) for _ in range(6000)],31250)
            self.assertEqual(decode(path)['status'],'decoding_failed')


if __name__=='__main__': unittest.main(verbosity=2)
