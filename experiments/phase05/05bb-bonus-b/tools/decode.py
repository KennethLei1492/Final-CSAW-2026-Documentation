"""Output-only PCM16 mono BFSK decoder. No expected payload or input-file access."""
import argparse
import binascii
import hashlib
import json
import struct
import wave
from pathlib import Path

SYNC = format(0xD391C5A7, '032b')
SPS = 32


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        if (w.getnchannels(), w.getsampwidth(), w.getcomptype()) != (1, 2, 'NONE'):
            raise ValueError('Designated filtered-left recording must be mono PCM16')
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())
    return list(struct.unpack('<%dh' % (len(raw)//2), raw)), rate


def decode(path):
    samples, rate = read_wav(path)
    templates = [[1 if (n // h) % 2 == 0 else -1 for n in range(SPS)] for h in (4, 2)]
    candidates = []
    for phase in range(SPS):
        bits, quality = [], []
        for start in range(phase, len(samples)-SPS+1, SPS):
            x = samples[start:start+SPS]
            energy = sum(abs(v) for v in x)
            scores = [abs(sum(a*b for a,b in zip(x,t))) / max(1, energy) for t in templates]
            best = int(scores[1] > scores[0])
            bits.append(str(best) if energy/SPS >= 256 and scores[best] >= .65 else '?')
            quality.append(scores[best])
        stream = ''.join(bits)
        pos = stream.find(SYNC)
        while pos >= 0:
            header = stream[pos+32:pos+40]
            if len(header) == 8 and '?' not in header:
                length = int(header, 2)
                end = pos+40+8*length+16
                packet = stream[pos:end]
                if 0 < length <= 64 and end <= len(stream) and '?' not in packet:
                    body_bits = packet[32:-16]
                    body = int(body_bits, 2).to_bytes(1+length, 'big')
                    crc = int(packet[-16:], 2)
                    candidates.append(dict(start_sample=phase+pos*SPS, end_sample=phase+end*SPS,
                        payload_bits=packet[40:-16], payload_hex=body[1:].hex(),
                        crc_valid=crc == binascii.crc_hqx(body, 0xffff),
                        quality=min(quality[pos:end]), length_bytes=length))
            pos = stream.find(SYNC, pos+1)
    # Choose the highest-quality symbol alignment, independent of expected data.
    frames = []
    for item in sorted(candidates, key=lambda x: (-x['quality'], x['start_sample'])):
        if not any(abs(item['start_sample']-f['start_sample']) < SPS for f in frames):
            frames.append(item)
    frames.sort(key=lambda x: x['start_sample'])
    return dict(source=str(Path(path).resolve()), source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                source_kind='designated_mono_audio_only', sample_rate_hz=rate, samples=len(samples),
                audio_duration_seconds=len(samples)/rate, raw_signaling_bps=rate/SPS,
                frames=frames, crc_valid_frames=sum(f['crc_valid'] for f in frames),
                status='recovered' if any(f['crc_valid'] for f in frames) else 'decoding_failed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('recording', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = decode(args.recording)
    (args.output/'decode.json').write_text(json.dumps(result, indent=2)+'\n')
    (args.output/'recovered.bits').write_text(''.join(f['payload_bits']+'\n' for f in result['frames']))
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'recovered' else 2


if __name__ == '__main__':
    raise SystemExit(main())
