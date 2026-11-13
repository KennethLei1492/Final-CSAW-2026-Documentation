"""Archive locally generated evidence, retaining its complete per-file hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

EXP=Path(__file__).resolve().parent.parent


def main():
    argv=[sys.executable,str(EXP/'tools/test_decoder.py')]
    result=subprocess.run(argv,capture_output=True,text=True)
    (EXP/'evidence/decoder-tests.log').write_text(result.stdout+result.stderr)
    (EXP/'evidence/decoder-tests.log.json').write_text(json.dumps({'argv':argv,'exit_code':result.returncode},indent=2)+'\n')
    if result.returncode: raise RuntimeError('Decoder tests failed')
    files=[]
    for name in ('evidence','reports','tests/rtl/q-vectors','tests/rtl/recovered'):
        files += [p for p in (EXP/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    archive=EXP/'verification-evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(files): z.write(p,p.relative_to(EXP).as_posix())
    def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    inventory={'archive':archive.name,'archive_sha256':digest(archive),
        'files':{p.relative_to(EXP).as_posix():digest(p) for p in sorted(files)}}
    (EXP/'evidence-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    source=[]
    for name in ('rtl','tools','constraints','inputs','official'):
        source += [p for p in (EXP/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    source += list((EXP/'tests/rtl').glob('*.py'))+list((EXP/'tests/rtl').glob('*.sv'))
    source += [EXP/'baseline-build-manifest.json']
    (EXP/'source-inventory.json').write_text(json.dumps({p.relative_to(EXP).as_posix():digest(p) for p in sorted(source)},indent=2)+'\n')
    print(f'Archived {len(files)} files, {archive.stat().st_size} bytes')


if __name__=='__main__': main()
