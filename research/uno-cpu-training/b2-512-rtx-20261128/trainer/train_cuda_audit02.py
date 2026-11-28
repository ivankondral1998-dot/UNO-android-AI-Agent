"""New research phase of existing B2-512; language/assistant only, no S4 write/S6.
Original checkpoint and tokenizer pinned. New corpus/optimizer, never old exact resume.
"""
import argparse, hashlib, io, json, math, os, random, subprocess, sys, time, tempfile, heapq, contextlib, collections, shutil
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import torch
from torch.nn import functional as F
from model_audit import B2
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
  p=ROOT/'tokenizer.json';require(sha(p)==TOK_SHA,'TOKENIZER_MISMATCH');t=json.loads(p.read_text());self.ids=t['active_ids'];self.allowed=set(self.ids);self.rules={(a,b):(i,c) for i,(a,b,c) in enumerate(t['merges'])};self.bos=t['bos'];self.eos=t['eos'];self.tokens={int(k):bytes.fromhex(v) for k,v in t['tokens_hex'].items()}
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
  self.p=p;self.kind=kind;self.offsets=[];self.cache=collections.OrderedDict();self.cache_tokens=0
  with p.open('rb') as f:
   while True:
    pos=f.tell();line=f.readline()
    if not line:break
    if line.strip():self.offsets.append(pos)
  require(bool(self.offsets),'EMPTY '+str(p))
 def get(self,i):
  with self.p.open('rb') as f:f.seek(self.offsets[i]);return json.loads(f.readline())
 def encoded(self,i,codec):
  if i in self.cache:
   self.cache.move_to_end(i);return self.cache[i]
  t,m=codec.record(self.get(i),self.kind);targets=[j for j in range(1,len(t)) if m[j]];r=(t,m,targets)
  if len(t)<=200000:
   while self.cache and (len(self.cache)>=2048 or self.cache_tokens+len(t)>500000):
    _,old=self.cache.popitem(last=False);self.cache_tokens-=len(old[0])
   self.cache[i]=r;self.cache_tokens+=len(t)
  return r
 def row(self,rng,codec,L,first_only=False):
  for _ in range(100):
   t,m,targets=self.encoded(rng.randrange(len(self.offsets)),codec)
   if not targets:continue
   # For dialogue, sample answer onset on half of training draws. Keep the
   # preceding user/role context rather than randomly cropping it away.
   anchored=self.kind=='dialogue' and (first_only or rng.random()<.5)
   if anchored:
    starts=[j for j in targets if not m[j-1]];require(bool(starts),'NO_ASSISTANT_START')
    i=rng.choice(starts);start=max(0,i-max(1,3*L//4))
   else:
    i=rng.choice(targets);lo=max(0,i-L);hi=min(i-1,max(0,len(t)-L-1));start=rng.randint(lo,max(lo,hi))
   a=t[start:start+L+1];b=m[start:start+L+1];k=len(a)-1
   if first_only:b=[j+start==i for j in range(len(a))]
   require(k>0 and any(b[1:]),'TARGET_WINDOW_EMPTY')
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
@torch.no_grad()
def validate_optimizer(model,opt,ids):
 inactive=torch.ones(32768,dtype=torch.bool,device=ids.device);inactive[ids]=False
 for name,p in model.p.items():
  for k,v in opt.state.get(p,{}).items():
   if torch.is_tensor(v):
    require(bool(torch.isfinite(v).all()),'OPTIMIZER_NONFINITE '+name+' '+k)
    if name in ('E_text','b_text') and v.shape==p.shape:
     require(not bool(v[inactive].any()),'OPTIMIZER_INACTIVE_ROWS '+name+' '+k)
@contextlib.contextmanager
def output_lock(out):
 # OS releases the lock on process death. The file itself persists harmlessly.
 path=out/'active.lock'
 with path.open('a+b') as f:
  if path.stat().st_size==0:f.write(b'0');f.flush()
  f.seek(0)
  if os.name=='nt':
   import msvcrt
   msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
  else:
   import fcntl
   fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:yield
  finally:
   f.seek(0)
   if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
def guard():
 s=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True,timeout=5).strip().splitlines();require(len(s)==1,'GPU_COUNT');t,m=map(float,s[0].split(','));require(math.isfinite(t) and math.isfinite(m) and 0<=t<78 and 0<=m<6500,'GPU_GUARD_STOP '+str(s));return [t,m]
def save(p,obj,keep_previous=False):
 b=io.BytesIO();torch.save(obj,b);body=b.getbuffer();fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:f.write(HEADER);f.write(hashlib.sha256(body).hexdigest().encode()+b'\n');f.write(body);f.flush();os.fsync(f.fileno())
  if keep_previous and p.is_file():
   prev=p.with_name('previous.uno');fd2,old=tempfile.mkstemp(dir=p.parent,prefix='previous.',suffix='.tmp');os.close(fd2)
   try:
    # copy rather than changing current checkpoint; preserve it until publish.
    with p.open('rb') as src,open(old,'wb') as dst:
     shutil.copyfileobj(src,dst,1024*1024);dst.flush();os.fsync(dst.fileno())
    os.replace(old,prev)
   finally:
    if os.path.exists(old):os.unlink(old)
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def restore(p):
 require(1<=p.stat().st_size<=1024**3,'CHECKPOINT_SIZE')
 with p.open('rb') as f:require(f.readline()==HEADER,'CHECKPOINT_FORMAT');d=f.readline().strip();b=f.read()
 require(hashlib.sha256(b).hexdigest().encode()==d,'CHECKPOINT_HASH');return torch.load(io.BytesIO(b),map_location='cpu',weights_only=True)
def batch(records,rng,codec,L,B,device,remap,first_only=False):
 r=[records.row(rng,codec,L,first_only) for _ in range(B)];x,y,m=zip(*r);require(all(t in codec.allowed for seq in (*x,*y) for t in seq),'INVALID_TOKEN');x=torch.tensor(x,device=device);y=remap[torch.tensor(y,device=device)];m=torch.tensor(m,device=device,dtype=torch.bool);require(bool(m.any()) and bool((y>=0).all()),'MASK_OR_ID');return x,y,m
def objective(model,r,ids):
 x,y,m=r;z=model.language(x,ids,1)[m];return F.cross_entropy(z,y[m]),int(m.sum())
@torch.no_grad()
def evaluate(model,sets,codec,ids,remap,a):
 model.eval();res={}
 for k,ds in [*sets.items(),('dialogue_start',sets['dialogue'])]:
  rng=random.Random(271828);total=0;loss=0.;correct=0
  for _ in range(min(a.eval_batches,2) if k=='dialogue_start' else a.eval_batches):
   if a.device=='cuda':guard()
   x,y,m=batch(ds,rng,codec,a.context,a.batch,a.device,remap,first_only=k=='dialogue_start');z=model.language(x,ids,1)[m];target=y[m];n=len(target);total+=n;loss+=float(F.cross_entropy(z,target,reduction='sum'));correct+=int((z.argmax(-1)==target).sum())
  res[k]={'nll':loss/total,'targets':total,'accuracy':correct/total}
 return res

def selection_score(metrics):
 # Keep selection on both established objectives; onset is a separate diagnostic.
 return (metrics['language']['nll']+metrics['dialogue']['nll'])/2

@torch.no_grad()
def chat(a,codec):
 c=restore(a.out/'best.uno');cfg=c['config'];require(cfg['tokenizer']==TOK_SHA and cfg['model']==sha(ROOT/'model_audit.py'),'CHAT_MODEL_MISMATCH')
 model=B2(512);model.load_state_dict(c['weights'],strict=True);model.to(a.device);validate_weights(model);model.eval();del c
 ids=torch.tensor(codec.ids,device=a.device);L=cfg['context'];prefix=[codec.bos]+codec.encode('Пользователь: '+a.prompt)+[codec.eos]+codec.encode('UNO: ');generated=[]
 for _ in range(a.new_tokens):
  if a.device=='cuda':guard()
  part=(prefix+generated)[-L:];x=torch.tensor([part+[codec.bos]*(L-len(part))],device=a.device);idx=int(model.language(x,ids,1)[0,len(part)-1].argmax());token=codec.ids[idx]
  if token in (codec.bos,codec.eos):break
  generated.append(token)
 print('UNO:',b''.join(codec.tokens[i] for i in generated).decode('utf8',errors='replace'),flush=True)
def main():
 invoked=time.monotonic()
 p=argparse.ArgumentParser();p.add_argument('command',choices=['probe','train','resume','chat']);p.add_argument('--data',type=Path,default=Path(r'D:\UNO\corpus_prepared_v4'));p.add_argument('--out',type=Path,default=Path(r'D:\UNO\b2_cuda_run_audit02'));p.add_argument('--minutes',type=float,default=0);p.add_argument('--device',choices=['cuda','cpu'],default='cuda');p.add_argument('--batch',type=int,default=8);p.add_argument('--context',type=int,default=32);p.add_argument('--eval-batches',type=int,default=8);p.add_argument('--probe-steps',type=int,default=5);p.add_argument('--max-steps',type=int,default=100000);p.add_argument('--prompt',type=str);p.add_argument('--new-tokens',type=int,default=48);a=p.parse_args();require(1<=a.batch<=32 and 2<=a.context<=128 and 1<=a.eval_batches<=32 and 3<=a.probe_steps<=100 and 1<=a.max_steps<=1000000,'BOUNDS');require(a.command in ('probe','chat') or a.device=='cuda','CPU_PROBE_ONLY');require(a.command in ('probe','chat') or math.isfinite(a.minutes) and a.minutes>0,'MINUTES_REQUIRED');require(1<=a.new_tokens<=256,'GENERATION_BOUNDS')
 if a.device=='cuda':require(torch.cuda.is_available() and torch.cuda.device_count()==1,'CUDA_REQUIRED');guard()
 torch.set_num_threads(3);torch.manual_seed(20261128512);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
 codec=Codec();
 if a.command=='chat':
  require(a.prompt is not None,'PROMPT_REQUIRED');chat(a,codec);return
 data=a.data.resolve();digest=identity(data);ids=torch.tensor(codec.ids,device=a.device);remap=torch.full((32768,),-1,device=a.device,dtype=torch.long);remap[ids]=torch.arange(len(ids),device=a.device)
 train={k:Records(data/k/'train.jsonl',k) for k in ('language','dialogue')};dev={k:Records(data/k/'validation.jsonl',k) for k in train};require(sha(ROOT/'latest.uno')==PARENT_SHA,'PARENT_MISMATCH');parent=torch.load(ROOT/'latest.uno',map_location='cpu',weights_only=True);model=B2(512);model.load_state_dict(parent['weights'],strict=True);del parent;model.to(a.device);validate_weights(model);opt=torch.optim.Adam(model.parameters(),lr=2e-4);rng=random.Random(20261128512);step=0;best=float('inf');hist=[]
 cfg={'corpus':digest,'parent':PARENT_SHA,'tokenizer':TOK_SHA,'model':sha(ROOT/'model_audit.py'),'trainer':sha(Path(__file__)),'device':a.device,'torch':str(torch.__version__),'gpu':torch.cuda.get_device_name(0) if a.device=='cuda' else None,'context':a.context,'batch':a.batch,'eval_batches':a.eval_batches,'stage':'B2-512 fixed K1 language/assistant research, fresh Adam, audit02'}
 if a.command!='probe':
  require(time.monotonic()<invoked+a.minutes*60,'TIME_BUDGET_EXHAUSTED_DURING_SETUP')
  receipt=ROOT/'cuda-probe-audit02.json';require(receipt.is_file(),'RUN_CUDA_PROBE_FIRST');r=json.loads(receipt.read_text());require(r.get('status')=='CUDA_MECHANISM_ONLY_NOT_QUALITY' and r.get('config')==cfg,'CUDA_PROBE_MISMATCH')
  if a.command=='train':a.out.mkdir(parents=True,exist_ok=False)
  else:require(a.out.is_dir(),'NO_RUN')
  lock=output_lock(a.out)
 else:lock=contextlib.nullcontext()
 def snapshot(path):save(path,{'config':cfg,'weights':model.state_dict(),'optimizer':opt.state_dict(),'step':step,'rng':rng.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if a.device=='cuda' else [],'best':best,'history':hist},keep_previous=path.name=='latest.uno')
 with lock:
  if a.command=='resume':
   c=restore(a.out/'latest.uno');require(c['config']==cfg,'RESUME_CONFIG_MISMATCH');model.load_state_dict(c['weights'],strict=True);validate_weights(model);opt.load_state_dict(c['optimizer']);validate_optimizer(model,opt,ids);step=c['step'];require(0<=step<=a.max_steps,'RESUME_STEP_LIMIT');rng.setstate(c['rng']);torch.set_rng_state(c['torch_rng']);torch.cuda.set_rng_state_all(c['cuda_rng']);best=c['best'];hist=c['history'];del c
  start=time.monotonic();last=start;last_guard=0;targets=0;update_seconds=0.;limit=step+a.probe_steps if a.command=='probe' else a.max_steps;deadline=invoked+(a.minutes*60 if a.command!='probe' else 1e9)
  if a.command!='probe' and step==0:
   met=evaluate(model,dev,codec,ids,remap,a);best=selection_score(met);hist.append({'step':0,'dev':met});snapshot(a.out/'best.uno');snapshot(a.out/'latest.uno');print('BASELINE',met,flush=True)
  while step<limit and time.monotonic()<deadline:
   if a.device=='cuda' and time.monotonic()-last_guard>=2:guard();last_guard=time.monotonic()
   update_start=time.monotonic();kind='dialogue' if step%3==2 else 'language';model.train();r=batch(train[kind],rng,codec,a.context,a.batch,a.device,remap);opt.zero_grad(set_to_none=True);loss,n=objective(model,r,ids);require(bool(torch.isfinite(loss)),'NONFINITE_LOSS');loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();model.project(opt,active_ids=ids);step+=1;targets+=n;value=float(loss.detach());update_seconds+=time.monotonic()-update_start
   if a.command=='probe' or step<=3 or step%20==0:print('STEP',step,kind,'loss',round(value,4),'targets',n,'total_targets',targets,'targets_s',round(targets/max(update_seconds,1e-9),1),flush=True)
   if a.command!='probe' and (step%100==0 or time.monotonic()-last>=300):
    met=evaluate(model,dev,codec,ids,remap,a);score=selection_score(met);hist.append({'step':step,'dev':met});print('DEV',met,flush=True)
    if score<best:best=score;snapshot(a.out/'best.uno')
    snapshot(a.out/'latest.uno');last=time.monotonic()
    # Conservative no-improvement stop only after 2000 optimizer steps.
    if step>=2000 and len(hist)>=13:
     prior=min(selection_score(h['dev']) for h in hist[:-12]);recent=min(selection_score(h['dev']) for h in hist[-12:])
     if recent>=prior-0.005:print('VALIDATION_PLATEAU_STOP',flush=True);break
  if a.command!='probe' and (not hist or hist[-1]['step']!=step):
   met=evaluate(model,dev,codec,ids,remap,a);score=selection_score(met);hist.append({'step':step,'dev':met});print('DEV',met,flush=True)
   if score<best:best=score;snapshot(a.out/'best.uno')
   snapshot(a.out/'latest.uno')
  if a.command=='probe':
   met=evaluate(model,dev,codec,ids,remap,a);print('PROBE_DEV',met,flush=True)
  result={'step':step,'targets':targets,'seconds':time.monotonic()-start,'parameters':model.count,'update_seconds':update_seconds,'update_targets_s':targets/max(update_seconds,1e-9),'peak_cuda_mib':torch.cuda.max_memory_reserved()/2**20 if a.device=='cuda' else None,'status':'MECHANISM_ONLY_NOT_QUALITY' if a.command=='probe' else 'RESEARCH_ONLY'}
  if a.command=='probe' and a.device=='cuda':
   guard();require(step>=3,'PROBE_NEEDS_BOTH_OBJECTIVES');result.update(status='CUDA_MECHANISM_ONLY_NOT_QUALITY',config=cfg);tmp=ROOT/'cuda-probe-audit02.json.tmp';tmp.write_text(json.dumps(result,indent=2));os.replace(tmp,ROOT/'cuda-probe-audit02.json')
  print(json.dumps(result),flush=True)
if __name__=='__main__':main()
