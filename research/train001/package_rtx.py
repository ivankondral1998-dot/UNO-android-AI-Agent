"""Package only prepared synthetic input/fixtures and tracked runner sources. Never starts training."""
import argparse,hashlib,pathlib,zipfile
p=argparse.ArgumentParser();p.add_argument('prepared',type=pathlib.Path);a=p.parse_args();root=a.prepared.resolve();source=pathlib.Path(__file__).resolve().parent
required=['initial.tsv','train.tsv','validation.tsv','test.tsv','erased.tsv']
files=[]
for name in required:
    path=root/name
    if not path.is_file():raise ValueError('MISSING_PREPARED_INPUT '+name)
    files.append(path)
for fixture in ('parity','parity96','parity-singleton'):
    for name in ('weights.tsv','events.tsv','target.tsv','controls.tsv','update1.tsv','update2.tsv'):
        path=root/fixture/name
        if not path.is_file():raise ValueError('MISSING_KOTLIN_FIXTURE '+str(path))
        files.append(path)
for name in ('torch_backend.py','torch_backend_test.py','torch_crash_test.py','rtx_check.py','RTX.ps1','README_RTX.md'):
    target=root/name;data=(source/name).read_bytes()
    if target.exists() and target.read_bytes()!=data:raise ValueError('REFUSE_REPLACE_PREVIOUS_BUNDLE '+name)
    target.write_bytes(data);files.append(target)
manifest=''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(root).as_posix()+'\n' for f in sorted(files))
(root/'SHA256SUMS').write_text(manifest);files.append(root/'SHA256SUMS')
archive=root.with_suffix('.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in sorted(files):z.write(f,(pathlib.Path(root.name)/f.relative_to(root)).as_posix())
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise ValueError('ZIP_CRC_FAILED')
    for f in files:
        if z.read((pathlib.Path(root.name)/f.relative_to(root)).as_posix())!=f.read_bytes():raise ValueError('ZIP_ROUNDTRIP_FAILED')
print('PREPARED_ONLY',archive,'bytes',archive.stat().st_size,'sha256',hashlib.sha256(archive.read_bytes()).hexdigest())
