"""Audit retained Phase 8 execution receipts without rerunning HDL or packaging."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); source=a.source.resolve()
    head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    for name in ('reproduce.py','release_package.py','release_transcripts.py','handoffs/phase-08/reproduction.json'):
        committed=subprocess.check_output(['git','-C',str(source),'show',head+':'+name])
        if committed.replace(b'\r\n',b'\n')!=(source/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Source differs from immutable commit: '+name)
    sys.path.insert(0,str(source))
    from release_package import selected_evidence
    config=source/'handoffs/phase-08/reproduction.json'
    output=source/'.state/phase-08-cycle-02'
    evidence,attempt=selected_evidence(json.loads(config.read_text()),output,config)
    counts={name:len(json.loads((attempt/name).read_text())['outputs'])
            for name in ('quality-suite.json','repeat-build.json','continuous-audio.json')}
    result={'passed':True,'source_commit_sha':head,'evidence_type':'retained_execution_receipts_reaudited',
            'new_hdl_executions_this_audit':0,'selected_validation':evidence,
            'checkpoint_files_verified':len(evidence['checkpoint_sha256']),
            'output_files_verified':counts,'receipt_source':str(output/'selected-validation.json'),
            'selected_receipt_sha256':hashlib.sha256((output/'selected-validation.json').read_bytes()).hexdigest(),
            'caveats':['No physical board evidence.',
                       'Release selection input is cycle002; source SHA matches cycle004.',
                       'Release candidate model labels are configured labels, not verified runtime attribution.',
                       'A different toolchain passed simulations/timing but failed historical bitstream identity; preserve that failed comparison.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps({'passed':True,'checkpoints':len(evidence['checkpoint_sha256']),'outputs':sum(counts.values()),'simulations_retained':evidence['simulations']}))
