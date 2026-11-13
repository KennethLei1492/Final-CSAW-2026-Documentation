"""New failure cases prompted by the damaged cycle-003 reference and stale delivery."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
old=module('prior_tests',ROOT/'experiments/phase05s/cycle-03/test_state.py')
inspect=old.inspect
verify=old.verify

class MetadataTests(old.StateTests):
    def test_stale_winner_rejected(self):
        self.s['winner']['current_best_known_commit_sha']='0'*40
        with self.assertRaisesRegex(ValueError,'winner SHA'): verify.validate_metadata(self.s,self.c,self.h)
    def test_wrong_candidate_id_rejected(self):
        self.c['selected_candidate_id']='05D'
        with self.assertRaisesRegex(ValueError,'candidate ID'): verify.validate_metadata(self.s,self.c,self.h)
    def test_original_inventory_rejected(self):
        self.s['original_candidate_shas']['05B']='0'*40
        with self.assertRaisesRegex(ValueError,'original inventory'): verify.validate_metadata(self.s,self.c,self.h)
    def test_stale_backlog_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as tmp:
            folder=Path(tmp); self.isolated_checkpoint(folder)
            (folder/'handoffs/phase-05/improvement-backlog.json').write_text(json.dumps({'last_evaluation_cycle_id':'05S-001'}))
            with self.assertRaisesRegex(ValueError,'stale backlog'): verify.verify(folder)

class DiscoveryTests(unittest.TestCase):
    def test_broken_reference_is_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            subprocess.run(['git','init','--quiet',str(folder)],check=True)
            (folder/'.git/refs/heads/broken').write_bytes(b'\0'*41)
            result=inspect.inspect(folder,folder/'absent.json')
            self.assertTrue(any('broken ref' in item['stderr'] for item in result['git_diagnostics']))
    def test_missing_output_parent_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); subprocess.run(['git','init','--quiet',str(folder)],check=True)
            output=folder/'nested'/'new.json'
            command=[sys.executable,str(ROOT/'experiments/phase05s/inspect.py'),'--repo',str(folder),
                     '--state',str(folder/'absent.json'),'--output',str(output)]
            first=subprocess.run(command,capture_output=True)
            self.assertEqual(first.returncode,0,first.stderr)
            before=output.read_bytes()
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(output.read_bytes(),before)

if __name__=='__main__': unittest.main(verbosity=2)
