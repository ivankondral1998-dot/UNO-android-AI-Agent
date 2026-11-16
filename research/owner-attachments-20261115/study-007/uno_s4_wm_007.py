"""UNO S4 working-memory split probe (research only).

Uses exact original UNO F S4/S5 implementation from 001 unchanged. Stores raw
observed WRITE values outside F (deterministic addressable memory), while F
continues processing every event. At QUERY, passes all eligible semantic
vectors to F.forward_event(keys=...,values=...) so q, attention, Wr and S5 are
computed by the original S4/S5 implementation. Not a learned WRITE policy.

No owner's GPU weights, no saved model overwritten, no network.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F
from uno_f_pilot import UnoF, project_l1_
from uno_ladder_005 import make_batch, evaluate as ladder_evaluate

SOURCE_SHA='d290ff97eb9c58fd609d97a3c74c2a06c2b5fc0a561a3c9489776e9f8913046a'
SEED_SHA='a2112184069067831eebe3c6e3a47dd9911b23c349c16ce217856b5bc12335ba'
RUNGS=('r2_two','r3_three','r4_overwrite')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slot_codes(rung):
    return (-1.,1.) if rung=='r2_two' else (-1.,0.,1.)


def bank_codes(n, dim=128, gain=.99):
    """Fixed, public semantic slot keys. They encode addresses, not answers."""
    # Deterministic orthogonal columns of +/-1. Each key norm=gain*sqrt(dim).
    k=torch.arange(dim)
    rows=[torch.where(k%2==0,1.,-1.),
          torch.where((k//2)%2==0,1.,-1.),
          torch.where((k//4)%2==0,1.,-1.)]
    return torch.stack(rows[:n],0)*gain


class SeparatedS4(nn.Module):
    def __init__(self,rung='r2_two',mode='s4',init_file=None,key_gain=.99):
        super().__init__()
        assert rung in RUNGS and mode in ('s4','s4_goal','no_memory')
        self.rung,self.mode=rung,mode
        self.core=UnoF()
        if init_file is not None:
            saved=torch.load(init_file,map_location='cpu',weights_only=True)
            self.core.load_state_dict({k.removeprefix('m.'):v for k,v in saved.items()},strict=True)
        # Freeze original F computation and 006-trained head. Allow only S4 query,
        # S4 read projection, and a separate diagnostic answer head to learn.
        for p in self.core.parameters():p.requires_grad_(False)
        for sub in (self.core.Wq,self.core.Wr):
            for p in sub.parameters():p.requires_grad_(mode!='no_memory')
        for p in self.core.Ug.parameters():p.requires_grad_(mode=='s4_goal')
        self.readout=nn.Linear(self.core.d,1)
        nn.init.normal_(self.readout.weight,std=.01)
        nn.init.zeros_(self.readout.bias)
        self.register_buffer('key_bank',bank_codes(len(slot_codes(rung)),self.core.m,gain=key_gain))
        # Fixed value vector: stores only the observed scalar WRITE value.
        i=torch.arange(self.core.m)
        sign=torch.where(i%2==0,1.,-1.)
        self.register_buffer('value_axis',sign)

    def after_step(self):
        with torch.no_grad():
            if self.mode!='no_memory':
                project_l1_(self.core.Wq.weight,2.0)
                project_l1_(self.core.Wr.weight,2.0)
                if self.mode=='s4_goal':project_l1_(self.core.Ug.weight,1.0)
            project_l1_(self.readout.weight,8.0)
            self.readout.bias.clamp_(-8.,8.)

    def scan(self,x):
        """WRITE/NOISE processed by F on *every* step; WM updated separately."""
        b,L,_=x.shape
        codes=slot_codes(self.rung)
        values=x.new_zeros((b,len(codes)))
        seen=torch.zeros((b,len(codes)),device=x.device,dtype=torch.bool)
        s=x.new_zeros((b,self.core.d))
        for t in range(L-1):
            f=x[:,t]
            is_write=f[:,2]==1
            for k,code in enumerate(codes):
                hit=is_write & (f[:,1]==code)
                values[:,k]=torch.where(hit,f[:,0],values[:,k])
                seen[:,k]|=hit
            # Important: core NOT gated or skipped; all noise changes compute state.
            # Core is frozen for this isolated S4 readout experiment. No TBPTT.
            with torch.no_grad():
                s,_=self.core.forward_event(f,s,[True]*self.core.nb,steps=2,alpha=.5,rho=.5)
        return values,seen,s

    def encode_goal(self,f):
        """The requested slot index, NOT its content/answer, encoded into S4's g."""
        b=f.shape[0]
        goal=f.new_zeros(b,self.core.d)
        for j,code in enumerate(slot_codes(self.rung)):
            goal[:,j]=torch.where(f[:,1]==code,1.0,0.0)
        return goal

    def sequence(self,x,**_):
        if x.ndim!=3 or x.shape[-1]!=3:raise ValueError('input shape')
        values,seen,s=self.scan(x)
        if not bool(seen.all()):raise ValueError('missing writes in episode')
        f=x[:,-1]
        if not bool((f[:,2]==-1).all()):raise ValueError('query op required')
        if self.mode!='no_memory':
            keys=self.key_bank.unsqueeze(0).expand(len(x),-1,-1)
            semantic_values=values[:,:,None]*self.value_axis[None,None,:]
        else:
            keys=semantic_values=None
        goal=self.encode_goal(f) if self.mode=='s4_goal' else None
        h,trace=self.core.forward_event(f,s,[True]*self.core.nb,steps=2,
                                         alpha=.5,rho=.5,goal=goal,keys=keys,values=semantic_values)
        if self.training and self.mode!='no_memory':
            # Auxiliary supervised address loss uses only the public QUERY address,
            # never the target answer. The actual read remains the original S4.
            zero=f.new_zeros(len(f),32)
            z0=torch.tanh(self.core.E(f)+self.core.Us(s)+
                self.core.Ug(goal if goal is not None else torch.zeros_like(s))+
                self.core.Wmeta(zero)+self.core.e+self.core.bz)
            q=torch.tanh(self.core.Wq(z0))
            trace['route_logits']=(keys*q[:,None,:]).sum(-1)/math.sqrt(self.core.m)
            ix=torch.zeros(len(f),device=x.device,dtype=torch.long)
            for j,code in enumerate(slot_codes(self.rung)):
                ix=torch.where(f[:,1]==code,j,ix)
            trace['route_target']=ix
        return self.readout(h).squeeze(-1),trace


def exact_oracle(x,rung):
    """Check source data, not an UNO result. Never receives generator label."""
    n=len(slot_codes(rung)); mem=x.new_zeros((len(x),n))
    for t in range(x.shape[1]-1):
        f=x[:,t];w=f[:,2]==1
        for j,code in enumerate(slot_codes(rung)):
            mem[:,j]=torch.where(w & (f[:,1]==code),f[:,0],mem[:,j])
    idx=torch.zeros(len(x),device=x.device,dtype=torch.long)
    for j,code in enumerate(slot_codes(rung)):
        idx=torch.where(x[:,-1,1]==code,j,idx)
    return mem.gather(1,idx[:,None]).squeeze(-1)


def score(model,rung,length,seed,n,device,erase=False,chunk=128,guard=None):
    model.eval(); gen=torch.Generator().manual_seed(seed)
    good=0;ce=0.;samples=0
    with torch.no_grad():
        while samples<n:
            if guard is not None:guard()
            b=min(chunk,n-samples)
            x,y=make_batch(b,length,rung,gen,erase=erase)
            logits,_=model.sequence(x.to(device))
            y=y.to(device)
            good+=int(((logits>=0)==(y>.5)).sum())
            ce+=float(F.binary_cross_entropy_with_logits(logits,y,reduction='sum'))
            samples+=b
    return {'acc':round(good/samples,4),'bce':round(ce/samples,4),'n':samples}


def atomic_save(obj,path):
    path=Path(path)
    temp=path.with_name(path.name+'.partial')
    torch.save(obj,temp)
    os.replace(temp,path)


def atomic_json(obj,path):
    path=Path(path)
    temp=path.with_name(path.name+'.partial')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temp,path)


def gpu_guard(device,max_temp,max_mib):
    if device.type!='cuda':return None
    try:
        line=subprocess.check_output(['nvidia-smi',
            '--query-gpu=temperature.gpu,memory.used',
            '--format=csv,noheader,nounits'],text=True,timeout=5).splitlines()[0]
        temp,used=map(float,line.split(','))
    except Exception as exc:
        raise RuntimeError('CUDA monitoring failed; stopped: '+str(exc)) from exc
    if temp>=max_temp or used>=max_mib:
        raise RuntimeError(f'GPU guard stopped: temp={temp}C used={used}MiB')
    return {'temp_c':temp,'used_mib':used}


def attention_probe(model,rung,device,seed=8127,n=256):
    """Independent readout of exactly the q and score formula used in UnoF.forward_event."""
    model.eval();rng=torch.Generator().manual_seed(seed)
    x,_=make_batch(n,24,rung,rng)
    x=x.to(device)
    with torch.no_grad():
        _values,_seen,s=model.scan(x)
        f=x[:,-1,:]
        c=model.core
        g=model.encode_goal(f) if model.mode=='s4_goal' else torch.zeros_like(s)
        z0=torch.tanh(c.E(f)+c.Us(s)+c.Ug(g)+c.e+c.bz) # meta exactly zero
        q=torch.tanh(c.Wq(z0))
        keys=model.key_bank[None,:,:].expand(n,-1,-1)
        prob=torch.softmax((keys*q[:,None,:]).sum(-1)/math.sqrt(c.m),dim=1)
        target=torch.zeros(n,dtype=torch.long,device=device)
        for j,code in enumerate(slot_codes(rung)):
            target=torch.where(f[:,1]==code,j,target)
        selected=prob.gather(1,target[:,None]).squeeze(1)
        return {'correct_key_top1':round((prob.argmax(1)==target).float().mean().item(),4),
                'correct_key_probability':round(selected.mean().item(),4),
                'uniform_baseline':round(1./len(slot_codes(rung)),4),
                'samples':n}


def run(args):
    root=Path(__file__).resolve().parent
    if sha(root/'uno_f_pilot.py')!=SOURCE_SHA:raise RuntimeError('F source SHA mismatch')
    if sha(root/'seed_F_006_research_only.pt')!=SEED_SHA:raise RuntimeError('research seed weights SHA mismatch')
    if args.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    device=torch.device(args.device)
    out=Path(args.output).resolve()
    if out.exists() and any(out.iterdir()) and not args.resume:
        raise RuntimeError('Output exists; refuse overwrite: '+str(out)+' (use --resume for checkpoints)')
    out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(min(torch.get_num_threads(),2))
    report_path=out/'metrics.json'
    if args.resume and report_path.exists():
        report=json.loads(report_path.read_text(encoding='utf8'))
        if report.get('source_sha256')!=SOURCE_SHA or report.get('seed_weights_sha256')!=SEED_SHA or report.get('seed')!=args.seed or report.get('steps')!=args.steps or report.get('batch')!=args.batch or report.get('lr')!=args.lr or report.get('rungs')!=args.rungs or report.get('modes')!=args.modes or report.get('eval_samples')!=args.eval_samples or report.get('route_loss')!=args.route_loss or report.get('key_gain')!=args.key_gain:
            raise RuntimeError('RESUME configuration mismatch')
    else:
        report={'status':'RESEARCH_ONLY','source_sha256':SOURCE_SHA,'seed_weights_sha256':SEED_SHA,
            'device':str(device),'torch':torch.__version__,'seed':args.seed,
            'steps':args.steps,'batch':args.batch,'lr':args.lr,'rungs':args.rungs,'modes':args.modes,'eval_samples':args.eval_samples,'route_loss':args.route_loss,'key_gain':args.key_gain,'runs':[],
            'limitations':['fixed external WRITE slot assignment; not learned',
                           'keys/values are deterministic encodings of observed data',
                           'F core frozen from CPU-trained 006; only S4 Wq/Wr and a fresh head trained',
                           'not adaptive S6; no online policy',
                           'training scans F over all events with no BPTT through frozen core',
                           'synthetic data only; no Android ABI/quality claims']}
    completed={(r['rung'],r['mode']) for r in report['runs']}
    for rung in args.rungs.split(','):
        if rung not in RUNGS:raise RuntimeError('invalid rung: '+rung)
        for mode in args.modes.split(','):
            if mode not in ('no_memory','s4','s4_goal'):raise RuntimeError('invalid mode: '+mode)
            if (rung,mode) in completed:
                print('SKIP completed',rung,mode,flush=True)
                continue
            torch.manual_seed(args.seed)
            m=SeparatedS4(rung,mode,root/'seed_F_006_research_only.pt',key_gain=args.key_gain).to(device)
            optimizer=torch.optim.Adam((p for p in m.parameters() if p.requires_grad),lr=args.lr)
            gen=torch.Generator().manual_seed(args.seed+101)
            start_step=0;hist=[]
            cp=out/f'{rung}_{mode}.checkpoint.pt'
            if args.resume and cp.exists():
                saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved.get('source_sha256')!=SOURCE_SHA or saved.get('seed')!=args.seed or saved.get('steps_target')!=args.steps or saved.get('rung')!=rung or saved.get('mode')!=mode or saved.get('batch')!=args.batch or saved.get('lr')!=args.lr or saved.get('route_loss')!=args.route_loss or saved.get('key_gain')!=args.key_gain:
                    raise RuntimeError('Checkpoint mismatch '+str(cp))
                m.load_state_dict(saved['model'],strict=True)
                optimizer.load_state_dict(saved['optimizer'])
                gen.set_state(saved['rng'])
                start_step=saved['step'];hist=saved['history']
                print('RESUMED',rung,mode,'step',start_step,flush=True)
            print('BEGIN',rung,mode,'from',start_step,flush=True)
            start=time.monotonic()
            for step in range(start_step+1,args.steps+1):
                if step==start_step+1 or step%25==0:
                    gpu_guard(device,args.max_temp,args.max_gpu_mib)
                length=(12,24)[int(torch.randint(0,2,(1,),generator=gen))]
                x,y=make_batch(args.batch,length,rung,gen)
                x=x.to(device);y=y.to(device)
                m.train();optimizer.zero_grad(set_to_none=True)
                logit,trace=m.sequence(x)
                loss=F.binary_cross_entropy_with_logits(logit,y)
                if mode!='no_memory' and args.route_loss:
                    loss=loss+args.route_loss*F.cross_entropy(trace['route_logits'],trace['route_target'])
                if not torch.isfinite(loss):raise RuntimeError('nonfinite loss')
                loss.backward()
                nn.utils.clip_grad_norm_((p for p in m.parameters() if p.requires_grad),1.,error_if_nonfinite=True)
                optimizer.step();m.after_step()
                if step==1 or step%args.log_every==0 or step==args.steps:
                    print('STEP',rung,mode,step,round(loss.item(),5),flush=True)
                    hist.append({'step':step,'train_bce':round(loss.item(),6)})
                if step%args.save_every==0 or step==args.steps:
                    atomic_save({'model':{k:v.detach().cpu() for k,v in m.state_dict().items()},
                        'optimizer':optimizer.state_dict(),'rng':gen.get_state(),
                        'step':step,'history':hist,'seed':args.seed,'steps_target':args.steps,
                        'source_sha256':SOURCE_SHA,'rung':rung,'mode':mode,
                        'batch':args.batch,'lr':args.lr,'route_loss':args.route_loss,'key_gain':args.key_gain},cp)
                if args.max_seconds and time.monotonic()-start>args.max_seconds:
                    # Exits only after an atomic checkpoint, including a mid-interval step.
                    if step%args.save_every!=0 and step!=args.steps:
                        atomic_save({'model':{k:v.detach().cpu() for k,v in m.state_dict().items()},
                            'optimizer':optimizer.state_dict(),'rng':gen.get_state(),
                            'step':step,'history':hist,'seed':args.seed,'steps_target':args.steps,
                            'source_sha256':SOURCE_SHA,'rung':rung,'mode':mode,
                            'batch':args.batch,'lr':args.lr,'route_loss':args.route_loss,'key_gain':args.key_gain},cp)
                    print('PAUSED: time budget reached, checkpoint saved',rung,mode,step,flush=True)
                    raise SystemExit(2)
            gpu_guard(device,args.max_temp,args.max_gpu_mib)
            evals={};erasures={}
            for length in (12,24,48,96):
                gpu_guard(device,args.max_temp,args.max_gpu_mib)
                print('EVAL_BEGIN',rung,mode,'length',length,flush=True)
                guard=lambda:gpu_guard(device,args.max_temp,args.max_gpu_mib)
                evals[str(length)]=score(m,rung,length,args.seed+2000+length,args.eval_samples,device,guard=guard)
                erasures[str(length)]=score(m,rung,length,args.seed+2000+length,args.eval_samples,device,erase=True,guard=guard)
                print('EVAL_DONE',rung,mode,'length',length,'acc',evals[str(length)]['acc'],'erased',erasures[str(length)]['acc'],flush=True)
            attn=attention_probe(m,rung,device) if mode!='no_memory' else None
            p=out/f'{rung}_{mode}.pt'
            atomic_save({k:v.cpu() for k,v in m.state_dict().items()},p)
            row={'rung':rung,'mode':mode,'parameter_count_total':sum(p.numel() for p in m.parameters()),
                 'parameters_updated':sum(p.numel() for p in m.parameters() if p.requires_grad),
                 'eval':evals,'erased':erasures,'attention':attn,'history':hist,
                 'duration_sec':round(time.monotonic()-start,3),'weights':p.name,'sha256':sha(p),
                 'max_core_l1_violation':m.core.max_violation()}
            report['runs'].append(row)
            atomic_json(report,report_path)
            print('FINAL',rung,mode,'acc',{k:v['acc'] for k,v in evals.items()},'erased',{k:v['acc'] for k,v in erasures.items()},'attention',attn,flush=True)
    print('SUCCESS',out,flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    ap.add_argument('--rungs',default='r2_two,r3_three')
    ap.add_argument('--modes',default='no_memory,s4_goal')
    ap.add_argument('--steps',type=int,default=250)
    ap.add_argument('--batch',type=int,default=32)
    ap.add_argument('--eval-samples',type=int,default=256)
    ap.add_argument('--log-every',type=int,default=50)
    ap.add_argument('--lr',type=float,default=.003)
    ap.add_argument('--seed',type=int,default=47)
    ap.add_argument('--route-loss',type=float,default=0.25)
    ap.add_argument('--key-gain',type=float,default=.99)
    ap.add_argument('--max-seconds',type=float,default=900)
    ap.add_argument('--max-temp',type=float,default=80.)
    ap.add_argument('--max-gpu-mib',type=float,default=7000.)
    ap.add_argument('--save-every',type=int,default=25)
    ap.add_argument('--resume',action='store_true')
    ap.add_argument('--output',default='uno_s4_wm_007_results')
    args=ap.parse_args()
    if min(args.steps,args.batch,args.eval_samples,args.log_every,args.save_every)<=0 or args.route_loss<0 or args.key_gain<=0 or args.key_gain>1:ap.error('invalid sizes/loss/key_gain: max 1')
    run(args)

if __name__=='__main__':main()
