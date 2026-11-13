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
    diagnostics = []
    def git(*args):
        p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, encoding='utf-8', timeout=45)
        if p.stderr.strip():
            diagnostics.append({'command':list(args), 'exit_code':p.returncode, 'stderr':p.stderr.strip()})
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    prior = json.loads(state.read_text(encoding='utf-8-sig')) if state.exists() else None
    code, tree_text, err = git('worktree', 'list', '--porcelain')
    if code: raise RuntimeError(err)
    worktrees = {}
    invalid_worktrees = []
    for block in tree_text.split('\n\n'):
        fields = dict(line.split(' ', 1) for line in block.splitlines() if ' ' in line)
        if fields.get('HEAD') == '0'*40:
            invalid_worktrees.append(fields)
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
            row['worktree_status_error'] = status.stderr.strip() if status.returncode else None
        candidates[cid] = row
    rcode, remote, rerr = git('ls-remote','--heads','origin')
    remote_tips = {name: tip for tip,name in (line.split(None,1) for line in remote.splitlines())} if not rcode else {}
    reviewed_remote = prior.get('last_reviewed_remote_candidate_shas', {}) if prior else {}
    for cid, branch in BRANCHES.items():
        tip=remote_tips.get('refs/heads/'+branch)
        before=reviewed_remote.get(cid)
        candidates[cid]['remote'] = {
            'snapshot_sha':tip, 'previously_reviewed_sha':before,
            'availability':'discovery_error' if rcode else 'unavailable' if tip is None else
                'available' if git('cat-file','-e',tip+'^{commit}')[0]==0 else 'remote_only_not_fetched',
            'differs_from_local':tip != candidates[cid]['snapshot_sha'] if tip else None,
            'review_status':'unavailable' if tip is None else 'new' if before is None else 'changed' if before!=tip else 'unchanged'}
    # Supporting work can arrive outside the four original candidate branches.
    # Inventory immutable tips without fetching, changing branches or promoting.
    fcode, refs, ferr = git('for-each-ref','--format=%(refname) %(objectname)', 'refs/heads', 'refs/remotes')
    if fcode: raise RuntimeError(ferr)
    available_refs = dict(line.split(' ', 1) for line in refs.splitlines())
    if not rcode:
        for line in remote.splitlines():
            tip, name = line.split(None, 1)
            available_refs['refs/remotes/origin/'+name.removeprefix('refs/heads/')] = tip
    reviewed_refs = prior.get('last_reviewed_source_refs', {}) if prior else {}
    supporting = {}
    for ref, tip in available_refs.items():
        if ref.endswith('/HEAD'): continue
        branch = ref.removeprefix('refs/heads/').removeprefix('refs/remotes/origin/')
        if branch in BRANCHES.values(): continue
        object_available = git('cat-file','-e',tip+'^{commit}')[0] == 0
        paths = []
        if object_available:
            tcode, paths_text, terr = git('ls-tree','-r','--name-only',tip,'handoffs')
            if tcode: raise RuntimeError(terr)
            paths = paths_text.splitlines()
            if not paths: continue
        before = reviewed_refs.get(ref)
        supporting[ref] = {'snapshot_sha':tip, 'previously_reviewed_sha':before,
                           'review_status':'new' if before is None else 'changed' if before != tip else 'unchanged',
                           'object_available':object_available, 'handoff_paths':paths,
                           'availability':'available' if object_available else 'local_object_unavailable' if ref.startswith('refs/heads/') else 'remote_only_not_fetched',
                           'worktree':worktrees.get(branch) if ref.startswith('refs/heads/') else None}
    best = prior.get('current_best_known_sha') if prior else None
    best_available = git('cat-file','-e',best+'^{commit}')[0] == 0 if best else None
    return {'schema_version':3, 'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),
            'git_diagnostics':diagnostics, 'invalid_worktrees':invalid_worktrees,
            'mode':'A' if prior is None else 'B', 'state_file':str(state),
            'current_best_known_sha':best, 'best_object_available':best_available,
            'candidates':candidates, 'supporting_sources':supporting,
            'remote_heads':remote.splitlines() if not rcode else [],
            'remote_discovery_error':rerr if rcode else None,
            'policy':'Review changed source and new evidence only. Mode C requires isolated experiment and passing gates. No promotion performed.'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.cwd())
    p.add_argument('--state',type=Path,default=Path('handoffs/phase-05/selection.json'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=inspect(a.repo,a.state)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2); stream.write('\n')
    print(json.dumps({'mode':result['mode'],'best_object_available':result['best_object_available'],
                      'candidates':{cid:row['availability'] for cid,row in result['candidates'].items()}}))
