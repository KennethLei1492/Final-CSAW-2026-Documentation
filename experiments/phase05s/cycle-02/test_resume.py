import importlib.util,json,subprocess,tempfile
from pathlib import Path
root=Path.cwd()
spec=importlib.util.spec_from_file_location('phase05s_inspect',root/'experiments/phase05s/inspect.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
state=root/'handoffs/phase-05/selection.json'
live=module.inspect(root,state)
assert live['mode']=='B' and live['best_object_available']
assert not any(row['changed'] for row in live['candidates'].values())
with tempfile.TemporaryDirectory(prefix='05s-resume-') as temp:
    folder=Path(temp)
    old=json.loads(state.read_text())
    old['last_reviewed_candidate_shas']['05D']=old['original_candidate_shas']['05D']
    old_state=folder/'old.json'; old_state.write_text(json.dumps(old))
    delta=module.inspect(root,old_state)
    assert delta['candidates']['05D']['changed']
    assert len(delta['candidates']['05D']['changed_paths'])==12
    assert not any(r['changed'] for c,r in delta['candidates'].items() if c!='05D')
    subprocess.run(['git','init','--quiet',str(folder/'empty')],check=True)
    unavailable=module.inspect(folder/'empty',folder/'missing.json')
    assert unavailable['mode']=='A'
    assert all(r['availability']=='unavailable' for r in unavailable['candidates'].values())
    assert unavailable['remote_discovery_error']
out=root/'handoffs/phase-05/cycles/05S-002'
(out/'discovery.json').write_text(json.dumps(live,indent=2)+'\n')
(out/'resume-validation.json').write_text(json.dumps({'passed':True,'checks':[
 'Current checkpoint resumes B with best commit available; no changed candidates',
 'Old D snapshot identifies exactly 12 changed paths, no changes to other candidates',
 'Empty repository enters A and records all candidates unavailable, not failed',
 'Missing origin is recorded as remote discovery error without promotion']},indent=2)+'\n')
print('4 resumption checks passed')
