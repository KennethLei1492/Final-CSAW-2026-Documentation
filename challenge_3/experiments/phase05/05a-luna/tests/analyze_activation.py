#!/usr/bin/env python3
"""Audit captured baseline/candidate activation and inactive traces."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_capture(path: Path) -> list[dict[str, int]]:
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows or list(rows[0]) != ['index', 'channel', 'value']:
        raise ValueError(f'invalid capture header: {path}')
    parsed = [{key: int(row[key]) for key in ('index', 'channel', 'value')} for row in rows]
    for index, row in enumerate(parsed):
        if row['index'] != index or row['channel'] != index % 2:
            raise ValueError(f'nonsequential capture row {index}: {row}')
    return parsed


def compare_pair(baseline: Path, candidate: Path) -> tuple[list[dict], int | None]:
    base, cand = read_capture(baseline), read_capture(candidate)
    if len(base) != len(cand):
        raise ValueError('capture lengths differ')
    changes = []
    for expected, actual in zip(base, cand):
        if expected['channel'] != actual['channel']:
            raise ValueError(f'channel changed at row {expected["index"]}')
        if expected['value'] != actual['value']:
            changes.append({
                'index': actual['index'],
                'channel': actual['channel'],
                'baseline': expected['value'],
                'candidate': actual['value'],
                'xor16': (expected['value'] & 0xffff) ^ (actual['value'] & 0xffff),
            })
    return changes, changes[0]['index'] if changes else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    activation_changes, first_change = compare_pair(
        args.baseline / 'activation' / 'actual.csv',
        args.candidate / 'activation' / 'actual.csv')
    boundary_changes, boundary_first = compare_pair(
        args.baseline / 'boundary-early-trigger' / 'actual.csv',
        args.candidate / 'boundary-early-trigger' / 'actual.csv')
    inactive_changes, inactive_first = compare_pair(
        args.baseline / 'negative-near-miss' / 'actual.csv',
        args.candidate / 'negative-near-miss' / 'actual.csv')
    inactive_cases = ['canonical-inactive', 'inactive', 'negative-near-miss',
                      'random-inactive', 'provided-audio']
    inactive_case_results = {}
    for case in inactive_cases:
        changes, _ = compare_pair(args.baseline / case / 'actual.csv',
                                  args.candidate / case / 'actual.csv')
        inactive_case_results[case] = {'changed_rows': len(changes), 'passed': not changes}

    expected_first = 2 * (8 + 2)  # trigger completes at logical frame 8; latency is 2 frames
    active_left = [row for row in activation_changes if row['channel'] == 0]
    active_right = [row for row in activation_changes if row['channel'] == 1]
    bad_active = [row for row in active_left if row['xor16'] != 1]
    report = {
        'passed': bool(activation_changes)
            and first_change == expected_first
            and not active_right
            and not bad_active
            and boundary_first == 2 * (2 + 2)
            and not inactive_changes
            and all(item['passed'] for item in inactive_case_results.values()),
        'baseline_equivalence': {
            'all_inactive_cases_passed': all(item['passed'] for item in inactive_case_results.values()),
            'cases': inactive_case_results,
        },
        'activation': {
            'first_changed_row': first_change,
            'expected_first_changed_row': expected_first,
            'changed_rows': len(activation_changes),
            'left_changed_rows': len(active_left),
            'right_changed_rows': len(active_right),
            'bad_xor_rows': bad_active,
            'first_rows': activation_changes[:10],
        },
        'boundary_early_trigger': {
            'first_changed_row': boundary_first,
            'expected_first_changed_row': 8,
            'changed_rows': len(boundary_changes),
        },
        'negative_near_miss': {
            'first_changed_row': inactive_first,
            'changed_rows': len(inactive_changes),
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
