"""Generate declared synthetic ROM packet and trigger-only host stimulus."""
import argparse
import binascii
import json
import struct
import wave
from pathlib import Path

MESSAGE = b'CSAW26-BONUS-B'
MAGIC = [0x1357,0xECA8,0x2468,0xDB97,0x369C,0xC963,0x55AA,0xAA55]
MAGIC = [v if v < 32768 else v-65536 for v in MAGIC]


def wav(path, samples, rate):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack('<%dh'%len(samples),*samples))


def prepare(out, rate=31250, repeats=3):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    body=bytes([len(MESSAGE)])+MESSAGE
    packet=bytes.fromhex('D391C5A7')+body+binascii.crc_hqx(body,0xffff).to_bytes(2,'big')
    bits=''.join(format(x,'08b') for x in MESSAGE)
    (out/'original.bits').write_text((bits+'\n')*repeats)
    (out/'message.txt').write_text(MESSAGE.decode()+'\n')
    (out/'packet.hex').write_text(packet.hex()+'\n')
    (out/'protocol.json').write_text(json.dumps(dict(message_ascii=MESSAGE.decode(),packet_hex=packet.hex(),
        packet_bits=len(packet)*8,samples_per_bit=32,crc='CRC16-CCITT init FFFF poly1021 length+payload',
        trigger_signed=MAGIC,sample_rate_hz=rate,repeats=repeats),indent=2)+'\n')
    samples=[0]*128
    for _ in range(repeats):
        samples+=MAGIC+[0]*(len(packet)*8*32+128)
    samples += [0]*128
    wav(out/'input.wav', samples, rate)
    (out/'vectors.hex').write_text(''.join(f'{v&65535:04x}\n{v&65535:04x}\n' for v in samples))
    return samples,packet


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True)
    p.add_argument('--rate',type=int,default=31250); p.add_argument('--repeats',type=int,default=3)
    a=p.parse_args(); prepare(a.output,a.rate,a.repeats)
