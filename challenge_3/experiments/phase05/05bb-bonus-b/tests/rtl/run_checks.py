"""Repeat baseline/build, Q regressions and synthetic-transmitter boundary tests.

Run from any cwd; --output must be a new directory. No source is overwritten.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
PACKAGE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from infrastructure.toolchain import Toolchain
from experiments.quality.prepare import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tc = Toolchain(args.suite)

    def run(log, *argv):
        tc.run([sys.executable, *argv], ROOT, out/log, timeout=900)

    run('baseline-command.log', 'infrastructure/run.py', '--suite', str(args.suite),
        'validate', '--manifest', str(PACKAGE/'baseline-build-manifest.json'),
        '--output', str(out/'baseline-build'))
    run('recover-command.log', 'infrastructure/prepare_recovered.py', '--source-root', str(ROOT),
        '--ref', '1befb30e99a506698c45d4ca9394a3c7ec95c966', '--output', str(out/'recovered'))
    prepare(out/'q-vectors', out/'recovered')
    for name in ('common', 'directed'):
        path = out/'q-vectors'/f'{name}.json'
        config = json.loads(path.read_text())
        config['name'] = '05bb-'+name
        config['simulation']['sources'] = [str(PACKAGE/'rtl'/f) for f in
            ('fir_audio_top.v', 'audio_lab_tx.v', 'phase4_dut.sv')]
        path.write_text(json.dumps(config, indent=2)+'\n')
        run(name+'-command.log', 'infrastructure/run.py', '--suite', str(args.suite),
            'sim', '--manifest', str(path), '--output', str(out/name))
    run('directed-audit-command.log', 'experiments/quality/audit_directed.py',
        '--run', str(out/'directed'), '--specs', str(out/'q-vectors/directed-specs.json'),
        '--output', str(out/'directed-audit.json'))
    tc.run([tc.find('iverilog'), '-g2012', '-s', 'tb_audio_lab_tx', '-o', out/'lab.vvp',
            PACKAGE/'rtl/audio_lab_tx.v', PACKAGE/'tests/rtl/tb_audio_lab_tx.sv'],
           ROOT, out/'lab-compile.log')
    tc.run([tc.find('vvp'), out/'lab.vvp'], ROOT, out/'lab-simulation.log')
    print('PASS: baseline/build, common, directed, and lab boundary tests')


if __name__ == '__main__':
    main()
