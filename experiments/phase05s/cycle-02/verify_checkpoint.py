"""Verify selection identity and retained cycle evidence before handoff."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
def read(relative): return json.loads((ROOT/relative).read_text(encoding='utf-8-sig'))
def main():
    selection=read('handoffs/phase-05/selection.json')
    current=read('handoffs/quality-review/current-best.json')
    history=read('handoffs/phase-05/selection-history.json')
    cycle=ROOT/'handoffs/phase-05/cycles/05S-002'
    receipt=json.loads((cycle/'continuous-receipt.json').read_text())
    best=selection['current_best_known_sha']
    assert best==selection['previous_best_known_sha']==current['current_best_known_sha']
    assert best==current['current_best_known_commit_sha']==history['events'][-1]['selected_sha']
    assert best==receipt['source_commit_sha']
    subprocess.run(['git','-C',str(ROOT),'cat-file','-e',best+'^{commit}'],check=True)
    assert receipt['passed'] and receipt['comparison']['mismatch_count']==0
    assert receipt['comparison']['samples_compared']==480260
    assert current['hardware_testing_status'].startswith('not_run')
    assert selection['last_evaluation_cycle_id']==current['last_evaluation_cycle_id']=='05S-002'
    runner=ROOT/'experiments/phase05s/cycle-02/run_continuous.py'
    assert hashlib.sha256(runner.read_bytes()).hexdigest()==receipt['runner_sha256']
    audit=json.loads((cycle/'Q-receipt-audit.json').read_text())
    assert audit['passed'] and audit['checked']==230 and all(row['passed'] for row in audit['results'])
    assert json.loads((cycle/'continuous-inventory.json').read_text())['passed']
    assert json.loads((cycle/'resume-validation.json').read_text())['passed']
    print(json.dumps({'passed':True,'cycle':'05S-002','best_sha':best,
                      'new_continuous_words':480260,'physical_verified':False}))

if __name__=='__main__': main()
