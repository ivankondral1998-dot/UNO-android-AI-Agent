"""UNO F CAUSE-006: controlled write-gate ablation. Research only.

Requires unchanged uno_f_pilot.py and uno_ladder_005.py in the same folder.
No edit to originals, no use of owner's production weights, no external network.
"""
import argparse, hashlib, json, time
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as fn
from uno_ladder_005 import UnoWrap, make_batch, evaluate

CORE_SHA='d290ff97eb9c58fd609d97a3c74c2a06c2b5fc0a561a3c9489776e9f8913046a'

class WriteGateOneSlot(UnoWrap):
    """F unchanged; separate controller keeps s when op != WRITE.
    One-slot, write-only diagnostic. Does NOT implement S4 memory or S6 policy.
    """
    def sequence(self, x, **_):
        s=x.new_zeros(x.shape[0], self.m.d)
        for t in range(x.shape[1]):
            w=(x[:,t,2:3]==1.0)
            if not bool(w.any()):
                continue
            nxt,_=self.m.forward_event(x[:,t],s,[True]*self.m.nb,steps=2,alpha=.5,rho=.5)
            s=torch.where(w,nxt,s)
        return self.m.w_conf(s).squeeze(-1),None


def train(mode, args):
    torch.manual_seed(47)
    model = WriteGateOneSlot() if mode=='gate' else UnoWrap()
    model = model.to(args.device)
    opt = torch.optim.Adam(model.parameters(), lr=.001)
    rng = torch.Generator(device='cpu').manual_seed(148)
    t0=time.perf_counter();history=[]
    for step in range(1,args.steps+1):
        L=(12,24,32)[int(torch.randint(0,3,(1,),generator=rng))]
        x,y=make_batch(args.batch,L,'r1_single',rng)
        x,y=x.to(args.device),y.to(args.device)
        for pg in opt.param_groups:pg['lr']=.001*min(1.,step/100.)
        opt.zero_grad(set_to_none=True)
        z,_=model.sequence(x)
        loss=fn.binary_cross_entropy_with_logits(z,y)
        if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
        loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
        opt.step();model.after_step()
        if step%50==0 or step==args.steps:
            e=evaluate(model,args.device,'r1_single',24,2076,512)
            row={'step':step,'train_bce':round(loss.item(),6),'eval24_accuracy':e['acc']}
            history.append(row);print(mode,row,flush=True)
    outcomes={}
    for L in (12,24,48,96):
        seed=2048+L
        outcomes[str(L)]={'full':evaluate(model,args.device,'r1_single',L,seed,args.eval_samples),
                           'erased':evaluate(model,args.device,'r1_single',L,seed,args.eval_samples,erase=True)}
    weights=args.output/f'{mode}_research_only.pt'
    torch.save({k:v.detach().cpu() for k,v in model.state_dict().items()},weights)
    digest=hashlib.sha256(weights.read_bytes()).hexdigest()
    result={'status':'RESEARCH_ONLY','ablation':mode,'source_sha256':CORE_SHA,
            'steps':args.steps,'batch':args.batch,'seed':47,'device':args.device,
            'outcomes':outcomes,'history':history,'time_s':round(time.perf_counter()-t0,2),
            'weights':weights.name,'sha256':digest,
            'limitations':['one slot only','write op supplied externally','query op ignored for one slot',
                          'write gate is external and not normative S6','synthetic data only']}
    (args.output/f'{mode}_metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('FINAL',json.dumps({'mode':mode,'accuracy':{k:v['full']['acc'] for k,v in outcomes.items()},
                              'erased':{k:v['erased']['acc'] for k,v in outcomes.items()},
                              'sha256':digest}),flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['plain','gate','both'],default='gate')
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--steps',type=int,default=250)
    p.add_argument('--batch',type=int,default=32)
    p.add_argument('--eval-samples',type=int,default=2048)
    p.add_argument('--output',type=Path,default=Path('uno_f_cause_006_results'))
    a=p.parse_args()
    if min(a.steps,a.batch,a.eval_samples)<=0:p.error('positive sizes only')
    core=Path(__file__).with_name('uno_f_pilot.py')
    if not core.is_file() or hashlib.sha256(core.read_bytes()).hexdigest()!=CORE_SHA:
        raise SystemExit('STOP: original UNO F source missing or SHA mismatch')
    if a.device=='cuda' and not torch.cuda.is_available(): raise SystemExit('CUDA unavailable')
    torch.set_num_threads(min(2,torch.get_num_threads()))
    a.output.mkdir(parents=True,exist_ok=True)
    for mode in (('plain','gate') if a.mode=='both' else (a.mode,)):
        target=a.output/f'{mode}_metrics.json'
        if target.exists():raise SystemExit('STOP: refusing overwrite '+str(target))
        train(mode,a)

if __name__=='__main__':main()
