"""Paired CPU pilot. Identical initial weights and batches, validation only."""
import argparse, json, random, sys, time
from pathlib import Path
import torch
from torch.nn import functional as F
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--steps',type=int,default=24);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.root.resolve()))
import train_cuda_fast03 as t
from fast_model03 import FastB2
torch.set_num_threads(3);torch.use_deterministic_algorithms(True)
codec=t.Codec();ids=torch.tensor(codec.ids);remap=torch.full((32768,),-1,dtype=torch.long);remap[ids]=torch.arange(len(ids));digest=t.identity(a.data.resolve());assert t.sha(a.root/'latest.uno')==t.PARENT_SHA
initial=torch.load(a.root/'latest.uno',map_location='cpu',weights_only=True)['weights'];train={k:t.Records(a.data/k/'train.jsonl',k) for k in ('language','dialogue')};dev={k:t.Records(a.data/k/'validation.jsonl',k) for k in train}
val={}
for k in ['language','dialogue','dialogue_start']:
 rng=random.Random(271828);val[k]=[t.batch(dev['dialogue' if k=='dialogue_start' else k],rng,codec,32,4,'cpu',remap,first_only=k=='dialogue_start') for _ in range(8)]
@torch.no_grad()
def evaluate(model):
 model.eval();out={}
 for k,batches in val.items():
  loss=0.;total=correct=0
  for x,y,m in batches:
   z=model.language(x,ids,1)[m];target=y[m];loss+=float(F.cross_entropy(z,target,reduction='sum'));total+=len(target);correct+=int((z.argmax(-1)==target).sum())
  out[k]={'nll':loss/total,'accuracy':correct/total,'targets':total}
 return out
def create():
 torch.manual_seed(20261128512);model=FastB2(512);model.load_state_dict(initial,strict=True);model.compact(ids);return model
model=create();baseline=evaluate(model);del model
print('BASELINE',json.dumps(baseline),flush=True)
result={'corpus_manifest':digest,'corpus_path':str(a.data),'parent_sha':t.PARENT_SHA,'trainer_sha':t.sha(a.root/'train_cuda_fast03.py'),'fast_model_sha':t.sha(a.root/'fast_model03.py'),'torch':str(torch.__version__),'device':'cpu','steps':a.steps,'batch':4,'context':32,'baseline':baseline,'runs':[]}
for seed in [11,73,2026]:
 rng=random.Random(seed);batches=[t.batch(train['dialogue' if i%3==2 else 'language'],rng,codec,32,4,'cpu',remap) for i in range(a.steps)]
 counts={k:sum(int(r[2].sum()) for i,r in enumerate(batches) if ('dialogue' if i%3==2 else 'language')==k) for k in train}
 for lr in [0.0002,0.0001,0.0004]:
  model=create();opt=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=lr,foreach=False);start=time.monotonic();norms=[];trainloss=0.;targets=0
  for r in batches:
   opt.zero_grad(set_to_none=True);loss,n=t.objective(model,r,ids);assert bool(torch.isfinite(loss));loss.backward();norms.append(float(torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)));opt.step();model.project_fast(opt);trainloss+=float(loss.detach())*n;targets+=n
  seconds=time.monotonic()-start;t.validate_weights(model);t.validate_optimizer(model,opt,ids);metrics=evaluate(model)
  run={'seed':seed,'lr':lr,'seconds':seconds,'train_targets':targets,'counts':counts,'train_nll':trainloss/targets,'gradient_clipped_fraction':sum(v>1 for v in norms)/len(norms),'dev':metrics,'mixed_nll':(metrics['language']['nll']+metrics['dialogue']['nll'])/2};result['runs'].append(run);a.out.write_text(json.dumps(result,indent=2),encoding='utf8');print('RESULT',json.dumps(run),flush=True);del model,opt
print('COMPLETE',len(result['runs']),flush=True)
