from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
m=json.loads((r/'SHA256_MANIFEST.json').read_text())
for e in m['files']:
 b=(r/e['path']).read_bytes()
 assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'],e['path']
print('MANIFEST PASS:',len(m['files']),'files')
