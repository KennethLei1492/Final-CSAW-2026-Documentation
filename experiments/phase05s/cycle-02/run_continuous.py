"""Check uninterrupted supplied audio against the unchanged Phase 3 golden model.

AI-authored evaluation code, Codex, Phase 05S cycle 02. No implementation edits.
Archive the exact requested commit; never use the candidate's working directory.
The existing testbench supports MAX_WORDS; override it only for this long run.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sha = subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', args.ref+'^{commit}'], text=True).strip()
    receipt = {'source_commit_sha': sha, 'passed': False, 'hardware_verified': False,
               'hypothesis': 'The full recording remains bit-exact without intermediate reset.',
               'implementation_changed': False}
    try:
        archive = out/'source.tar'
        subprocess.run(['git', '-C', str(args.repo), 'archive', '--format=tar', '--output='+str(archive), sha], check=True)
        root = out/'source'; root.mkdir()
        subprocess.run(['tar', '-xf', str(archive), '-C', str(root)], check=True)
        sys.path.insert(0, str(root/'infrastructure'))
        from toolchain import Toolchain, sha256
        from results import compare
        from vectors import write_vectors
        tc = Toolchain(args.suite)
        package = root/'experiments/phase05/05b-astra'
        tc.run([sys.executable, root/'experiments/quality/verify_inventory.py', '--manifest',
                package/'manifest.json', '--output', out/'inventory.json'], root, out/'inventory.log')
        spec = importlib.util.spec_from_file_location('full_audio', package/'tests/prepare_full_audio.py')
        audio = importlib.util.module_from_spec(spec); spec.loader.exec_module(audio)
        samples, metadata, audio_hash = audio.read_audio()
        hits = audio.trigger_completions(samples)
        if hits:
            raise ValueError('Normal audio contains trigger; baseline-only assumption invalid')
        samples += [0] * audio.FLUSH_FRAMES
        words = 2*len(samples)
        audio.write_csv_pair(out/'input.csv', out/'expected.csv', samples,
                             audio.baseline.load_coeffs(str(package/'tests/reference/coeffs.json')))
        vectors, _ = write_vectors(out, [v for sample in samples for v in (sample, sample)], 16)
        sources = [root/'infrastructure/hdl'/name for name in ('i2s_driver.sv','i2s_monitor.sv','tb_i2s.sv')]
        sources += [package/'rtl/fir_audio_top.v', package/'rtl/phase4_dut.sv']
        params = {'SAMPLE_BITS':16, 'SLOT_BITS':16, 'MSB_DELAY':1, 'LEFT_LEVEL':0,
                  'HALF_PERIOD_NS':500, 'CLOCK_HALF_NS':50, 'RESET_CYCLES':10, 'MAX_WORDS':words}
        binary = out/'simulation.vvp'
        argv = [tc.find('iverilog'), '-g2012', '-Wall', '-s', 'tb_i2s', '-o', binary]
        argv += [f'-Ptb_i2s.{key}={value}' for key,value in params.items()]
        tc.run(argv+sources, out, out/'compile.log')
        receipt.update(source_audio=metadata, audio_sha256=audio_hash, reset_count=1,
                       flush_frames=audio.FLUSH_FRAMES, trigger_hits=hits, parameters=params,
                       input_sha256={str(p.relative_to(root)):sha256(p) for p in sources},
                       runner_sha256=sha256(Path(__file__)),
                       tool_sha256={name:sha256(tc.find(name)) for name in ('iverilog','vvp')})
        (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        print(f'Running one continuous simulation: {words} words from {sha}', flush=True)
        log = tc.run([tc.find('vvp'), binary, f'+VECTORS={vectors}', f'+CAPTURE={out/"actual.csv"}',
                      f'+WORDS={words}'], out, out/'simulation.log', 1200)
        if f'PHASE4_SIM_PASS words={words}' not in log:
            raise RuntimeError('Simulation completion marker missing')
        result = compare(out/'expected.csv', out/'actual.csv', 0, 0, 16)
        (out/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
        receipt.update(comparison=result, passed=result['passed'],
                       artifact_sha256={p.name:sha256(p) for p in out.iterdir()
                           if p.is_file() and p.name not in ('receipt.json','source.tar')})
    except Exception as exc:
        receipt.update(passed=False, error=str(exc))
        raise
    finally:
        (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed':receipt['passed'], 'comparison':receipt['comparison']}))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
