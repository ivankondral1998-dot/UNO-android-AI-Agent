"""Matched-data CPU GRU control for Kotlin Ladder export. No F replacement or CUDA claim.
Uses same order, steps, batch, Astra LR/clip; same state MSE; F has extra auxiliary losses/memory.
"""
import argparse,hashlib,json,os,pathlib,time
import torch
from torch import nn

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    rows=[]
    for line in p.read_text().splitlines():
        fields=line.split('\t');key,label=fields[:2];raw=fields[-1]
        rows.append((key,int(label),torch.tensor([[float(x) for x in f.split(',')] for f in raw.split(';')],dtype=torch.float64)))
    return rows

class Control(nn.Module):
    def __init__(self):
        super().__init__();self.gru=nn.GRU(3,215,batch_first=True);self.head=nn.Linear(215,1)
    def forward(self,x):
        o,_=self.gru(x);return torch.tanh(self.head(o[:,-1])).flatten()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--steps',type=int,required=True);p.add_argument('--batch',type=int,required=True);p.add_argument('--seed',type=int,default=47);p.add_argument('--group-existing',action='store_true');a=p.parse_args()
    assert 1<=a.steps<=10000 and 1<=a.batch<=64
    if not a.group_existing:a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(a.seed);torch.use_deterministic_algorithms(True)
    data={split:load(a.data/f'{split}.tsv') for split in ('train','validation','test','erased')}
    model=Control().double();opt=torch.optim.Adam(model.parameters(),lr=2e-4)
    def predict(row):return model(row[2][None,:])[0]
    def score(rows):
        with torch.no_grad():
            values=[(predict(row).item(),row[1]) for row in rows]
        return {'n':len(values),'correct':sum((v>=0)==bool(y) for v,y in values),'mse':sum((v-(.8 if y else -.8))**2 for v,y in values)/len(values)}
    def grouped(rows):
        keys=sorted(set('-'.join(row[0].split('-')[1:-1]) for row in rows))
        return {key:score([row for row in rows if '-'.join(row[0].split('-')[1:-1])==key]) for key in keys}
    if a.group_existing:
        report=json.loads((a.output/'report.json').read_text())
        assert report['seed']==a.seed and report['steps']==a.steps and report['batch']==a.batch
        assert report['hashes']=={s:digest(a.data/f'{s}.tsv') for s in data}
        assert report['weights_sha256']==digest(a.output/'selected.pt')
        model.load_state_dict(torch.load(a.output/'selected.pt',weights_only=True,map_location='cpu'))
        groups={'test':grouped(data['test']),'erased':grouped(data['erased'])}
        (a.output/'grouped.json').write_text(json.dumps(groups,indent=2));print(json.dumps(groups));raise SystemExit(0)
    history=[];best=None;best_loss=float('inf')
    for step in range(a.steps+1):
        if step==0 or step%10==0 or step==a.steps:
            m=score(data['validation']);print('VALIDATION',step,m,flush=True)
            if m['mse']<best_loss:best_loss=m['mse'];best={k:v.detach().clone() for k,v in model.state_dict().items()};selected=step
        if step==a.steps:break
        loss=0.
        for j in range(a.batch):
            row=data['train'][(step*a.batch+j)%len(data['train'])]
            loss=loss+(predict(row)-(.8 if row[1] else -.8))**2/a.batch
        opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        nxt=step+1
        rate=2e-4*nxt/1000 if nxt<=1000 else 2e-5+(2e-4-2e-5)*.5*(1+__import__('math').cos(__import__('math').pi*(nxt-1000)/(max(2000,a.steps)-1000)))
        for group in opt.param_groups:group['lr']=rate
        opt.step();history.append({'step':nxt,'loss':loss.item()})
    state={'weights':model.state_dict(),'optimizer':opt.state_dict(),'step':a.steps,'cursor':a.steps*a.batch,'rng':torch.get_rng_state()}
    torch.save(state,a.output/'last.pt');torch.save(best,a.output/'selected.pt');model.load_state_dict(best)
    report={'torch':torch.__version__,'device':'cpu','seed':a.seed,'steps':a.steps,'batch':a.batch,'params':sum(v.numel() for v in model.parameters()),'selected':selected,'hashes':{s:digest(a.data/f'{s}.tsv') for s in data},'history':history,'test':score(data['test']),'erased':score(data['erased']),'grouped':{'test':grouped(data['test']),'erased':grouped(data['erased'])},'weights_sha256':digest(a.output/'selected.pt'),'limits':['same task state MSE; F also has retrieval/value auxiliary losses','GRU unconstrained, no address bank; F constrained with episodic bank','small synthetic CPU budget; no CUDA or general language claims']}
    (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='history'}),flush=True)
