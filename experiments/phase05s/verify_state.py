"""Validate a resumable checkpoint without selecting or promoting an implementation.

Checks metadata consistency, retained history and file identity. It does not run
HDL or turn a stored verification assertion into physical evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def require(condition, message):
    if not condition: raise ValueError(message)


def digest(path):
    raw=Path(path).read_bytes()
    if Path(path).suffix in {'.json','.md','.py'}: raw=raw.replace(b'\r\n',b'\n')
    return hashlib.sha256(raw).hexdigest()


def validate_metadata(selection, current, history):
    cid=selection['last_evaluation_cycle_id']
    require(cid==f"05S-{selection['cycle_number']:03d}", 'cycle number/id mismatch')
    require(current['phase']=='05S' and current['cycle']==selection['cycle_number'], 'stale current-best cycle')
    require(current['last_evaluation_cycle_id']==cid, 'stale current-best cycle id')
    best=selection['current_best_known_sha']
    winner=selection['winner']
    require(winner['current_best_known_commit_sha']==best, 'winner SHA disagreement')
    original_id=selection['original_candidate_id']
    require(original_id==winner['candidate_id']==current['original_candidate_id']==current['selected_candidate_id'],
            'candidate ID disagreement')
    require(selection['original_candidate_shas'][original_id]==selection['original_candidate_commit_sha']
            ==winner['immutable_package_commit_sha'], 'original inventory disagreement')
    require(best==current['current_best_known_sha']==current['current_best_known_commit_sha'], 'best SHA disagreement')
    require(selection['previous_best_known_sha']==current['previous_best_known_sha'], 'previous best SHA disagreement')
    require(selection['original_candidate_commit_sha']==current['original_candidate_commit_sha'], 'original source disagreement')
    require(selection['common_baseline_commit_sha']==current['baseline_commit_sha'], 'baseline disagreement')
    require(history['events'][-1]['id']==cid and history['events'][-1]['selected_sha']==best, 'latest history event mismatch')
    require(current['regression_status']=='passed', 'best regression is not verified')
    require(current['resource_and_timing_results']['passed'], 'best build/timing is not verified')
    require(current['verification_status']=='simulation_and_synthesis_verified_physical_not_run'
            or current['verification_status']=='physical_verified', 'unverified selection status')
    if current['verification_status']=='physical_verified':
        require(bool(current.get('physical_evidence')), 'physical claim has no evidence')
        require(current.get('hardware_testing_status')=='verified' and
                current['resource_and_timing_results'].get('hardware_validated') is True,
                'contradictory physical metadata')
    if best!=selection['previous_best_known_sha']:
        promotion=selection.get('promotion',{})
        require(promotion.get('source_commit_sha')==best and promotion.get('accepted') is True,
                'changed best lacks explicit acceptance')
        required=('baseline','regression','synthesis','timing_resources','reproducibility')
        require(all(promotion.get('gates',{}).get(g) is True for g in required), 'promotion gates incomplete')
        require(bool(promotion.get('measurable_benefit')) and bool(promotion.get('evidence')), 'promotion lacks measured evidence')
    return best


def verify(root):
    root=Path(root).resolve()
    def read(relative): return json.loads((root/relative).read_text(encoding='utf-8-sig'))
    selection=read('handoffs/phase-05/selection.json')
    current=read('handoffs/quality-review/current-best.json')
    history=read('handoffs/phase-05/selection-history.json')
    backlog=read('handoffs/phase-05/improvement-backlog.json')
    require(backlog['last_evaluation_cycle_id']==selection['last_evaluation_cycle_id'], 'stale backlog cycle')
    best=validate_metadata(selection,current,history)
    previous_path=(root/selection['previous_checkpoint_history']).resolve()
    require(previous_path.is_relative_to(root), 'previous checkpoint path escapes root')
    previous=read(selection['previous_checkpoint_history'])
    pinned=json.loads(subprocess.check_output(['git','-C',str(root),'show',
          selection['previous_checkpoint_commit_sha']+':handoffs/phase-05/selection-history.json'],encoding='utf-8'))
    require(previous==pinned, 'previous checkpoint differs from immutable Git history')
    require(history['events'][:-1]==previous['events'], 'historical selection was rewritten')
    previous_best=previous['events'][-1].get('selected_sha',previous['events'][-1].get('sha'))
    require(selection['previous_best_known_sha']==previous_best and
            history['events'][-1]['previous_sha']==previous_best, 'previous best differs from immutable history')
    subprocess.run(['git','-C',str(root),'cat-file','-e',best+'^{commit}'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',selection['common_baseline_commit_sha'],best],check=True)
    entries=selection['cycle_evidence']
    require(bool(entries), 'missing current-cycle evidence')
    for entry in entries:
        path=(root/entry['path']).resolve()
        require(path.is_relative_to(root), 'evidence path escapes checkpoint')
        require(path.is_file() and digest(path)==entry['sha256_lf'], 'evidence digest mismatch: '+entry['path'])
    # Promotion and physical evidence also need retained, hash-bound receipts.
    indexed={e['path'] for e in entries}
    if best!=selection['previous_best_known_sha']:
        require(set(selection['promotion']['evidence']).issubset(indexed), 'promotion receipts not indexed')
    if current['verification_status']=='physical_verified':
        require(set(current['physical_evidence']).issubset(indexed), 'physical receipts not indexed')
        for path in current['physical_evidence']:
            proof=read(path)
            require(proof.get('source_commit_sha')==best and proof.get('physical_board_demonstration') is True
                    and proof.get('normal_baseline_passed') is True and proof.get('payload_passed') is True,
                    'physical receipt is not candidate-bound demonstration evidence')
    return {'passed':True,'cycle_id':selection['last_evaluation_cycle_id'],'best_sha':best,
            'evidence_files_checked':len(entries),'scope':'checkpoint integrity; no new HDL or hardware verification'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    try: result=verify(a.root)
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        result={'passed':False,'error':str(exc)}
    if a.output:
        with a.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)
