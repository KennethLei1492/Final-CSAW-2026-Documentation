"""Audit retained Bonus B evidence without executing candidate code or simulation.

AI-authored evidence auditor, Phase 05S cycle 003. Reads exact artifacts, checks
their inventories and recomputes recorded bit comparisons and sample-clock rates.
Does not create audio, decode a channel, change RTL, or program any device.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import wave
import zipfile

PACKAGE = Path('experiments/phase05/05bb-bonus-b')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=30)


def bits(path):
    value = ''.join(path.read_text(encoding='ascii').split())
    if set(value) - {'0', '1'}:
        raise ValueError(f'Nonbinary recovered-bit artifact: {path}')
    return value


def audit(root):
    package = root / PACKAGE
    handoff = read(root / 'handoffs/phase-05/bonus-b.json')
    inventory = read(package / 'evidence-inventory.json')
    sources = read(package / 'source-inventory.json')
    channel = read(package / 'evidence/channel-run-1/channel-summary.json')
    experiment = handoff['experiment_commit_sha']
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    source_sha = handoff['source_commit_sha']
    changed = git(root, 'diff', '--name-only', source_sha, experiment).decode('utf-8').splitlines()
    later = git(root, 'diff', '--name-only', experiment, head).decode('utf-8').splitlines()
    ancestry = []
    for before, after in ((source_sha, experiment), (experiment, head)):
        result = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', before, after], timeout=30)
        ancestry.append({'before': before, 'after': after, 'passed': result.returncode == 0})
    archive_path = package / inventory['archive']
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        bad_archive = [name for name, expected in inventory['files'].items()
                       if name not in names or digest(archive.read(name)) != expected]
        unexpected_archive = sorted(names - set(inventory['files']))
    bad_local = [name for name, expected in inventory['files'].items()
                 if not (package / name).is_file() or digest((package / name).read_bytes()) != expected]
    bad_sources = [name for name, expected in sources.items()
                   if not (package / name).is_file() or digest((package / name).read_bytes()) != expected]
    bad_commit_sources = [name for name, expected in sources.items()
                          if digest(git(root, 'show', f'{experiment}:{(PACKAGE / name).as_posix()}')) != expected]
    outside = [name for name in changed if not name.startswith(PACKAGE.as_posix() + '/')]
    report = {
        'schema_version': 1, 'cycle_id': '05S-003', 'iteration': 2,
        'audit_timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'source_worktree': str(root), 'reviewed_tip_sha': head,
        'source_candidate_sha': source_sha, 'experiment_commit_sha': experiment,
        'ancestry': ancestry, 'experiment_changed_paths': len(changed),
        'changes_outside_experiment': outside, 'later_changed_paths': later,
        'archive_sha256': digest(archive_path.read_bytes()),
        'archive_sha256_matches': digest(archive_path.read_bytes()) == inventory['archive_sha256'],
        'archive_entries_checked': len(inventory['files']), 'archive_mismatches': bad_archive,
        'archive_unexpected_entries': unexpected_archive,
        'retained_files_checked': len(inventory['files']), 'retained_file_mismatches': bad_local,
        'source_entries_checked': len(sources), 'source_file_mismatches': bad_sources,
        'immutable_source_blob_mismatches': bad_commit_sources,
        'rates': {}, 'baseline_regressions': {}, 'physical_verified': False,
        'scope': 'Read-only audit of retained evidence. No decoder, HDL simulation or build executed.',
        'limitation': [
            'No physical demonstration or measured hardware throughput.',
            'Rates derive from retained WAV sample counts and simulated sample clocks.',
            'Full long-audio coverage belongs to the unchanged source candidate, not this experiment.',
            'AI transcript sufficiency remains unverified.',
            'No clock-drift, acoustic or sample-rate-conversion robustness claim.',
            'This audit checks recorded data and provenance; it does not independently rerun decoding or simulation.'],
        'recommendation': 'Retain main best; track this separate experiment as conditional simulation-only Bonus B evidence.'}
    for rate in (31250, 15625):
        folder = package / f'evidence/channel-run-1/channel-{rate}'
        original = bits(folder / 'original.bits')
        recovered = bits(folder / 'recovery/recovered.bits')
        with (folder / 'recovery/evaluation/bit-comparison.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        with wave.open(str(folder / 'simulation-filtered-left.wav'), 'rb') as stream:
            frames, hz = stream.getnframes(), stream.getframerate()
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise ValueError('Expected mono PCM16 capture')
            pcm = list(struct.unpack('<' + 'h' * frames, stream.readframes(frames)))
        with (folder / 'serial-output.csv').open(encoding='utf-8', newline='') as stream:
            left = [int(row['value']) for row in csv.DictReader(stream) if row['channel'] == '0']
        equal_length = bool(original) and len(original) == len(recovered)
        incorrect = sum(a != b for a, b in zip(original, recovered)) if equal_length else None
        duration = frames / hz
        ber = incorrect / len(original) if equal_length else None
        net_rate = len(recovered) / duration if equal_length and incorrect == 0 else None
        csv_equal = (''.join(row['original'] for row in rows) == original
                     and ''.join(row['recovered'] for row in rows) == recovered
                     and all(int(row['incorrect']) == (row['original'] != row['recovered']) for row in rows))
        summary = channel[str(rate)]
        summary_equal = (summary['total_compared_bits'] == len(original)
                         and summary['incorrect_recovered_bits'] == incorrect
                         and summary['ber'] == ber
                         and math.isclose(summary['elapsed_transmission_seconds'], duration)
                         and net_rate is not None and math.isclose(summary['net_recovered_payload_bps'], net_rate))
        report['rates'][str(rate)] = {
            'original_bits': len(original), 'recovered_bits': len(recovered),
            'incorrect_bits': incorrect, 'ber': ber, 'bit_comparison_rows': len(rows),
            'bit_csv_matches_artifacts': csv_equal, 'wav_frames': frames, 'sample_rate_hz': hz,
            'elapsed_simulated_seconds': duration, 'net_payload_bps': net_rate,
            'wav_equals_serial_left': pcm == left, 'serial_left_samples': len(left),
            'recorded_summary_matches_recalculation': summary_equal,
            'passed': equal_length and incorrect == 0 and csv_equal and pcm == left and hz == rate and summary_equal}
    for name in ('baseline-build-run1', 'q-directed-run1', 'q-common-run1'):
        folder = package / 'reports' / name
        execution = read(folder / 'report.json')
        comparisons = [read(path) for path in folder.rglob('comparison.json')]
        report['baseline_regressions'][name] = {
            'passed': execution['passed'] and bool(comparisons) and all(item['passed'] for item in comparisons),
            'comparison_files': len(comparisons),
            'compared_words': sum(item['samples_compared'] for item in comparisons),
            'mismatches': sum(item['mismatch_count'] for item in comparisons)}
    bitstream = package / handoff['evidence_paths']['bitstream'].removeprefix(PACKAGE.as_posix() + '/')
    report['bitstream_sha256'] = digest(bitstream.read_bytes())
    report['bitstream_hash_matches'] = report['bitstream_sha256'] == handoff['fpga']['bitstream_sha256']
    report['passed'] = (all(row['passed'] for row in ancestry) and not outside
                        and report['archive_sha256_matches'] and not any((bad_archive, unexpected_archive, bad_local, bad_sources, bad_commit_sources))
                        and all(row['passed'] for row in report['rates'].values())
                        and all(row['passed'] for row in report['baseline_regressions'].values())
                        and report['bitstream_hash_matches'] and not handoff['hardware']['verified'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Phase 05BB worktree root')
    parser.add_argument('--output', type=Path, required=True, help='New JSON receipt; existing files are refused')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        try:
            report = audit(args.source.resolve())
        except Exception as exc:
            report = {'passed': False, 'error': str(exc), 'physical_verified': False}
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps({key: report.get(key) for key in ('passed', 'archive_entries_checked', 'source_entries_checked', 'physical_verified')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
