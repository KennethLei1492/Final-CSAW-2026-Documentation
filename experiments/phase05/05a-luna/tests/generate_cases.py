#!/usr/bin/env python3
"""Generate deterministic 05A inactive, negative, boundary, and activation vectors."""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGER = [0x5A3C, 0xC3A5, 0x96E1]
TRIGGER_SIGNED = [value if value < 0x8000 else value - 0x10000 for value in TRIGGER]


def write(path: Path, samples: list[int]) -> None:
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['index', 'channel', 'value'])
        for index, sample in enumerate(samples):
            writer.writerow([2 * index, 0, sample])
            writer.writerow([2 * index + 1, 1, sample])


def convert_canonical() -> None:
    source = ROOT / 'reference_io.in.csv'
    samples = []
    with source.open(newline='') as stream:
        for row in csv.reader(stream):
            if row and row[-1].lstrip('+-').isdigit():
                samples.append(int(row[-1]))
    write(ROOT / 'canonical-inactive.csv', samples)


def main() -> None:
    convert_canonical()
    inactive = [0, 1, -1, 32767, -32768, 0x1234, -0x2345, 0x4000, -0x4000]
    inactive += [((index * 7919 + 12345) % 65536) - 32768 for index in range(71)]
    write(ROOT / 'inactive.csv', inactive)

    near_miss = [0, 0, 17, TRIGGER_SIGNED[0], TRIGGER_SIGNED[1], TRIGGER_SIGNED[2] + 1,
                 TRIGGER_SIGNED[0], 9]
    near_miss += [(-index * 31337) % 65536 - 32768 for index in range(36)]
    write(ROOT / 'negative-near-miss.csv', near_miss)

    boundary = TRIGGER_SIGNED + [32767, -32768, 32767, -32768, 0, 1, -1, 32767, -32768]
    write(ROOT / 'boundary-early-trigger.csv', boundary)

    active = [0, 100, -100, 2345, -2345, 7] + TRIGGER_SIGNED
    active += [32767, -32768, 16384, -16384, 8192, -8192, 1, -1]
    active += [((index * 1543 + 2718) % 65536) - 32768 for index in range(48)]
    write(ROOT / 'activation.csv', active)

    rng = random.Random(0x05A)
    random_inactive = [rng.randint(-32768, 32767) for _ in range(256)]
    write(ROOT / 'random-inactive.csv', random_inactive)


if __name__ == '__main__':
    main()
