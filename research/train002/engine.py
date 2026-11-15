"""TRAIN002 adapter around immutable TRAIN001 schema/optimizer/checkpoint.
S4 key preactivation gains a fixed public chronology code; F/S5 are unchanged.
"""
import pathlib,sys,math,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'train001'))
import torch
from torch import nn
from torch_backend import TorchF,checkpoint,restore,project,rate,atomic,output_lock,require,canonical,file_sha
from organizer import Chronology

class OrganizedF(TorchF):
    def __init__(self,initial,dtype=torch.float32,device='cpu',clock_gain=0.,control='full',payload='typed'):
        super().__init__(initial,dtype,device);self.clock_gain=float(clock_gain);self.control=control;self.payload=payload;self.without_s4=False
        require(self.clock_gain in (0.,.5) and control in ('full','memory_off','zero_values','random_keys','permute_values','reverse_pairs','clock_shuffle') and payload in ('legacy','typed'),'EXPERIMENT_MODE')
    def replay(self,features,mode=None):
        mode=mode or self.control
        require(features.ndim==2 and features.shape[1]==3 and 1<=len(features)<=96 and bool(torch.isfinite(features).all()),'FEATURES')
        w=self.named_tensors();s=features.new_zeros(64);store=Chronology();reads=[];states=[]
        for index,f in enumerate(features):
            z0=torch.tanh(w['projection']@f+w['us']@s+w['e'][:,0]+w['bias'][:,0]);q=features.new_zeros(128) if self.without_s4 else torch.tanh(w['wq']@z0)
            entries=store.records if mode!='reverse_pairs' else list(reversed(store.records))
            if entries and mode!='memory_off':
                keys=[entry.key for entry in entries];values=[entry.value for entry in entries]
                if mode=='clock_shuffle' and self.clock_gain:
                    keys=[torch.tanh(w['wk']@states[entry.sequence-1]+self.clock_gain*Chronology.clock(other.sequence,other.ordinal,other.version,q)) for entry,other in zip(entries,reversed(entries))]
                if mode=='permute_values':values=values[::-1]
                logits=torch.stack(keys)@q/math.sqrt(128);prob=torch.softmax(logits,0)
                r=prob@(torch.stack(values) if mode!='zero_values' else features.new_zeros((len(entries),128)))
            else:
                prob=features.new_zeros(0);logits=features.new_zeros(0);r=features.new_zeros(128)
            reads.append({'sequence':index+1,'ids':[e.sequence for e in entries] if mode!='memory_off' else [],'prob':prob,'logits':logits,'query':q,'read':r})
            # Same S4/S5 order as TRAIN001. No additional neural head or parameters.
            z=torch.tanh(z0 if self.without_s4 else z0+w['wr']@r);h=.5*s+.5*z;cached=[w[f'branch.{l}.0.c']@z for l in (0,1)]
            for _ in range(2):
                out=[]
                for l in (0,1):
                    n=f'branch.{l}.0';u=torch.tanh(w[n+'.a']@h+cached[l]+w[n+'.ab'][:,0]);out.append(torch.tanh(w[n+'.b']@u+w[n+'.bb'][:,0]))
                h=.5*h+.25*(out[0]+out[1])
            s=h;states.append(s)
            if float(f[2])==1. and not self.without_s4:
                sequence=index+1;ordinal=len(store.records)+1;version=len(store.history(float(f[1])))+1
                pre=w['wk']@s
                if self.clock_gain:pre=pre+self.clock_gain*Chronology.clock(sequence,ordinal,version,s)
                key=torch.tanh(pre)
                if mode=='random_keys':
                    prefix=repr(features[:index+1].detach().cpu().tolist()).encode()
                    seed=int.from_bytes(hashlib.sha256(prefix).digest()[:8],'little')%(2**63-1)
                    gen=torch.Generator().manual_seed(seed)
                    key=(torch.rand(128,generator=gen,dtype=torch.float64)*1.8-.9).to(s)
                store.append(sequence,float(f[1]),key,torch.tanh(w['wv']@s))
        return {'state':s,'query':q,'store':store,'states':states,'reads':reads}
    def project_(self):
        with torch.no_grad():
            for (_,_,_,cap,box),p in zip(self.rules,self.slots):
                if not p.requires_grad:continue
                if box:p.clamp_(-cap,cap)
                else:project(p,cap)
        self.validate()
    def episode(self,features,mode=None):
        g=self.replay(features,mode);return g['state'],g['query'],[(r.sequence,r.key,r.value) for r in g['store'].records]
    def loss(self,row):
        g=self.replay(row['x']);h=g['state'];records=g['store'].records
        state_loss=(h[0]-row['state'])**2
        if self.control=='memory_off':return state_loss
        target=[i for i,r in enumerate(records) if r.sequence==row['record']]
        require(bool(target),'RETRIEVAL_MISS')
        # Loss consumes gold only after the entire candidate bank/forward has been built.
        logits=torch.stack([r.key for r in records])@g['query']/math.sqrt(128)
        retrieval=-logits.log_softmax(0)[target[0]]
        if self.payload=='legacy':value=(records[target[0]].value[0]-row['value'])**2
        else:
            # Same write fields for every task, independent of a future query/target choice.
            value=sum(((r.value[:2]-row['x'][r.sequence-1,:2])**2).mean() for r in records)/len(records)
        return state_loss+.3*retrieval+.2*value

class GRUControl(nn.Module):
    def __init__(self,dtype=torch.float32,device='cpu'):
        super().__init__();self.gru=nn.GRU(3,215,batch_first=True);self.head=nn.Linear(215,1);self.to(device=device,dtype=dtype)
    def episode(self,x,mode=None):
        output,_=self.gru(x[None,:,:]);state=torch.tanh(self.head(output[:,-1])).flatten();return state,None,[]
    def loss(self,row):return (self.episode(row['x'])[0][0]-row['state'])**2
    def project_(self):
        require(all(bool(torch.isfinite(p).all()) for p in self.parameters()),'NONFINITE_GRU')

ARMS={
 'baseline_legacy':(0.,'full','legacy'), 'baseline_typed':(0.,'full','typed'),
 'chrono_legacy':(.5,'full','legacy'), 'chrono_typed':(.5,'full','typed'),
 'f_no_memory':(0.,'memory_off','typed'), 'frozen_write':(0.,'full','typed'),
 'random_keys':(0.,'random_keys','typed'), 'permuted_values':(0.,'permute_values','typed'),
 'gru':None,
}
def make_model(initial,arm,seed,dtype,device):
    require(arm in ARMS,'UNKNOWN_ARM');torch.manual_seed(seed)
    if arm=='gru':return GRUControl(dtype,device)
    gain,mode,payload=ARMS[arm];model=OrganizedF(initial,dtype,device,gain,mode,payload)
    if arm=='f_no_memory':model.without_s4=True
    if arm=='frozen_write':
        for name in ('wk','wv'):model.named_tensors()[name].requires_grad_(False)
    return model

def metrics(model,rows,mode=None,details=False):
    groups={};predictions=[]
    with torch.no_grad():
        for row in rows:
            graph=model.replay(row['x'],mode) if details and isinstance(model,OrganizedF) else None
            h=graph['state'] if graph is not None else model.episode(row['x'],mode)[0]
            score=float(h[0]);pred=int(score>=0);label=row['label']
            group=row['group'];g=groups.setdefault(group,{'n':0,'correct':0,'sse':0.})
            g['n']+=1;g['correct']+=int(pred==label);g['sse']+=(score-row['state'])**2
            record={'id':row['id'],'pair':row['pair'],'group':group,'label':label,'prediction':pred,'score':score,'correct':pred==label}
            if details:
                last=graph['reads'][-1] if graph else None
                ids=last['ids'] if last else [];prob=last['prob'].tolist() if last else []
                record.update({'target_record':row['record'],'read_ids':ids,'attention':prob,'logits':last['logits'].tolist() if last else [],'selected_record':ids[max(range(len(prob)),key=prob.__getitem__)] if prob else None,'records':[{'id':r.sequence,'ordinal':r.ordinal,'slot':r.slot,'version':r.version,'previous':r.previous,'next':r.next,'previous_version':r.previous_version,'raw_write':row['x'][r.sequence-1].tolist(),'learned_value_head':r.value[:2].tolist()} for r in graph['store'].records] if graph else []})
            predictions.append(record)
    for g in groups.values():g['accuracy']=g['correct']/g['n'];g['mse']=g['sse']/g['n']
    n=sum(g['n'] for g in groups.values());return {'n':n,'correct':sum(g['correct'] for g in groups.values()),'mse':sum(g['sse'] for g in groups.values())/n,'groups':groups},predictions
