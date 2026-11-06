#!/usr/bin/env python3
"""Read-only verification of preserved source bytes; run from any cwd."""
import hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[3]
m=json.loads((pathlib.Path(__file__).with_name('MIRROR_SHA256.json')).read_text(encoding='utf-8'))
fail=[]
for item in m['files']:
 p=root/item['path']
 if not p.is_file():fail.append((item['path'],'MISSING'));continue
 b=p.read_bytes()
 if len(b)!=item['bytes'] or hashlib.sha256(b).hexdigest()!=item['sha256']:fail.append((item['path'],'SHA_MISMATCH'))
print('UNO mirror',len(m['files'])-len(fail),'/',len(m['files']),'verified')
for x in fail:print('FAIL',*x)
if fail:sys.exit(1)
