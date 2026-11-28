"""CPU language-only research trial, independent B2-512. Resume on same host."""
import argparse,collections,hashlib,json,math,os,pathlib,random,tempfile,time,torch
from torch.nn import functional as F
from model import B2
ROOT=pathlib.Path(__file__).resolve().parent
CFG={'d':512,'seed':20261125512,'lr':.001,'threads':3,'batch':4,'seq':16,'K':1,'stage':'T1-language-only-pilot-fixed-full-route','dtype':'float32','optimizer':'Adam-no-weight-decay','version':1,'torch':str(torch.__version__)}

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def model_hash(m):
 h=hashlib.sha256()
 for n,p in m.state_dict().items():h.update(n.encode());h.update(p.detach().numpy().tobytes())
 return h.hexdigest()
def manifest():
 return {'config':CFG,'files':{n:sha(ROOT/n) for n in ['model.py','train.py','tokenizer.py','tokenizer.json','data.json','corpus_manifest.json','math/UNO_ASTRA_MATH_AUDIT_RETURN_20261124.zip','corpus/good.txt','corpus/ram.txt','corpus/questions.txt','corpus/storm.txt']}}
def atomic_save(path,obj):
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:torch.save(obj,f);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path);d=os.open(path.parent,os.O_RDONLY);os.fsync(d);os.close(d)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def write_json(p,obj):
 data=json.dumps(obj,ensure_ascii=False,indent=2).encode();fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def load_data():
 tok=json.loads((ROOT/'tokenizer.json').read_text());data=json.loads((ROOT/'data.json').read_text());ids=torch.tensor(tok['active_ids']);remap=torch.full((32768,),-1,dtype=torch.long);remap[ids]=torch.arange(len(ids));return data,ids,remap

def windows(doc,L):
 for i in range(0,len(doc)-1,L):
  yield doc[i:min(i+L+1,len(doc))]

@torch.no_grad()
def evaluate(m,docs,ids,remap):
 m.eval();total=0;loss=0.;correct=0;L=CFG['seq'];rows=[w for doc in docs for w in windows(doc,L)]
 for i in range(0,len(rows),CFG['batch']):
  rs=rows[i:i+CFG['batch']];x=torch.tensor([r[:-1]+[256]*(L-len(r)+1) for r in rs]);y=torch.tensor([r[1:]+[0]*(L-len(r)+1) for r in rs]);mask=torch.arange(L)[None,:]<torch.tensor([len(r)-1 for r in rs])[:,None];ys=remap[y][mask];z=m.language(x,ids,CFG['K'])[mask];loss+=F.cross_entropy(z,ys,reduction='sum').item();correct+=int((z.argmax(-1)==ys).sum());total+=len(ys)
 return {'tokens':total,'nll':loss/total,'perplexity':math.exp(loss/total),'accuracy':correct/total,'correct':correct}

def classical(data,ids):
 vocab=len(ids);counts=collections.Counter(t for d in data['train'] for t in d[1:]);pairs=collections.Counter((a,b) for d in data['train'] for a,b in zip(d,d[1:]));from_count=collections.Counter(a for d in data['train'] for a in d[:-1]);n=sum(counts.values());predictions=[(a,b) for d in data['dev'] for a,b in zip(d,d[1:])];N=len(predictions);alpha=.1
 uni=sum(-math.log((counts[b]+alpha)/(n+alpha*vocab)) for a,b in predictions)/N
 bi=sum(-math.log((pairs[a,b]+alpha)/(from_count[a]+alpha*vocab)) for a,b in predictions)/N
 return {'uniform_nll':math.log(vocab),'unigram_nll':uni,'bigram_nll':bi,'unigram_ppl':math.exp(uni),'bigram_ppl':math.exp(bi),'alpha':alpha,'dev_tokens':N}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--steps',type=int,default=20);ap.add_argument('--resume',action='store_true');ap.add_argument('--eval-every',type=int,default=20);args=ap.parse_args();assert args.steps>=1
 torch.set_num_threads(CFG['threads']);torch.set_num_interop_threads(1);torch.manual_seed(CFG['seed']);random.seed(CFG['seed']);torch.use_deterministic_algorithms(True)
 data,ids,remap=load_data();m=B2(CFG['d']);o=torch.optim.Adam(m.parameters(),lr=CFG['lr']);base=model_hash(m);start=0;history=[];metrics=[];path=ROOT/'latest.uno';man=manifest()
 if args.resume:
  c=torch.load(path,map_location='cpu',weights_only=True);assert c['manifest']==man;assert c['initial_hash']==base;assert c['cursor']==c['step']*CFG['batch']*CFG['seq'];m.load_state_dict(c['weights']);o.load_state_dict(c['optimizer']);start=c['step'];history=c['history'];metrics=c['metrics'];torch.set_rng_state(c['torch_rng']);random.setstate(c['python_rng']);del c
 elif path.exists():raise ValueError('Refusing to overwrite existing checkpoint without --resume')
 def save(step):
  atomic_save(path,dict(manifest=man,weights=m.state_dict(),optimizer=o.state_dict(),step=step,cursor=step*CFG['batch']*CFG['seq'],torch_rng=torch.get_rng_state(),python_rng=random.getstate(),initial_hash=base,history=history,metrics=metrics))
  write_json(ROOT/'metrics.json',dict(config=CFG,model_parameters=m.count,tensors=len(m.p),initial_hash=base,baseline=classical(data,ids),step=step,metrics=metrics,history=history))
 if start==0 and not metrics:
  met=evaluate(m,data['dev'],ids,remap);metrics.append({'step':0,'dev':met});print('BASELINE',met,'CLASSICAL',classical(data,ids),flush=True)
  save(0)
 before=time.monotonic()
 for s in range(start+1,start+args.steps+1):
  m.train();L=CFG['seq'];rows=[]
  for _ in range(CFG['batch']):
   doc=random.choice(data['train']);i=random.randrange(len(doc)-L);rows.append(doc[i:i+L+1])
  x=torch.tensor([r[:-1] for r in rows]);y=remap[torch.tensor([r[1:] for r in rows])];o.zero_grad(set_to_none=True);logits=m.language(x,ids,CFG['K']);loss=F.cross_entropy(logits.flatten(0,1),y.flatten());loss.backward();grad=torch.nn.utils.clip_grad_norm_(m.parameters(),1.);assert torch.isfinite(grad) and torch.isfinite(loss);o.step();m.project(o);history.append({'step':s,'loss':float(loss.detach()),'grad_norm':float(grad),'tokens':CFG['batch']*L})
  if s%5==0:print('STEP',s,'loss',history[-1]['loss'],'elapsed',round(time.monotonic()-before,2),flush=True)
  if s%args.eval_every==0 or s==start+args.steps:
   met=evaluate(m,data['dev'],ids,remap);metrics.append({'step':s,'dev':met});print('DEV',s,met,flush=True)
  if s%10==0 or s==start+args.steps:save(s)
 print('END',start+args.steps,'seconds',round(time.monotonic()-before,2),flush=True)
if __name__=='__main__':main()
