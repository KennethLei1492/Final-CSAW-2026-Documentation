#!/usr/bin/env python3
"""Expected-output generator for the 05A trigger/payload test cases.

The FIR calculation is the verified Phase 3 model.  This adapter adds only the
candidate's specified behavior: after the first three consecutive left samples
equal the trigger words, flip the filtered result LSB for that and every later
logical sample.  The right-channel echo and two-frame I2S latency are retained.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

TRIGGER = (0x5A3C, 0xC3A5, 0x96E1)
HALF = 1 << 14
MIN16, MAX16 = -(1 << 15), (1 << 15) - 1


def load_coefficients(path: Path) -> list[int]:
    return [int(v) for v in json.loads(path.read_text())['coeffs_q15']]


def sat16(value: int) -> int:
    return MAX16 if value > MAX16 else MIN16 if value < MIN16 else value


def fir(samples: list[int], coefficients: list[int]) -> list[int]:
    result = []
    for n in range(len(samples)):
        acc = sum(coefficients[k] * samples[n - k]
                  for k in range(min(n + 1, len(coefficients))))
        result.append(sat16((acc + HALF) >> 15))
    return result


def read_left(path: Path) -> list[int]:
    rows = []
    with path.open(newline='') as stream:
        for row in csv.reader(stream):
            if not row or not row[-1].lstrip('+-').isdigit():
                continue
            rows.append([int(cell) for cell in row])
    if not rows:
        return []
    if len(rows[0]) >= 3:
        return [row[2] for row in rows if row[1] == 0]
    return [row[1] for row in rows]


def first_trigger(samples: list[int]) -> int | None:
    for start in range(max(0, len(samples) - len(TRIGGER) + 1)):
        if tuple(value & 0xFFFF for value in samples[start:start + len(TRIGGER)]) == TRIGGER:
            return start + len(TRIGGER) - 1
    return None


def write_output(path: Path, samples: list[int], filtered: list[int], trigger_index: int | None,
                 latency: int) -> None:
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['index', 'channel', 'value'])
        for frame in range(len(samples)):
            logical = frame - latency
            if logical < 0:
                left = right = 0
            else:
                left = filtered[logical]
                right = samples[logical]
                if trigger_index is not None and logical >= trigger_index:
                    left = left ^ 1
            writer.writerow([2 * frame, 0, left])
            writer.writerow([2 * frame + 1, 1, right])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--coeffs', required=True)
    parser.add_argument('--latency', type=int, default=2)
    args = parser.parse_args()
    samples = read_left(Path(args.input))
    coefficients = load_coefficients(Path(args.coeffs))
    trigger_index = first_trigger(samples)
    write_output(Path(args.output), samples, fir(samples, coefficients), trigger_index, args.latency)
    print('candidate_reference: frames=%d trigger_index=%s latency=%d' %
          (len(samples), trigger_index, args.latency))


if __name__ == '__main__':
    main()
