"""Check an isolated pyserial host environment; never open a physical serial port.

Use a fresh --output directory for every invocation. A pinned local wheel is
installed only beneath that directory, with no index or dependency resolution.
All command results and failures are retained. loop:// is software-only evidence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

PY_SERIAL_SHA256 = 'c4451db6ba391ca6ca299fb3ec7bae67a5c55dde170964c7a14ceefec02f2cf0'
BASE_PROBE = """import importlib.util, json, sys
spec = importlib.util.find_spec('serial')
print(json.dumps({'python': sys.executable, 'serial_available': spec is not None,
                  'serial_origin': spec.origin if spec else None}))
"""
ISOLATED_PROBE = """import hashlib, json, pathlib, sys
site = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(site))
import serial
from serial.tools import list_ports
origin = pathlib.Path(serial.__file__).resolve()
if not origin.is_relative_to(site):
    raise RuntimeError('serial import escaped isolated target')
payload = bytes(range(256)) + b'CSAW-05S-host-readiness\\x00\\xff'
with serial.serial_for_url('loop://', timeout=2, write_timeout=2) as port:
    sent = port.write(payload)
    received = port.read(len(payload))
    surplus = port.in_waiting
if sent != len(payload) or received != payload or surplus != 0:
    raise RuntimeError('software serial loopback mismatch')
# comports enumerates metadata only; no physical port is opened.
ports = [{'device': p.device, 'description': p.description, 'hwid': p.hwid,
          'vid': p.vid, 'pid': p.pid} for p in list_ports.comports()]
print(json.dumps({'serial_version': serial.__version__, 'serial_origin': str(origin),
    'isolated_import': True, 'loopback_url': 'loop://',
    'sent_bytes': sent, 'received_bytes': len(received),
    'payload_sha256': hashlib.sha256(payload).hexdigest(),
    'received_sha256': hashlib.sha256(received).hexdigest(),
    'byte_mismatches': 0, 'ports_enumerated': ports,
    'physical_ports_opened': [], 'physical_board_verified': False}))
"""


def evaluate(wheel, output, expected_sha256):
    output = output.resolve()
    # Exclusive creation prevents accidental reuse or destruction of evidence.
    output.mkdir(parents=True, exist_ok=False)
    commands = []
    result = {
        'schema_version': 1,
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'passed': False,
        'scope': 'Isolated host dependency, software serial loopback, read-only port inventory',
        'physical_board_verified': False,
        'physical_ports_opened': [],
        'global_packages_modified': False,
        'python': sys.executable,
        'output_directory': str(output),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'wheel': {'path': str(wheel.resolve()), 'expected_sha256': expected_sha256},
        'commands': commands,
    }

    def command(argv, timeout=30):
        started = time.monotonic()
        record = {'argv': argv, 'timeout_seconds': timeout}
        commands.append(record)
        try:
            completed = subprocess.run(argv, capture_output=True, text=True,
                                       encoding='utf-8', errors='replace', timeout=timeout)
            record.update(exit_code=completed.returncode, stdout=completed.stdout,
                          stderr=completed.stderr)
            if completed.returncode:
                raise RuntimeError('command failed with exit code ' + str(completed.returncode))
            return completed.stdout
        except subprocess.TimeoutExpired as exc:
            record.update(timed_out=True,
                          stdout=(exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else exc.stdout,
                          stderr=(exc.stderr or b'').decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else exc.stderr)
            raise
        finally:
            record['elapsed_seconds'] = time.monotonic() - started

    try:
        actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
        result['wheel']['actual_sha256'] = actual
        if actual != expected_sha256:
            raise ValueError('wheel SHA256 mismatch; installation was not attempted')
        result['base_environment'] = json.loads(command([sys.executable, '-I', '-c', BASE_PROBE]))
        wheel_dir = output / 'wheel'
        wheel_dir.mkdir()
        retained_wheel = wheel_dir / wheel.name
        shutil.copyfile(wheel, retained_wheel)
        if hashlib.sha256(retained_wheel.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('retained wheel SHA256 mismatch; installation was not attempted')
        result['wheel']['retained_path'] = str(retained_wheel)
        site = output / 'site'
        command([sys.executable, '-I', '-m', 'pip', 'install', '--no-index', '--no-deps',
                 '--no-compile', '--disable-pip-version-check', '--target', str(site),
                 str(retained_wheel)], timeout=60)
        result['isolated_environment'] = json.loads(command(
            [sys.executable, '-I', '-c', ISOLATED_PROBE, str(site)]))
        result['passed'] = True
        result['decision'] = 'Host pyserial import and software loopback pass; no board claim'
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        result['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        with (output / 'readiness.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-sha256', default=PY_SERIAL_SHA256)
    args = parser.parse_args()
    outcome = evaluate(args.wheel, args.output, args.expected_sha256)
    print(json.dumps({'passed': outcome['passed'],
                      'receipt': str(args.output / 'readiness.json'),
                      'error': outcome.get('error'), 'physical_board_verified': False}))
    raise SystemExit(0 if outcome['passed'] else 1)
