"""Regression tests for missed supporting sources and unsafe/stale checkpoints."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
inspect=module('checkpoint_inspect',ROOT/'experiments/phase05s/inspect.py')
verify=module('checkpoint_verify',ROOT/'experiments/phase05s/verify_state.py')

class StateTests(unittest.TestCase):
    def setUp(self):
        self.s=json.loads((ROOT/'handoffs/phase-05/selection.json').read_text())
        self.c=json.loads((ROOT/'handoffs/quality-review/current-best.json').read_text())
        self.h=json.loads((ROOT/'handoffs/phase-05/selection-history.json').read_text())
    def test_current_cycle_and_full_integrity(self):
        self.assertTrue(verify.verify(ROOT)['passed'])
    def test_old_cycle_rejected(self):
        self.c.update(phase='Q',cycle=1)
        with self.assertRaisesRegex(ValueError,'stale current-best cycle'):
            verify.validate_metadata(self.s,self.c,self.h)
    def test_unverified_promotion_rejected(self):
        other='a'*40
        self.s['current_best_known_sha']=other
        self.c.update(current_best_known_sha=other,current_best_known_commit_sha=other)
        self.h['events'][-1]['selected_sha']=other
        with self.assertRaisesRegex(ValueError,'explicit acceptance'):
            verify.validate_metadata(self.s,self.c,self.h)
    def test_pending_verification_rejected(self):
        self.c['regression_status']='pending'
        with self.assertRaisesRegex(ValueError,'not verified'):
            verify.validate_metadata(self.s,self.c,self.h)
    def test_unsupported_physical_claim_rejected(self):
        self.c['verification_status']='physical_verified'
        with self.assertRaisesRegex(ValueError,'physical claim'):
            verify.validate_metadata(self.s,self.c,self.h)
    def test_future_cycle_is_not_hardcoded(self):
        self.s.update(cycle_number=25,last_evaluation_cycle_id='05S-025')
        self.c.update(cycle=25,last_evaluation_cycle_id='05S-025')
        self.h['events'][-1]['id']='05S-025'
        self.assertEqual(verify.validate_metadata(self.s,self.c,self.h),self.s['current_best_known_sha'])
    def test_contradictory_physical_status_rejected(self):
        self.c.update(verification_status='physical_verified',physical_evidence=['some-indexed-file.json'])
        with self.assertRaisesRegex(ValueError,'contradictory physical'):
            verify.validate_metadata(self.s,self.c,self.h)
    def isolated_checkpoint(self, folder):
        paths=['handoffs/phase-05/selection.json','handoffs/quality-review/current-best.json',
               'handoffs/phase-05/selection-history.json',self.s['previous_checkpoint_history']]
        paths += [entry['path'] for entry in self.s['cycle_evidence']]
        for path in paths:
            dest=folder/path; dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/path,dest)
    def test_evidence_tampering_rejected(self):
        with tempfile.TemporaryDirectory(prefix='state-check-',dir=ROOT/'build') as tmp:
            folder=Path(tmp); self.isolated_checkpoint(folder)
            target=folder/self.s['cycle_evidence'][0]['path']
            target.write_text(target.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'digest mismatch'): verify.verify(folder)
    def test_history_rewrite_rejected(self):
        with tempfile.TemporaryDirectory(prefix='state-check-',dir=ROOT/'build') as tmp:
            folder=Path(tmp); self.isolated_checkpoint(folder)
            changed=copy.deepcopy(self.h); changed['events'][0]['selected_sha']='0'*40
            (folder/'handoffs/phase-05/selection-history.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'historical selection'): verify.verify(folder)
    def test_forged_previous_best_cannot_bypass_promotion(self):
        with tempfile.TemporaryDirectory(prefix='state-check-',dir=ROOT/'build') as tmp:
            folder=Path(tmp); self.isolated_checkpoint(folder)
            forged=self.s['common_baseline_commit_sha']
            self.s.update(current_best_known_sha=forged,previous_best_known_sha=forged)
            self.c.update(current_best_known_sha=forged,current_best_known_commit_sha=forged,previous_best_known_sha=forged)
            self.h['events'][-1].update(selected_sha=forged,previous_sha=forged)
            for name,data in [('handoffs/phase-05/selection.json',self.s),('handoffs/quality-review/current-best.json',self.c),('handoffs/phase-05/selection-history.json',self.h)]:
                (folder/name).write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'previous best differs'): verify.verify(folder)
    def test_joint_history_rewrite_rejected(self):
        with tempfile.TemporaryDirectory(prefix='state-check-',dir=ROOT/'build') as tmp:
            folder=Path(tmp); self.isolated_checkpoint(folder)
            older=json.loads((folder/self.s['previous_checkpoint_history']).read_text())
            older['events'][0]['selected_sha']='0'*40
            self.h['events'][:-1]=older['events']
            (folder/self.s['previous_checkpoint_history']).write_text(json.dumps(older))
            (folder/'handoffs/phase-05/selection-history.json').write_text(json.dumps(self.h))
            with self.assertRaisesRegex(ValueError,'immutable Git history'): verify.verify(folder)
    def test_new_bonus_source_discovered(self):
        out=inspect.inspect(ROOT,ROOT/'handoffs/phase-05/selection.json')
        item=out['supporting_sources']['refs/heads/challenge3/05bb-bonus-b']
        self.assertIn('handoffs/phase-05/bonus-b.json',item['handoff_paths'])
        self.assertEqual(out['current_best_known_sha'],self.s['current_best_known_sha'])
    def test_remote_only_is_not_failed_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); remote=base/'remote'; local=base/'local'
            for repo in (remote,local): subprocess.run(['git','init','--quiet',str(repo)],check=True)
            (remote/'receipt.txt').write_text('new remote evidence')
            subprocess.run(['git','-C',str(remote),'add','.'],check=True)
            subprocess.run(['git','-C',str(remote),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','evidence fixture'],check=True)
            subprocess.run(['git','-C',str(local),'remote','add','origin',str(remote)],check=True)
            out=inspect.inspect(local,base/'none.json')
            self.assertEqual(out['mode'],'A')
            self.assertTrue(all(c['availability']=='unavailable' for c in out['candidates'].values()))
            self.assertTrue(any(c['availability']=='remote_only_not_fetched' for c in out['supporting_sources'].values()))
            subprocess.run(['git','-C',str(remote),'branch','-m','challenge3/05b-astra'],check=True)
            out=inspect.inspect(local,base/'none.json')
            self.assertEqual(out['candidates']['05B']['remote']['availability'],'remote_only_not_fetched')
            self.assertTrue(out['candidates']['05B']['remote']['differs_from_local'])

if __name__=='__main__': unittest.main(verbosity=2)
