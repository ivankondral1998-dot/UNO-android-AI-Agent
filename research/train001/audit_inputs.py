import pathlib,hashlib,json,sys
root=pathlib.Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((root/'005b/COMPACT_MANIFEST_20261115.json').read_text())
for e in m['files']:
 p=root/'005b'/e['path']; assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
print('COMPACT_MANIFEST',len(m['files']),'files verified; excluded',m['excluded_entries'])
h=root/'handoff'
for line in (h/'MANIFEST_SHA256.txt').read_text().splitlines():
 if not line.strip(): continue
 digest,name=line.split(maxsplit=1); p=h/name.lstrip('* ');assert sha(p)==digest,name
print('HANDOFF_MANIFEST_PASS')
for p in (h/'RESULTS_005B').iterdir(): assert p.read_bytes()==(root/'005b/uno_ladder_005b_gpu'/p.name).read_bytes(),p.name
print('005B duplicate results identical')
for rung in ['r1_single','r2_two','r3_three','r4_overwrite','r5_order']:
 for model in ['uno_f','gru']:
  p=root/'005b/uno_ladder_005b_gpu'/f'{rung}__{model}'
  final=json.loads(p.with_suffix('.json').read_text());tr=json.loads(p.with_suffix('.train.json').read_text())
  for k in tr: assert tr[k]==final[k],(p,k)
  print(rung,model,'steps',tr['steps_run'],'verdict',final['verdict'],'weights_sha',sha(p.with_suffix('.weights.pt')))
print('No optimizer checkpoints in compact package: cannot resume old Adam runs')
