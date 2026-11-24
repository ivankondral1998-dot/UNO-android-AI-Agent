"""Bounded 12-update synthetic mechanism test, true kill/restart in separate Python processes.
No held-out task experiment. Uses provided Kotlin fixture, not RTX training corpus.
"""
import json,pathlib,subprocess,sys,tempfile,torch,hashlib,os
from torch_backend import restore,checkpoint
if not __debug__:raise RuntimeError('Tests require Python without -O')
device=sys.argv[2] if len(sys.argv)>2 else "cpu"
if device=="cuda" and not torch.cuda.is_available():raise RuntimeError("CUDA_UNAVAILABLE; no CPU fallback")
fixture=pathlib.Path(sys.argv[1]);root=pathlib.Path(tempfile.mkdtemp(prefix='uno-crash-test-'));data=root/'data';data.mkdir()
rules={f[0]:f[1:3] for f in (line.split('\t') for line in (fixture/'update1.tsv').read_text().splitlines())}
lines=[]
for line in (fixture/'weights.tsv').read_text().splitlines():
    n,r,c,x,g=line.split('\t');cap,box=rules[n];lines.append('\t'.join((n,r,c,cap,box,x)))
(data/'initial.tsv').write_text('\n'.join(lines))
record,state,value,_=(fixture/'target.tsv').read_text().split('\t');label='1' if float(state)>0 else '0'
raw=';'.join(line.split('\t')[-1] for line in (fixture/'events.tsv').read_text().splitlines())
for split in ('train','validation','test','erased'):(data/f'{split}.tsv').write_text('\t'.join((split+'-diagnostic-0',label,record,value,raw))+'\n')
backend=pathlib.Path(__file__).with_name('torch_backend.py')
# Internal qualification receipt exists only in this temporary diagnostic directory.
# The user-visible final Check receipt is written only after all tests succeed.
receipt=root/'diagnostic-cuda-receipt.json'
if device=='cuda':receipt.write_text(json.dumps({'status':'CUDA_MECHANISM_CHECK_PASS_NOT_QUALITY','backend_sha256':hashlib.sha256(backend.read_bytes()).hexdigest(),'torch':str(torch.__version__),'gpu':torch.cuda.get_device_name(0)}))
def cmd(output,*extra):
    return [sys.executable,str(backend),'train',str(data),str(root/output),'--device',device,'--precision','double' if device=='cpu' else 'float32','--steps','12','--batch','1','--seed','47',*(['--cuda-receipt',str(receipt)] if device=='cuda' else []),*extra]
with open(root/'continuous.txt','w') as log:subprocess.run(cmd('continuous'),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
child=subprocess.Popen(cmd('crashed'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
    for line in child.stdout:
        if line.startswith('{') and json.loads(line)['step']>=3:child.kill();break
    child.wait(timeout=10)
    assert child.returncode!=0,'EXPECTED_KILLED_PROCESS'
finally:
    if child.poll() is None:child.kill();child.wait()
with open(root/'resume.txt','w') as log:subprocess.run(cmd('crashed','--resume'),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
a=restore(root/'continuous/latest.uno');b=restore(root/'crashed/latest.uno')
def same(x,y):
    if isinstance(x,torch.Tensor):assert torch.equal(x,y)
    elif isinstance(x,dict):
        assert x.keys()==y.keys()
        for k in x:same(x[k],y[k])
    elif isinstance(x,(list,tuple)):
        assert len(x)==len(y)
        for v,w in zip(x,y):same(v,w)
    else:assert x==y,(x,y)
same(a,b);print('TWELVE_SYNTHETIC_UPDATES_FORCED_PROCESS_KILL_RESUME_EXACT_WEIGHTS_MOMENTS_CURSOR_RNG_HISTORY_BEST_PASS')
# Completed resume must not rewrite the pinned checkpoint.
original=(root/'crashed/latest.uno').read_bytes()
subprocess.run(cmd('crashed','--resume'),stdout=subprocess.DEVNULL,check=True,timeout=30)
assert (root/'crashed/latest.uno').read_bytes()==original
print('COMPLETED_RESUME_CHECKPOINT_UNCHANGED_PASS')
# Invariants survive optimized interpreter flags; changing batch cannot silently resume.
bad=[sys.executable,'-O',*cmd('crashed','--resume')[1:]];bad[bad.index('--batch')+1]='2'
r=subprocess.run(bad,capture_output=True,text=True,timeout=30)
assert r.returncode!=0 and 'RUN_MANIFEST_MISMATCH' in r.stderr
print('OPTIMIZED_PYTHON_CONFIG_MISMATCH_REJECTED_PASS')
if not torch.cuda.is_available():
    bad=cmd('cuda-unavailable');bad[bad.index('--device')+1]='cuda'
    r=subprocess.run(bad,capture_output=True,text=True,timeout=30)
    assert r.returncode!=0 and 'CUDA_UNAVAILABLE' in r.stderr
    print('CUDA_UNAVAILABLE_NO_CPU_FALLBACK_PASS')
print('CRASH_TEST_PASS device='+device+'; only bounded synthetic diagnostic updates, no quality training')
