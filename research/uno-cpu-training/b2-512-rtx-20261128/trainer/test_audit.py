import pathlib, tempfile, random, time, subprocess, sys, os
import torch
from train_cuda_audit import Codec, Records, batch, objective, save, restore, validate_weights, validate_optimizer, output_lock, identity
from model_audit import B2
from model import B2 as Old

torch.set_num_threads(3);torch.manual_seed(123)
c=Codec();ids=torch.tensor(c.ids);remap=torch.full((32768,),-1,dtype=torch.long);remap[ids]=torch.arange(len(ids))
a=Old(128);b=B2(128);b.load_state_dict(a.state_dict());ao=torch.optim.Adam(a.parameters(),lr=2e-4);bo=torch.optim.Adam(b.parameters(),lr=2e-4)
for i in range(3):
 x=ids[torch.randint(len(ids),(2,8))];y=torch.randint(len(ids),(2,8));m=torch.ones_like(y,dtype=torch.bool)
 for model,opt in [(a,ao),(b,bo)]:
  opt.zero_grad(set_to_none=True);loss,_=objective(model,(x,y,m),ids);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step()
 t=time.perf_counter();a.project(ao);oldtime=time.perf_counter()-t;t=time.perf_counter();b.project(bo,ids);newtime=time.perf_counter()-t
 for (n,p),(q,r) in zip(a.named_parameters(),b.named_parameters()):
  assert n==q and torch.equal(p,r),n
 validate_weights(b);validate_optimizer(b,bo,ids)
 print('projection exact weights step',i+1,'original',round(oldtime,4),'new',round(newtime,4),flush=True)
# poison inactive moments to ensure they cannot bypass the subset projection on restore.
with torch.no_grad():bo.state[b.p['E_text']]['exp_avg'][258,0]=1
try:validate_optimizer(b,bo,ids);raise AssertionError('accepted inactive moment')
except ValueError as e:assert 'OPTIMIZER_INACTIVE_ROWS' in str(e)
print('inactive optimizer guard PASS',flush=True)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);f=p/'train.jsonl';f.write_text('{"text":"Привет, мир!"}\n',encoding='utf8');r=Records(f,'language');r.row(random.Random(1),c,8);assert len(r.cache)==1;assert r.encoded(0,c) is r.encoded(0,c)
 print('record cache PASS',flush=True)
 ck=p/'latest.uno';save(ck,{'step':1});save(ck,{'step':2},keep_previous=True);assert restore(p/'previous.uno')['step']==1;assert restore(ck)['step']==2
 print('checkpoint previous PASS',flush=True)
 with output_lock(p):
  proc=subprocess.run([sys.executable,'-c','from train_cuda_audit import output_lock;from pathlib import Path;import sys;\nwith output_lock(Path(sys.argv[1])): pass',d],capture_output=True);assert proc.returncode!=0
 with output_lock(p):pass
 proc=subprocess.Popen([sys.executable,'-c','from train_cuda_audit import output_lock;from pathlib import Path;import sys,time;\nwith output_lock(Path(sys.argv[1])): print("LOCKED",flush=True);time.sleep(60)',d],stdout=subprocess.PIPE,text=True);assert proc.stdout.readline().strip()=='LOCKED';proc.kill();proc.wait()
 with output_lock(p):pass
 print('OS lock concurrent refusal + forced death recovery PASS',flush=True)
print('AUDIT TESTS PASS',flush=True)
