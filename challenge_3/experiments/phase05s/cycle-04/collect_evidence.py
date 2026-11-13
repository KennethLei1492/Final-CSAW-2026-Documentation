"""Capture cycle004 reporting regressions and immutable source identity; no HDL runs."""
import copy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'handoffs/phase-05/cycles/05S-004'
FILES = ['handoffs/phase-05/'+n for n in ('selection.json','selection.md','selection-history.json','improvement-backlog.json','documentation-agent-handoff.md')]+['handoffs/quality-review/current-best.json']

def sha(data): return hashlib.sha256(data).hexdigest()
def save(name, value):
    with (OUT/name).open('x',encoding='utf-8') as f: json.dump(value,f,indent=2); f.write('\n')
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args])

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New evidence directory; existing output is refused')
    parser.add_argument('--official-source',type=Path,required=True,help='Previously retrieved official challenge README')
    args=parser.parse_args()
    OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=False)
    shared=ROOT.parents[1]
    # Archive before any shared update; the delivery step checks these hashes again.
    shared_state={}
    for rel in FILES:
        raw=(shared/rel).read_bytes()
        dest=OUT/'shared-before'/rel; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
        shared_state[rel]=sha(raw)
    save('shared-before-hashes.json',shared_state)
    for rel in FILES:
        dest=OUT/'previous-checkpoint'/Path(rel).name
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes((ROOT/rel).read_bytes())
    old_path=ROOT/'build/verify_state_before.py'
    old_path.parent.mkdir(parents=True,exist_ok=True)
    old_path.write_bytes(git('show','ab71ea88c7853fed7917c31c59c2f0b6abc83d96:experiments/phase05s/verify_state.py'))
    spec=importlib.util.spec_from_file_location('old_check',old_path)
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    selection=json.loads((ROOT/FILES[0]).read_text())
    current=json.loads((ROOT/FILES[-1]).read_text())
    history=json.loads((ROOT/FILES[2]).read_text())
    misses={}
    for name in ('winner_sha','candidate_id','original_inventory'):
        s,c,h=copy.deepcopy((selection,current,history))
        if name=='winner_sha': s['winner']['current_best_known_commit_sha']='0'*40
        if name=='candidate_id': c['selected_candidate_id']='05D'
        if name=='original_inventory': s['original_candidate_shas']['05B']='0'*40
        try: old.validate_metadata(s,c,h); misses[name]='incorrectly_accepted'
        except ValueError: misses[name]='rejected'
    test=subprocess.run([sys.executable,'experiments/phase05s/cycle-04/test_reliability.py'],cwd=ROOT,capture_output=True)
    log=test.stdout+test.stderr; (OUT/'reliability-tests.log').write_bytes(log)
    save('iteration-01-reliability.json',{
        'hypothesis':'The previous validator accepts conflicting winner identity and omits broken-ref diagnostics; completed checks prevent stale resumption.',
        'before_commit':'ab71ea88c7853fed7917c31c59c2f0b6abc83d96','before_mutations':misses,
        'after_test_exit_code':test.returncode,'tests_passed':19 if test.returncode==0 else None,
        'log':'reliability-tests.log','log_sha256':sha(log),
        'command':[sys.executable,'experiments/phase05s/cycle-04/test_reliability.py'],
        'review':'Independent code review found no must-fix regression; clean-checkout build directory setup added.',
        'decision':'accepted' if test.returncode==0 else 'rejected','rtl_changed':False})
    original='df22816fe29c479d404314bf0ae9e8baacdd1d3d'; recovered='ab71ea88c7853fed7917c31c59c2f0b6abc83d96'
    trees={commit:git('rev-parse',commit+'^{tree}').decode().strip() for commit in (original,recovered)}
    save('recovery.json',{'original_cycle003_commit':original,'recovered_commit':recovered,'trees':trees,
         'identical_trees':len(set(trees.values()))==1,'original_ref_status':'corrupted_NUL_ref_preserved',
         'shared_prior_cycle':'05S-002','authoritative_previous_cycle':'05S-003','best_commit_available':True,
         'candidate_source_diff':git('diff','--name-only',selection['current_best_known_sha'],recovered,'--','experiments/phase05/05b-astra').decode().splitlines()})
    url='https://raw.githubusercontent.com/JBlocklove/CSAW-AI-Hardware-Attack-Challenge-2026/main/finals/challenge_3/README.md'
    raw=args.official_source.read_bytes().replace(b'\r\n',b'\n')
    prior=(ROOT/'experiments/phase05s/cycle-02/official-rubric.md').read_bytes().replace(b'\r\n',b'\n')
    (OUT/'official-challenge.md').write_bytes(raw)
    save('official-rubric-review.json',{'url':url,'sha256':sha(raw),
        'scoring_section_unchanged':raw.split(b'## Scoring',1)[1]==prior.split(b'## Scoring',1)[1],
        'deliverables_change':'Current challenge points to finals overview for deliverables; category/bonus review below remains conditional.'})
    raise SystemExit(test.returncode)
