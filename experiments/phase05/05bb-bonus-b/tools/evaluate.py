"""Post-recovery comparison; expected bits are never supplied to the decoder."""
import argparse
import csv
import json
from pathlib import Path


def evaluate(expected_path, decoded_path, output, elapsed=None):
    expected = [s.strip() for s in Path(expected_path).read_text().splitlines() if s.strip()]
    result = json.loads(Path(decoded_path).read_text())
    frames = result['frames']
    # No data-dependent bit shifting. Frame-count/length mismatch makes aggregate BER undefined.
    aligned = len(expected) == len(frames) and all(len(e) == len(f['payload_bits']) for e,f in zip(expected,frames))
    errors = compared = good = 0
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output/'bit-comparison.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['frame','bit','original','recovered','incorrect'])
        if aligned:
            for i,(e,frame) in enumerate(zip(expected, frames)):
                r = frame['payload_bits']
                for j,(a,b) in enumerate(zip(e,r)):
                    wrong = int(a != b); errors += wrong; compared += 1
                    writer.writerow([i,j,a,b,wrong])
                if frame['crc_valid']:
                    good += len(r)
    duration = elapsed if elapsed is not None else result['audio_duration_seconds']
    if duration <= 0: raise ValueError('Elapsed duration must be positive')
    report = dict(alignment_valid=aligned, incorrect_recovered_bits=errors if aligned else None,
        total_compared_bits=compared, expected_payload_bits=sum(map(len,expected)),
        ber=errors/compared if aligned and compared else None,
        attempted_frames=len(expected), recovered_frames=len(frames), crc_valid_frames=result['crc_valid_frames'],
        failed_frames=max(0,len(expected)-result['crc_valid_frames']),
        correctly_framed_recovered_payload_bits=good,
        elapsed_transmission_seconds=duration, duration_basis='measured_wall_clock' if elapsed is not None else 'entire_capture_samples/sample_rate',
        net_recovered_payload_bps=good/duration, raw_signaling_bps=result['raw_signaling_bps'],
        bit_exact=aligned and errors == 0 and result['crc_valid_frames'] == len(expected),
        methodology='Whole capture includes trigger, sync, length, CRC, guards and failed attempts. No payload-based alignment; count/length failure gives null BER and zero net accepted throughput.')
    (output/'evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('original'); p.add_argument('decoded'); p.add_argument('--output', required=True)
    p.add_argument('--elapsed-seconds', type=float)
    a=p.parse_args(); r=evaluate(a.original,a.decoded,a.output,a.elapsed_seconds)
    print(json.dumps(r,indent=2)); raise SystemExit(0 if r['bit_exact'] else 2)
