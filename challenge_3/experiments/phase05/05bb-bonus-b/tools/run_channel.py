"""Reproduce HDL serial-output channel evidence. All WAVs here are SIMULATION ONLY."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys

HERE=Path(__file__).resolve().parent
EXP=HERE.parent
ROOT=EXP.parents[2]
sys.path.insert(0,str(ROOT/'infrastructure'))
from toolchain import Toolchain, sha256
from prepare import prepare, wav
from decode import decode, read_wav
from evaluate import evaluate


def save(path, obj):
    Path(path).write_text(json.dumps(obj,indent=2)+'\n')


def capture(tc, out, rate, source=False):
    out.mkdir(parents=True)
    samples,packet=prepare(out,rate)
    hdl=ROOT/'infrastructure/hdl'
    rtl=ROOT/'experiments/phase05/05b-astra/rtl' if source else EXP/'rtl'
    sources=[hdl/n for n in ('i2s_driver.sv','i2s_monitor.sv','tb_i2s.sv')]
    sources += [rtl/'fir_audio_top.v',rtl/'phase4_dut.sv']
    if not source: sources += [rtl/'audio_lab_tx.v']
    binary=out/'simulation.vvp'
    cmd=[tc.find('iverilog'),'-g2012','-Wall','-s','tb_i2s','-o',binary,
         '-Ptb_i2s.SLOT_BITS=16',f'-Ptb_i2s.HALF_PERIOD_NS={500 if rate==31250 else 1000}']+sources
    tc.run(cmd,out,out/'compile.log',120)
    tc.run([tc.find('vvp'),binary,f'+VECTORS={out / "vectors.hex"}',
            f'+CAPTURE={out / "serial-output.csv"}',f'+WORDS={len(samples)*2}'],out,out/'simulation.log',300)
    with (out/'serial-output.csv').open() as f: rows=list(csv.DictReader(f))
    assert len(rows)==len(samples)*2
    assert all(int(r['index'])==i and int(r['channel'])==i%2 for i,r in enumerate(rows))
    left=[int(r['value']) for r in rows[::2]]
    right=[int(r['value']) for r in rows[1::2]]
    assert right==[0,0]+samples[:-2], 'right echo/latency failure'
    wav(out/'simulation-filtered-left.wav',left,rate)
    wav(out/'simulation-right-echo.wav',right,rate)
    save(out/'capture-provenance.json',dict(hardware=False,measurement='I2S_SD_OUT sampled by existing Phase4 serial monitor',
        selected_channel='left channel 0 only',latency_frames=2,rate_hz=rate,
        bclk_hz=32*rate,ice_clk_hz=10000000,right_echo_mismatches=0,
        sources_sha256={str(p.relative_to(ROOT)):sha256(p) for p in sources},
        capture_sha256=sha256(out/'simulation-filtered-left.wav')))
    return left,right,samples


def recover(tc, wavpath, target, expected, expect_success):
    tc.run([sys.executable,HERE/'decode.py',wavpath,'--output',target],target.parent,
           target.parent/(target.name+'.log'),120) if expect_success else None
    if not expect_success:
        target.mkdir()
        result=decode(wavpath)
        save(target/'decode.json',result)
        (target/'recovered.bits').write_text(''.join(f['payload_bits']+'\n' for f in result['frames']))
    result=evaluate(expected,target/'decode.json',target/'evaluation')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True,type=Path)
    p.add_argument('--suite',required=True); a=p.parse_args()
    out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    tc=Toolchain(a.suite); save(out/'toolchain.json',tc.doctor())
    results={}
    for rate in (31250,15625):
        case=out/f'channel-{rate}'
        left,right,samples=capture(tc,case,rate)
        results[str(rate)]=recover(tc,case/'simulation-filtered-left.wav',case/'recovery',case/'original.bits',True)
        assert results[str(rate)]['bit_exact']
        for label,source in [('echo',case/'simulation-right-echo.wav'),('input',case/'input.wav')]:
            r=recover(tc,source,case/(label+'-negative'),case/'original.bits',False)
            assert r['ber'] is None and r['net_recovered_payload_bps']==0
        # Corrupt exactly one payload symbol while retaining frame alignment.
        decoded=json.loads((case/'recovery/decode.json').read_text())
        start=decoded['frames'][0]['start_sample']+40*32
        damaged=left.copy()
        bit=decoded['frames'][0]['payload_bits'][0]
        half=2 if bit=='0' else 4
        damaged[start:start+32]=[4096 if (n//half)%2==0 else -4096 for n in range(32)]
        wav(case/'software-corrupted-output.wav',damaged,rate)
        r=recover(tc,case/'software-corrupted-output.wav',case/'corruption-control',case/'original.bits',True)
        assert r['incorrect_recovered_bits']==1 and r['failed_frames']==1 and not r['bit_exact']
        results[f'corruption-{rate}']=r
        # Remove final frame: must never claim BER=0 on failed alignment.
        wav(case/'software-truncated-output.wav',left[:decoded['frames'][-1]['start_sample']+32],rate)
        r=recover(tc,case/'software-truncated-output.wav',case/'truncation-control',case/'original.bits',True)
        assert r['ber'] is None and not r['bit_exact']
        results[f'truncation-{rate}']=r
    source=out/'source-candidate-control'
    capture(tc,source,31250,True)
    r=recover(tc,source/'simulation-filtered-left.wav',source/'recovery',source/'original.bits',False)
    assert r['ber'] is None and r['net_recovered_payload_bps']==0
    results['source_candidate_control']=r
    # No trigger means silence cannot be interpreted as a successful packet.
    wav(out/'silence.wav',[0]*6000,31250)
    assert decode(out/'silence.wav')['status']=='decoding_failed'
    results['status']='passed'; results['hardware_verified']=False
    results['classification']='PARTIAL DEMONSTRATION'
    save(out/'channel-summary.json',results)
    save(out/'evidence-sha256.json',{str(f.relative_to(out)):sha256(f) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='evidence-sha256.json'})
    print(json.dumps(results,indent=2))


if __name__=='__main__': main()
