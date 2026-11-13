"""Read-only evidence integrity and declared-result checks; not a new HDL run."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

EXP=Path(__file__).resolve().parent.parent
ROOT=EXP.parents[2]


def main():
    sha=lambda b:hashlib.sha256(b).hexdigest()
    source=json.loads((EXP/'source-inventory.json').read_text())
    for name,digest in source.items(): assert sha((EXP/name).read_bytes())==digest,name
    inventory=json.loads((EXP/'evidence-inventory.json').read_text())
    archive=EXP/inventory['archive']
    assert sha(archive.read_bytes())==inventory['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        for name,digest in inventory['files'].items(): assert sha(z.read(name))==digest,name
        channel=json.loads(z.read('evidence/channel-run-1/channel-summary.json'))
        for rate in ('31250','15625'):
            assert channel[rate]['bit_exact'] and channel[rate]['total_compared_bits']==336
            assert channel['corruption-'+rate]['incorrect_recovered_bits']==1
            assert channel['truncation-'+rate]['ber'] is None
        assert channel['source_candidate_control']['recovered_frames']==0
        rtl=json.loads(z.read('reports/rtl-verification-summary.json'))
        assert rtl['build']['passed'] and rtl['original_candidate_regression']['mismatches']==0
        assert rtl['q_directed']['mismatches']==0 and rtl['phase2_golden']['mismatches']==0
        bitstream=z.read('reports/baseline-build-run1/fpga-build/bitstream.bin')
        assert sha(bitstream)==rtl['build']['bitstream_sha256']
    sourcepath='experiments/phase05/05b-astra/rtl/fir_audio_top.v'
    original=subprocess.check_output(['git','show','fd0ca7f6bce1d30bb1b1e6ce43603b4c7d51e5b6:'+sourcepath],cwd=ROOT)
    assert (ROOT/sourcepath).read_text().replace('\r\n','\n')==original.decode().replace('\r\n','\n')
    print(json.dumps(dict(passed=True,source_files=len(source),archived_evidence_files=len(inventory['files']),
        source_candidate_unchanged=True,hardware_verified=False,classification='PARTIAL DEMONSTRATION')))


if __name__=='__main__': main()
