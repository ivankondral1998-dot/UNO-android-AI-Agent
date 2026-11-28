"""Research B2-128 from ASTRA_01/02 and R5.4 §§2–6; no production ABI or effects."""
import argparse, hashlib, io, json, math, os, random, time, pathlib, tempfile
import torch
from torch import nn
import torch.nn.functional as F
R=pathlib.Path(__file__).resolve().parent; D=128; V=32768; M=128; P=4892977
WORDS='красный синий зелёный белый чёрный жёлтый серый розовый круг квадрат треугольник ромб куб шар ключ книга чашка лампа стол стул окно дверь сад дом поле лес река вода камень песок снег кот пёс птица рыба утром вечером днём ночью здесь там слева справа стоит лежит растёт течёт светит идёт бежит сидит спит пьёт ест берёт кладёт видит ищет нашёл читает пишет несёт тихо быстро медленно ярко тепло холодно большой маленький новый старый один два три четыре первый последний запомни вспомни цвет форма предмет ответ вопрос да нет привет спасибо хорошо сегодня завтра вчера'.split()
TOK={w:512+i for i,w in enumerate(WORDS)}; VALUES=list(TOK.values())[:16]; FIRST,LAST,QUERY,TEXT=256,257,258,259
CFG=dict(version='B2-128-R54-research-v1',d=D,m=M,V=V,b=64,chi=4,J=2,Kcap=2,alpha=.5,rho=.5,eps=.05,T=1.,seed=20261125,batch=8,lr=.001,threads=3,torch=str(torch.__version__),device='cpu',dtype='float32',data_version=1)
def sha(b):return hashlib.sha256(b).hexdigest()
def fs(p):return sha(p.read_bytes())
def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def atomic(p,b):
 fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p);fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def encode(s):
 import re
 return [i for part in re.findall(r'\w+|[^\w]+',s) for i in ([TOK[part]] if part in TOK else list(part.encode('utf8')))]
def decode(ids):
 rev={v:k for k,v in TOK.items()};return b''.join(bytes([i]) if i<256 else rev[i].encode() for i in ids).decode()
def gen(seed,n):
 r=random.Random(seed);rows=[]
 for i in range(n):
  if i%2==0:
   slots=[0,1,0,1];r.shuffle(slots);v=r.sample(VALUES,4);a=r.randrange(2);g=r.choice([FIRST,LAST]);ix=[k for k,b in enumerate(slots) if b==a];t=ix[0 if g==FIRST else -1];rows.append(dict(kind='memory',goal=g,tokens=v+[QUERY],slots=slots+[a],target=v[t],record=t))
  else:
   groups=[(['кот','пёс','птица'],['сидит','спит','бежит'],['тихо','здесь','там']),(['река','вода'],['течёт'],['медленно','быстро']),(['лампа'],['светит'],['ярко','тихо']),(['книга','ключ','чашка'],['лежит','стоит'],['здесь','там','слева','справа'])];a,b,c=r.choice(groups);w=[r.choice(['утром','вечером','днём','ночью','сегодня']),r.choice(a),r.choice(b),r.choice(c)];q=[TOK[x] for x in w];rows.append(dict(kind='text',goal=TEXT,tokens=q[:3]+[QUERY,QUERY],slots=[-1]*5,target=q[3],record=-1))
 return rows
def prepare():
 for name,seed,n in [('train',772811,4096),('validation',772812,128),('sealed_test',772813,256)]:
  p=R/(name+'.jsonl');b=''.join(js(x)+'\n' for x in gen(seed,n)).encode()
  if p.exists() and p.read_bytes()!=b:raise ValueError('data mismatch')
  if not p.exists():atomic(p,b)
 atomic(R/'tokenizer.json',js(dict(byte_ids=[0,255],words=TOK,roles=dict(first=FIRST,last=LAST,query=QUERY,text=TEXT),unused='reserved',V=V)).encode())
 sets={s:set((R/(s+'.jsonl')).read_text().splitlines()) for s in ('train','validation','sealed_test')};atomic(R/'data_manifest.json',js(dict(origin='synthetic original Russian word templates and memory episodes; no downloaded external text',unique={s:len(v) for s,v in sets.items()},overlap_train_validation=len(sets['train']&sets['validation']),overlap_train_sealed=len(sets['train']&sets['sealed_test']),note='shared grammar; no independent generalization claim')).encode())
class B2(nn.Module):
 def __init__(self):
  super().__init__();self.p=nn.ParameterDict();self.rules={};self.frozen={}
  def mat(n,r,c,cap=8,freeze=None):
   x=torch.empty(r,c);nn.init.xavier_uniform_(x);self.p[n]=nn.Parameter(x);self.rules[n]=(cap,False)
   if freeze is not None:self.frozen[n]=freeze
  def vec(n,r,cap=8,freeze=None,small=False):
   self.p[n]=nn.Parameter(torch.empty(r).uniform_(-.01,.01) if small else torch.zeros(r));self.rules[n]=(cap,True)
   if freeze is not None:self.frozen[n]=freeze
  mat('E_text',V,D);mat('W_audio',D,80);mat('W_image',D,768);mat('W_sensor',D,64);mat('W_meta',D,32);vec('e_modality',6*D,1,small=True);vec('b_z',D,1)
  for n in ['U_s','U_g']:mat(n,D,D,1)
  for n in ['W_q','W_k','W_v']:mat(n,M,D,2)
  mat('W_r',D,M,2)
  for j in range(2):
   for l in range(2):
    k=f'{j}_{l}';mat('A_'+k,256,D,1);mat('C_'+k,256,D,2);mat('B_'+k,64,256,.9);vec('a_'+k,256);vec('b_'+k,64)
  for n,r in [('verb',128),('outcome',128),('observable',128),('ctc',128),('belief',128),('speech',258),('V',1),('risk',1),('halt',1),('conf',1)]:
   freeze=list(range(24,128)) if n=='verb' else list(range(3))+list(range(24,128)) if n in ('outcome','observable') else None;mat('W_'+n,r,D,freeze=freeze);vec('b_'+n,r,freeze=freeze)
  vec('b_text',V);mat('W_mask',2,2*D+4);vec('b_mask',2);mat('W_wake',1,32);vec('b_wake',1)
  assert sum(p.numel() for p in self.parameters())==P;self.project()
  for n,rows in self.frozen.items():self.p[n].register_hook(lambda g,rows=rows:g.index_fill(0,torch.tensor(rows),0))
 @torch.no_grad()
 def project(self,opt=None):
  for n,p in self.p.items():
   cap,box=self.rules[n]
   if not torch.isfinite(p).all():raise ValueError('nonfinite '+n)
   if box:p.clamp_(-cap,cap)
   else:
    x=p.double();mask=x.abs().sum(-1)>cap
    if mask.any():
     a=x[mask];u=a.abs().sort(-1,descending=True).values;cs=u.cumsum(-1)-cap*(1-2e-7);k=torch.arange(1,u.shape[-1]+1,dtype=u.dtype);rho=(u>cs/k).sum(-1).clamp_min(1);theta=cs.gather(1,(rho-1)[:,None])/rho[:,None];p[mask]=(a.sign()*(a.abs()-theta).clamp_min(0)).float()
    if (p.double().abs().sum(-1)>cap).any():raise ValueError('decoded cap '+n)
   if n in self.frozen:
    p[self.frozen[n]]=0
    if opt:
     for v in opt.state.get(p,{}).values():
      if torch.is_tensor(v) and v.shape==p.shape:v[self.frozen[n]]=0
 def lin(self,x,w,b=None):return F.linear(x,self.p[w],self.p[b] if b else None)
 def event(self,tok,s,g,meta,bank,serial,mode='full'):
  p=self.p;bs=len(tok);z0=torch.tanh(p['E_text'][tok]+self.lin(s,'U_s')+self.lin(g,'U_g')+self.lin(meta,'W_meta')+p['e_modality'].view(6,D)[0]+p['b_z']);q=torch.tanh(self.lin(z0,'W_q'));scores=None
  if bank and mode!='off':
   keys,vals=map(lambda a:torch.stack(a,1),zip(*bank));scores=torch.einsum('bm,bnm->bn',q,keys)/math.sqrt(M);r=torch.einsum('bn,bnm->bm',scores.softmax(-1),vals)
  else:r=torch.zeros(bs,M)
  z=torch.tanh(z0+self.lin(r,'W_r'));h=.5*s+.5*z;order=[serial%2,1-serial%2];c=torch.ones(bs,4);ell=self.lin(torch.cat((z,s,c),-1),'W_mask','b_mask')[:,order];pr=.025+.95*(ell.cumsum(-1)/torch.tensor([1.,math.sqrt(2)])).softmax(-1);pick=torch.ones(bs,dtype=torch.long) if getattr(self,'fixed_route',False) else torch.multinomial(pr.detach(),1).squeeze(1);lp=torch.zeros(bs) if getattr(self,'fixed_route',False) else pr.gather(1,pick[:,None]).log().squeeze(1);cost=(pick+1).float()*163840
  cache={};active={}
  for pos,j in enumerate(order):
   ix=torch.where(pick>=pos)[0];active[j]=ix
   if len(ix):
    for l in range(2):cache[j,l]=self.lin(z[ix],f'C_{j}_{l}',f'a_{j}_{l}')
  def step(h,cont=None):
   parts=[]
   for j in range(2):
    ix=active[j];sel=torch.ones(len(ix),dtype=torch.bool) if cont is None else cont[ix];ix2=ix[sel];old=h[:,j*64:(j+1)*64]
    if len(ix2):
     br=[]
     for l in range(2):
      u=torch.tanh(self.lin(h[ix2],f'A_{j}_{l}')+cache[j,l][sel]);br.append(torch.tanh(self.lin(u,f'B_{j}_{l}',f'b_{j}_{l}')))
     old=old.index_copy(0,ix2,.5*old[ix2]+.25*(br[0]+br[1]))
    parts.append(old)
   return torch.cat(parts,-1)
  h=step(h);halt=torch.sigmoid(self.lin(h,'W_halt','b_halt').squeeze(1));stop=torch.zeros(bs,dtype=torch.bool) if getattr(self,'fixed_route',False) else torch.rand(bs)<halt.detach();lp=lp if getattr(self,'fixed_route',False) else lp+torch.where(stop,halt.clamp_min(1e-8).log(),(1-halt).clamp_min(1e-8).log());cost=cost+(~stop).float()*(pick+1).float()*98304;h=step(h,~stop)
  return h,scores,lp,cost
 def episode(self,rows,mode='full'):
  bs=len(rows);s=torch.zeros(bs,D);g=s.clone();meta=torch.zeros(bs,32);meta[:,0]=1;meta[:,4]=1;g,_,lp,cost=self.event(torch.tensor([r['goal'] for r in rows]),s,g,meta,[],0);s=torch.zeros_like(g);bank=[];scores=None;mem=rows[0]['kind']=='memory';assert all((r['kind']=='memory')==mem for r in rows)
  for t in range(5):
   meta=torch.zeros(bs,32);meta[:,0]=1;meta[:,4]=1;meta[:,14]=t/5
   if mem:meta[:,16]=torch.tensor([2*r['slots'][t]-1 for r in rows]);meta[:,24]=1
   s,scores,l,c=self.event(torch.tensor([r['tokens'][t] for r in rows]),s,g,meta,bank,t+1,mode);lp=lp+l;cost=cost+c
   if mem and t<4:bank.append((torch.tanh(self.lin(s,'W_k')),torch.tanh(self.lin(s,'W_v'))))
  return self.lin(s,'E_text','b_text'),scores,lp,cost
 def objective(self,rows):
  logits,scores,lp,cost=self.episode(rows);y=torch.tensor([r['target'] for r in rows]);ce=F.cross_entropy(logits,y,reduction='none');aux=F.cross_entropy(scores,torch.tensor([r['record'] for r in rows]),reduction='none') if scores is not None else torch.zeros_like(ce);task=ce+.3*aux;reward=task.detach()+.01*cost/(6*524288);return task.mean()+((reward-10.)*lp).mean(),ce,aux,cost

def load(s):return [json.loads(x) for x in (R/(s+'.jsonl')).read_text().splitlines()]
def manifest():return {**CFG,'source':fs(R/'experiment.py'),'tokenizer':fs(R/'tokenizer.json'),'data':{s:fs(R/(s+'.jsonl')) for s in ('train','validation','sealed_test')}}
def modelhash(m):
 h=hashlib.sha256()
 for n,p in m.state_dict().items():h.update(n.encode());h.update(p.detach().numpy().tobytes())
 return h.hexdigest()
def save(m,o,s,h,c,initial,grad):
 b=io.BytesIO();torch.save(dict(config=c,weights=m.state_dict(),optimizer=o.state_dict(),step=s,cursor=s*CFG['batch'],cpu_rng=torch.get_rng_state(),python_rng=random.getstate(),history=h,initial_hash=initial,gradient_tensors=sorted(grad)),b);v=b.getvalue();atomic(R/'latest.uno',b'UNO-B2-128/V1\n'+sha(v).encode()+b'\n'+v)
def restore(p):
 a,b,c=p.read_bytes().split(b'\n',2)
 if a!=b'UNO-B2-128/V1' or sha(c).encode()!=b:raise ValueError('checkpoint integrity')
 return torch.load(io.BytesIO(c),map_location='cpu',weights_only=True)
@torch.no_grad()
def evaluate(m,rows):
 rng=torch.get_rng_state();out={}
 try:
  for kind in ('memory','text'):
   rr=[r for r in rows if r['kind']==kind]
   for mode in ('full','off') if kind=='memory' else ('full',):
    torch.manual_seed(19191);n=ok=ret=0;ce=cost=0.
    for i in range(0,len(rr),8):
     x=rr[i:i+8];logits,score,_,mac=m.episode(x,mode);y=torch.tensor([r['target'] for r in x]);n+=len(x);ok+=int((logits.argmax(-1)==y).sum());ce+=float(F.cross_entropy(logits,y,reduction='sum'));cost+=float(mac.sum());ret+=int((score.argmax(-1)==torch.tensor([r['record'] for r in x])).sum()) if score is not None else 0
    out[kind+'_'+mode]=dict(n=n,correct=ok,ce=ce/n,retrieval_correct=ret if kind=='memory' and mode=='full' else None,mean_s5_mac=cost/n)
 finally:torch.set_rng_state(rng)
 return out

def setup():torch.set_num_threads(CFG['threads']);torch.use_deterministic_algorithms(True);torch.manual_seed(CFG['seed']);random.seed(CFG['seed'])
def train(steps,resume):
 setup();prepare();cfg=manifest();m=B2();o=torch.optim.Adam(m.parameters(),lr=CFG['lr']);tr=load('train');val=load('validation');h=[];start=0;initial=modelhash(m);grad=set()
 if resume:
  a=restore(R/'latest.uno');assert a['config']==cfg and a['cursor']==a['step']*CFG['batch'];m.load_state_dict(a['weights']);o.load_state_dict(a['optimizer']);torch.set_rng_state(a['cpu_rng']);random.setstate(a['python_rng']);start=a['step'];h=a['history'];initial=a['initial_hash'];grad=set(a['gradient_tensors'])
 else:
  if (R/'latest.uno').exists():raise ValueError('existing checkpoint; use --resume')
  h.append(dict(step=0,validation=evaluate(m,val)));save(m,o,0,h,cfg,initial,grad)
 print('START',start,'params',P,flush=True);t=time.monotonic()
 for s in range(start+1,start+steps+1):
  pool=tr[(s-1)%2::2];pos=((s-1)//2*CFG['batch'])%len(pool);rows=[pool[(pos+i)%len(pool)] for i in range(CFG['batch'])];o.zero_grad(set_to_none=True);loss,ce,aux,cost=m.objective(rows);assert torch.isfinite(loss);loss.backward();grad.update(n for n,p in m.p.items() if p.grad is not None and bool((p.grad!=0).any()));norm=torch.nn.utils.clip_grad_norm_(m.parameters(),1.,error_if_nonfinite=True);o.step();m.project(o);h.append(dict(step=s,kind=rows[0]['kind'],ce=float(ce.detach().mean()),retrieval_ce=float(aux.detach().mean()),surrogate=float(loss.detach()),gradient_norm=float(norm),mean_s5_mac=float(cost.mean())))
  if s%20==0 or s==start+steps:
   h[-1]['validation']=evaluate(m,val);save(m,o,s,h,cfg,initial,grad);atomic(R/'metrics.json',js(dict(step=s,initial_weight_sha256=initial,current_weight_sha256=modelhash(m),gradient_tensors=sorted(grad),params=P,free=P-318*(D+1),history=h)).encode());print('STEP',s,'CE',h[-1]['ce'],'VAL',h[-1]['validation'],'seconds',round(time.monotonic()-t,2),flush=True)
  elif s%5==0:save(m,o,s,h,cfg,initial,grad)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--steps',type=int,default=20);a.add_argument('--resume',action='store_true');x=a.parse_args();train(x.steps,x.resume)
