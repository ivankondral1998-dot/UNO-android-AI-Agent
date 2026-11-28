"""New research phase of existing B2-512; language/assistant only, no S4 write/S6.
Original checkpoint and tokenizer pinned. New corpus/optimizer, never old exact resume.
"""
import argparse, hashlib, io, json, math, os, random, subprocess, sys, time, tempfile, heapq
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import torch
from torch.nn import functional as F
from model import B2
ROOT=Path(__file__).resolve().parent
TOK_SHA='1c622409b42d96d339505d15d69da66d7176788f358e828672970c3ee637474f'
PARENT_SHA='33186b7515eef3a7d3954d94d9c31cd1969cdb1ce2f811c80e020cfd12f58a62'
HEADER=b'UNO-B2-CUDA-RESEARCH/V1\n'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def require(c,s):
 if not c:raise ValueError(s)
class Codec:
 def __init__(self):
  p=ROOT/'tokenizer.json';require(sha(p)==TOK_SHA,'TOKENIZER_MISMATCH');t=json.loads(p.read_text());self.ids=t['active_ids'];self.rules={(a,b):(i,c) for i,(a,b,c) in enumerate(t['merges'])};self.bos=t['bos'];self.eos=t['eos']
 def encode(self,s):
  # Same ranked merge order as original byte BPE, leftmost tie-breaking.
  v=list(s.encode('utf8'));n=len(v);prev=list(range(-1,n-1));nxt=list(range(1,n+1));alive=[True]*n;q=[]
  def push(i):
   if i>=0 and alive[i] and nxt[i]<n:
    j=nxt[i];rule=self.rules.get((v[i],v[j]))
    if rule:heapq.heappush(q,(rule[0],i,j,v[i],v[j],rule[1]))
  for i in range(n-1):push(i)
  while q:
   rank,i,j,a,b,c=heapq.heappop(q)
   if not alive[i] or not alive[j] or nxt[i]!=j or v[i]!=a or v[j]!=b:continue
   v[i]=c;alive[j]=False;k=nxt[j];nxt[i]=k
   if k<n:prev[k]=i
   push(prev[i]);push(i)
  return [x for i,x in enumerate(v) if alive[i]]
 def record(self,r,kind):
  if kind=='language':
   t=[self.bos]+self.encode(r['text'])+[self.eos];return t,[False]+[True]*(len(t)-1)
  t=[self.bos];mask=[False];role='user'
  for m in r['messages']:
   require(m['role']==role,'ROLE_ORDER');a=self.encode('Пользователь: ' if role=='user' else 'UNO: ');b=self.encode(m['text'])+[self.eos];t+=a+b;mask += [False]*len(a)+[role=='assistant']*len(b);role='assistant' if role=='user' else 'user'
  require(role=='user','NO_FINAL_ASSISTANT');return t,mask
class Records:
 def __init__(self,p,kind):
  self.p=p;self.kind=kind;self.offsets=[]
  with p.open('rb') as f:
   while True:
    pos=f.tell();line=f.readline()
    if not line:break
    if line.strip():self.offsets.append(pos)
  require(bool(self.offsets),'EMPTY '+str(p))
 def get(self,i):
  with self.p.open('rb') as f:f.seek(self.offsets[i]);return json.loads(f.readline())
 def row(self,rng,codec,L):
  for _ in range(100):
   t,m=codec.record(self.get(rng.randrange(len(self.offsets))),self.kind)
   targets=[i for i in range(1,len(t)) if m[i]]
   if not targets:continue
   i=rng.choice(targets);lo=max(0,i-L);hi=min(i-1,max(0,len(t)-L-1));start=rng.randint(lo,max(lo,hi));a=t[start:start+L+1];b=m[start:start+L+1];k=len(a)-1
   return a[:-1]+[codec.bos]*(L-k),a[1:]+[codec.eos]*(L-k),b[1:]+[False]*(L-k)
  raise ValueError('NO_TARGETS '+str(self.p))
def identity(data):
 p=data/'SHA256SUMS.txt';require(p.is_file(),'CORPUS_INCOMPLETE');seen=set()
 for line in p.read_text(encoding='utf8').splitlines():
  d,n=line.split(maxsplit=1);n=n.lstrip('*');q=(data/n).resolve();require(q.is_relative_to(data.resolve()) and q.is_file() and n not in seen,'CORPUS_PATH');require(sha(q)==d,'CORPUS_HASH '+n);seen.add(n)
 for n in ('tokenizer.json','report.json','language/train.jsonl','language/validation.jsonl','dialogue/train.jsonl','dialogue/validation.jsonl'):require(n in seen,'MISSING '+n)
 require(sha(data/'tokenizer.json')==TOK_SHA,'CORPUS_TOKENIZER');return sha(p)
@torch.no_grad()
def validate_weights(model):
 for n,p in model.p.items():
  cap,box=model.rules[n];require(bool(torch.isfinite(p).all()),'NONFINITE '+n);v=p.detach().double().abs();require(bool((v.max() if box else v.sum(-1).max())<=cap),'CAP '+n)
  if n in model.frozen:require(bool((p[model.frozen[n]]==0).all()),'FROZEN '+n)
def guard():
 s=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True,timeout=5).strip().splitlines();require(len(s)==1,'GPU_COUNT');t,m=map(float,s[0].split(','));require(math.isfinite(t) and math.isfinite(m) and 0<=t<78 and 0<=m<6500,'GPU_GUARD_STOP '+str(s));return [t,m]
def save(p,obj):
 b=io.BytesIO();torch.save(obj,b);body=b.getbuffer();fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:f.write(HEADER);f.write(hashlib.sha256(body).hexdigest().encode()+b'\n');f.write(body);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def restore(p):
 with p.open('rb') as f:require(f.readline()==HEADER,'CHECKPOINT_FORMAT');d=f.readline().strip();b=f.read()
 require(hashlib.sha256(b).hexdigest().encode()==d,'CHECKPOINT_HASH');return torch.load(io.BytesIO(b),map_location='cpu',weights_only=True)
def batch(records,rng,codec,L,B,device,remap):
 r=[records.row(rng,codec,L) for _ in range(B)];x,y,m=zip(*r);x=torch.tensor(x,device=device);y=remap[torch.tensor(y,device=device)];m=torch.tensor(m,device=device,dtype=torch.bool);require(bool(m.any()) and bool((y>=0).all()),'MASK_OR_ID');return x,y,m
def objective(model,r,ids):
 x,y,m=r;z=model.language(x,ids,1)[m];return F.cross_entropy(z,y[m]),int(m.sum())
@torch.no_grad()
def evaluate(model,sets,codec,ids,remap,a):
 model.eval();res={}
 for k,ds in sets.items():
  rng=random.Random(271828);total=0;loss=0.;correct=0
  for _ in range(a.eval_batches):
   if a.device=='cuda':guard()
   x,y,m=batch(ds,rng,codec,a.context,a.batch,a.device,remap);z=model.language(x,ids,1)[m];target=y[m];n=len(target);total+=n;loss+=float(F.cross_entropy(z,target,reduction='sum'));correct+=int((z.argmax(-1)==target).sum())
  res[k]={'nll':loss/total,'targets':total,'accuracy':correct/total}
 return res

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['probe','train','resume']);p.add_argument('--data',type=Path,default=Path(r'D:\UNO\corpus_prepared_v3'));p.add_argument('--out',type=Path,default=Path(r'D:\UNO\b2_cuda_run'));p.add_argument('--minutes',type=float,default=0);p.add_argument('--device',choices=['cuda','cpu'],default='cuda');p.add_argument('--batch',type=int,default=8);p.add_argument('--context',type=int,default=32);p.add_argument('--eval-batches',type=int,default=8);p.add_argument('--probe-steps',type=int,default=5);p.add_argument('--max-steps',type=int,default=100000);a=p.parse_args();require(1<=a.batch<=32 and 2<=a.context<=128 and 1<=a.eval_batches<=32 and a.probe_steps>=1 and a.max_steps>=1,'BOUNDS');require(a.command=='probe' or a.device=='cuda','CPU_PROBE_ONLY');require(a.command=='probe' or a.minutes>0,'MINUTES_REQUIRED')
 if a.device=='cuda':require(torch.cuda.is_available() and torch.cuda.device_count()==1,'CUDA_REQUIRED');guard()
 torch.set_num_threads(3);torch.manual_seed(20261128512);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
 data=a.data.resolve();digest=identity(data);codec=Codec();ids=torch.tensor(codec.ids,device=a.device);remap=torch.full((32768,),-1,device=a.device,dtype=torch.long);remap[ids]=torch.arange(len(ids),device=a.device)
 train={k:Records(data/k/'train.jsonl',k) for k in ('language','dialogue')};dev={k:Records(data/k/'validation.jsonl',k) for k in train};require(sha(ROOT/'latest.uno')==PARENT_SHA,'PARENT_MISMATCH');parent=torch.load(ROOT/'latest.uno',map_location='cpu',weights_only=True);model=B2(512);model.load_state_dict(parent['weights'],strict=True);del parent;model.to(a.device);validate_weights(model);opt=torch.optim.Adam(model.parameters(),lr=2e-4);rng=random.Random(20261128512);step=0;best=float('inf');hist=[]
 cfg={'corpus':digest,'parent':PARENT_SHA,'tokenizer':TOK_SHA,'model':sha(ROOT/'model.py'),'trainer':sha(Path(__file__)),'device':a.device,'torch':str(torch.__version__),'gpu':torch.cuda.get_device_name(0) if a.device=='cuda' else None,'context':a.context,'batch':a.batch,'eval_batches':a.eval_batches,'stage':'B2-512 fixed K1 language/assistant research, fresh Adam'}
 if a.command!='probe':
  receipt=ROOT/'cuda-probe.json';require(receipt.is_file(),'RUN_CUDA_PROBE_FIRST');r=json.loads(receipt.read_text());require(r.get('status')=='CUDA_MECHANISM_ONLY_NOT_QUALITY' and r.get('config')==cfg,'CUDA_PROBE_MISMATCH')
  if a.command=='train':a.out.mkdir(parents=True,exist_ok=False)
  else:require(a.out.is_dir(),'NO_RUN')
  # exclusive creation, fail closed after crash; never silently clear lock
  lock=a.out/'active.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 else:lock=None
 def snapshot(path):save(path,{'config':cfg,'weights':model.state_dict(),'optimizer':opt.state_dict(),'step':step,'rng':rng.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if a.device=='cuda' else [],'best':best,'history':hist})
 try:
  if a.command=='resume':
   c=restore(a.out/'latest.uno');require(c['config']==cfg,'RESUME_CONFIG_MISMATCH');model.load_state_dict(c['weights'],strict=True);validate_weights(model);opt.load_state_dict(c['optimizer']);step=c['step'];rng.setstate(c['rng']);torch.set_rng_state(c['torch_rng']);torch.cuda.set_rng_state_all(c['cuda_rng']);best=c['best'];hist=c['history'];del c
  start=time.monotonic();last=start;last_guard=0;targets=0;limit=step+(a.probe_steps if a.command=='probe' else a.max_steps);deadline=start+(a.minutes*60 if a.command!='probe' else 1e9)
  if a.command!='probe' and step==0:
   met=evaluate(model,dev,codec,ids,remap,a);best=sum(v['nll'] for v in met.values())/2;hist.append({'step':0,'dev':met});snapshot(a.out/'best.uno');snapshot(a.out/'latest.uno');print('BASELINE',met,flush=True)
  while step<limit and time.monotonic()<deadline:
   if a.device=='cuda' and time.monotonic()-last_guard>=2:guard();last_guard=time.monotonic()
   kind='dialogue' if step%3==2 else 'language';model.train();r=batch(train[kind],rng,codec,a.context,a.batch,a.device,remap);opt.zero_grad(set_to_none=True);loss,n=objective(model,r,ids);require(bool(torch.isfinite(loss)),'NONFINITE_LOSS');loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();model.project(opt);step+=1;targets+=n;print('STEP',step,kind,'loss',round(float(loss.detach()),4),'targets',n,flush=True)
   if a.command!='probe' and (step%100==0 or time.monotonic()-last>=300):
    met=evaluate(model,dev,codec,ids,remap,a);score=sum(v['nll'] for v in met.values())/2;hist.append({'step':step,'dev':met});print('DEV',met,flush=True)
    if score<best:best=score;snapshot(a.out/'best.uno')
    snapshot(a.out/'latest.uno');last=time.monotonic()
  if a.command!='probe':
   met=evaluate(model,dev,codec,ids,remap,a);score=sum(v['nll'] for v in met.values())/2;hist.append({'step':step,'dev':met});print('DEV',met,flush=True)
   if score<best:best=score;snapshot(a.out/'best.uno')
   snapshot(a.out/'latest.uno')
  if a.command=='probe':
   met=evaluate(model,dev,codec,ids,remap,a);print('PROBE_DEV',met,flush=True)
  result={'step':step,'targets':targets,'seconds':time.monotonic()-start,'parameters':model.count,'peak_cuda_mib':torch.cuda.max_memory_reserved()/2**20 if a.device=='cuda' else None,'status':'MECHANISM_ONLY_NOT_QUALITY' if a.command=='probe' else 'RESEARCH_ONLY'}
  if a.command=='probe' and a.device=='cuda':
   guard();require(step>=3,'PROBE_NEEDS_BOTH_OBJECTIVES');result.update(status='CUDA_MECHANISM_ONLY_NOT_QUALITY',config=cfg);tmp=ROOT/'cuda-probe.json.tmp';tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,ROOT/'cuda-probe.json')
  print(json.dumps(result),flush=True)
 finally:
  if lock:lock.unlink()
if __name__=='__main__':main()
