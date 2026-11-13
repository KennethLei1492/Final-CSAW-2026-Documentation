#!/usr/bin/env python3
"""Generate the 05B/Astra trigger as a 16 kHz PCM16 mono WAV (finding §34).

The selected trojan arms on eight exact consecutive left-channel samples:
    7F00 8101 5A3C A5C3 6D92 926D C33C 3CC3   (MSB-first 16-bit words)
read as signed int16. This script writes those words (optionally wrapped in
leading silence to arm from a clean state and trailing silence to flush the
128-frame payload + 2-frame latency) so the trigger can be streamed through the
board with the provided host tool. Stdlib only (no numpy).

Usage:
    python -I make_trigger_wav.py --out trigger.wav
    python -I make_trigger_wav.py --out triggered_stream.wav --lead 160 --trail 160
"""
import argparse
import struct
import wave

# Trigger words (hex) in order. Each pair is the bitwise complement of its
# partner (0x5A3C ^ 0xFFFF == 0xA5C3, etc.) -- see finding §5 (patterned magic).
MAGIC_HEX = [0x7F00, 0x8101, 0x5A3C, 0xA5C3, 0x6D92, 0x926D, 0xC33C, 0x3CC3]


def to_signed16(u: int) -> int:
    return u - 0x10000 if u & 0x8000 else u


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rate", type=int, default=16000, help="sample rate (Hz)")
    ap.add_argument("--lead", type=int, default=64, help="leading silence frames")
    ap.add_argument("--trail", type=int, default=160,
                    help="trailing silence frames (>=130 flushes payload+latency)")
    ap.add_argument("--repeat", type=int, default=1, help="times to repeat the trigger")
    args = ap.parse_args()

    magic = [to_signed16(u) for u in MAGIC_HEX]
    samples = [0] * args.lead
    for _ in range(args.repeat):
        samples += magic
    samples += [0] * args.trail

    with wave.open(args.out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(args.rate)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    print("trigger words (hex -> signed int16):")
    for u, s in zip(MAGIC_HEX, magic):
        print(f"  0x{u:04X} -> {s:7d}")
    print(f"wrote {args.out}: {len(samples)} frames @ {args.rate} Hz "
          f"(lead {args.lead}, {args.repeat}x8 trigger, trail {args.trail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
