"""Only twelve synthetic diagnostic updates, true separate-process forced termination/resume."""
import pathlib,sys,tempfile,subprocess,json,torch
from prepare import prepare
from study import source_identity,hardware
from engine import restore,canonical,file_sha
if not __debug__:raise RuntimeError('Unoptimized Python required for test assertions')
initial=pathlib.Path(sys.argv[1]);device=sys.argv[2] if len(sys.argv)>2 else 'cpu'
root=pathlib.Path(tempfile.mkdtemp(prefix='uno-train002-crash-'));study=root/'study';prepare(study,initial.parent,diagnostic=True)
script=pathlib.Path(__file__).with_name('study.py');out=root/'runs';receipt=root/'internal-check.json'
if device=='cuda':receipt.write_text(canonical({'source':source_identity(),'hardware':hardware('cuda'),'status':'CUDA_MECHANISM_PASS_NOT_QUALITY','plan_sha':file_sha(study/'study.json')}))
def command(output,resume=False):
    return [sys.executable,str(script),'resume' if resume else 'train',str(study),'--output',str(output),'--arm','chrono_typed','--seed','260015','--device',device,*(['--receipt',str(receipt)] if device=='cuda' else [])]
with open(root/'continuous.log','w') as log:subprocess.run(command(root/'continuous'),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
child=subprocess.Popen(command(root/'interrupted'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
    for line in child.stdout:
        if line.startswith('{') and 'step' in json.loads(line) and json.loads(line)['step']>=3:child.kill();break
    child.wait(timeout=15);assert child.returncode!=0
finally:
    if child.poll() is None:child.kill();child.wait()
with open(root/'resumed.log','w') as log:subprocess.run(command(root/'interrupted',True),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
name='chrono_typed__260015';a=restore(root/'continuous'/name/'latest.uno');b=restore(root/'interrupted'/name/'latest.uno')
def same(a,b):
    if isinstance(a,torch.Tensor):assert torch.equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:same(a[k],b[k])
    elif isinstance(a,(tuple,list)):
        assert len(a)==len(b)
        for x,y in zip(a,b):same(x,y)
    else:assert a==b,(a,b)
# Wall-clock resource measurements are factual and not expected to be deterministic.
a.pop('elapsed');b.pop('elapsed');a.pop('peak_cuda_allocated');b.pop('peak_cuda_allocated');same(a,b)
print('FORCED_PROCESS_KILL_EXACT_RESUME weights/Adam/RNG/cursor/history/best PASS device='+device)
p=root/'interrupted'/name/'latest.uno';before=p.read_bytes();subprocess.run(command(root/'interrupted',True),stdout=subprocess.DEVNULL,check=True,timeout=45);assert p.read_bytes()==before
print('COMPLETED_RESUME_NO_REWRITE PASS')
bad=command(root/'interrupted',True);bad[bad.index('--arm')+1]='baseline_typed'
r=subprocess.run([sys.executable,'-O',*bad[1:]],capture_output=True,text=True,timeout=45)
assert r.returncode!=0 and 'UNDECLARED_RUN' in r.stderr
print('OPTIMIZED_PYTHON_UNDECLARED_ARM_REJECT PASS')
# Evaluate only this temporary diagnostic corpus, then verify cached report reuse.
cmd=[sys.executable,str(script),'evaluate',str(study),'--output',str(root/'interrupted')]
with open(root/'evaluate.log','w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
report=root/'interrupted/test-report.json';original=report.read_bytes()
with open(root/'cached.log','w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
assert report.read_bytes()==original
print('DIAGNOSTIC_LOCKED_SELECTION_AND_CACHED_REPORT_PASS')
print('DIAGNOSTIC_ONLY NO_QUALITY_TRAINING')
