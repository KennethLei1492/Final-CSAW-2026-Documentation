"""Read-only Phase 05S resumption inventory; never promote a candidate automatically.

Run before each bounded cycle. Selection/history files remain human/agent reviewed.
An unavailable branch is not a failed implementation. Remote errors are recorded.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

BRANCHES = {'05A':'challenge3/05a-luna', '05B':'challenge3/05b-astra',
            '05C':'challenge3/05c-opus-architecture', '05D':'challenge3/05d-opus-dsp'}


def inspect(repo, state):
    def git(*args):
        p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, encoding='utf-8', timeout=45)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    prior = json.loads(state.read_text(encoding='utf-8-sig')) if state.exists() else None
    code, tree_text, err = git('worktree', 'list', '--porcelain')
    if code: raise RuntimeError(err)
    worktrees = {}
    for block in tree_text.split('\n\n'):
        fields = dict(line.split(' ', 1) for line in block.splitlines() if ' ' in line)
        if 'branch' in fields:
            worktrees[fields['branch'].removeprefix('refs/heads/')] = fields['worktree']
    candidates = {}
    reviewed = prior.get('last_reviewed_candidate_shas', {}) if prior else {}
    for cid, branch in BRANCHES.items():
        code, sha, _ = git('rev-parse', '--verify', 'refs/heads/'+branch+'^{commit}')
        row = {'branch':branch, 'worktree':worktrees.get(branch),
               'availability':'available' if not code else 'unavailable',
               'snapshot_sha':sha if not code else None, 'previously_reviewed_sha':reviewed.get(cid)}
        if not code and row['previously_reviewed_sha']:
            dcode, diff, derr = git('diff', '--name-only', row['previously_reviewed_sha'], sha)
            row.update(changed=sha != row['previously_reviewed_sha'],
                       changed_paths=diff.splitlines() if not dcode else None, diff_error=derr or None)
        if row['worktree']:
            status = subprocess.run(['git','-C',row['worktree'],'status','--porcelain'],
                                    capture_output=True,text=True,encoding='utf-8',timeout=30)
            row['working_changes_excluded'] = status.stdout.splitlines()
        candidates[cid] = row
    rcode, remote, rerr = git('ls-remote','--heads','origin')
    best = prior.get('current_best_known_sha') if prior else None
    best_available = git('cat-file','-e',best+'^{commit}')[0] == 0 if best else None
    return {'schema_version':1, 'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),
            'mode':'A' if prior is None else 'B', 'state_file':str(state),
            'current_best_known_sha':best, 'best_object_available':best_available,
            'candidates':candidates, 'remote_heads':remote.splitlines() if not rcode else [],
            'remote_discovery_error':rerr if rcode else None,
            'policy':'Review changed source and new evidence only. Mode C requires isolated experiment and passing gates. No promotion performed.'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--state',type=Path,default=Path('handoffs/phase-05/selection.json'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=inspect(a.repo,a.state)
    with a.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2); stream.write('\n')
    print(json.dumps({'mode':result['mode'],'best_object_available':result['best_object_available'],
                      'candidates':{cid:row['availability'] for cid,row in result['candidates'].items()}}))
