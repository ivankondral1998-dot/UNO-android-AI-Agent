"""Paired prompt-conditioning pilot, fixed F; no production claims."""
import sys,json,random,time,collections
from pathlib import Path
import torch
from torch.nn import functional as F
ROOT=Path('/mnt/data/b2_fast03'); DATA=Path('/mnt/data/uno_prep_v3_test_output_final'); OUT=Path(__file__).parent/'results.json'
sys.path.insert(0,str(ROOT));import train_cuda_fast03 as t
from fast_model03 import FastB2
torch.set_num_threads(3);torch.use_deterministic_algorithms(True)
codec=t.Codec();ids=torch.tensor(codec.ids);remap=torch.full((32768,),-1,dtype=torch.long);remap[ids]=torch.arange(len(ids));assert t.sha(ROOT/'latest.uno')==t.PARENT_SHA;digest=t.identity(DATA)
initial=torch.load(ROOT/'latest.uno',map_location='cpu',weights_only=True)['weights']
def pairs(split):
 groups=collections.defaultdict(list);seen=set()
 for line in (DATA/'dialogue'/f'{split}.jsonl').read_text().splitlines():
  r=json.loads(line);messages=r['messages'];q=codec.encode(messages[0]['text']);a=codec.encode(messages[1]['text'])[:12]
  if not q or len(a)<4 or len(q)>100 or tuple(q) in seen:continue
  seen.add(tuple(q));groups[len(q)].append((q,a))
 result=[]
 for group in groups.values():
  for q,a in group:
   for wrong,b in group:
    if q!=wrong and a[:4]!=b[:4]:result.append((q,wrong,a));break
 return result

def batch(rows):
 role=codec.encode('Пользователь: ');assistant=codec.encode('UNO: ');x=[];y=[];m=[]
 for q,wrong,a in rows:
  p=[codec.bos]+role+q+[codec.eos]+assistant;w=[codec.bos]+role+wrong+[codec.eos]+assistant
  for prefix in (p,w):
   seq=prefix+a;assert len(seq)<=129; k=len(seq)-1;x.append(seq[:-1]+[codec.bos]*(128-k));y.append(seq[1:]+[codec.eos]*(128-k));m.append([False]*(len(prefix)-1)+[True]*len(a)+[False]*(128-k))
 return torch.tensor(x),remap[torch.tensor(y)],torch.tensor(m)
def scores(model,r):
 x,y,m=r;z=model.language(x,ids,1);nll=F.cross_entropy(z.transpose(1,2),y,reduction='none');s=(nll*m).sum(1)/m.sum(1);return s[::2],s[1::2],int(((z.argmax(-1)==y)&m)[::2].sum()),int(m[::2].sum())
def create():
 torch.manual_seed(20261128512);model=FastB2(512);model.load_state_dict(initial,strict=True);model.compact(ids);return model
@torch.no_grad()
def evaluate(model,rows):
 model.eval();good=[];bad=[];correct=total=0
 for row in rows:
  a,b,c,n=scores(model,batch([row]));good+=a.tolist();bad+=b.tolist();correct+=c;total+=n
 return {'pairs':len(good),'correct_nll':sum(good)/len(good),'wrong_nll':sum(bad)/len(bad),'matched_win_rate':sum(a<b for a,b in zip(good,bad))/len(good),'token_accuracy':correct/total,'mean_margin':sum(b-a for a,b in zip(good,bad))/len(good)}
train=pairs('train');dev=pairs('validation');print('pairs',len(train),len(dev),flush=True);assert train and dev
rng=random.Random(405);draws=[batch([rng.choice(train)]) for _ in range(8)]
model=create();result={'parent':t.PARENT_SHA,'corpus_manifest':digest,'context':128,'steps':len(draws),'train_pair_pool':len(train),'validation_pair_pool':len(dev),'baseline':evaluate(model,dev),'arms':[]};del model
print('baseline',result['baseline'],flush=True);OUT.write_text(json.dumps(result,indent=2))
for weight in [0.,.5]:
 model=create();opt=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=.0004,foreach=False);start=time.monotonic()
 for r in draws:
  model.train();opt.zero_grad(set_to_none=True);good,bad,_,_=scores(model,r);loss=good.mean()+weight*F.relu(.1+good-bad).mean();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();model.project_fast(opt)
 elapsed=time.monotonic()-start;t.validate_weights(model);m=evaluate(model,dev);result['arms'].append({'weight':weight,'train_seconds':elapsed,'metrics':m});OUT.write_text(json.dumps(result,indent=2));print('arm',result['arms'][-1],flush=True);del model,opt
