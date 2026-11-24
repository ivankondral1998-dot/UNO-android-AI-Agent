"""R5.4 erratum 07. Frozen CPU backward tests; no optimizer, no training.
Usage: python causal_memory_regression_test.py CODEX_HANDOFF.zip TRAIN001_INPUT
"""
import math
import sys
import tempfile
import zipfile
from pathlib import Path
from collections import Counter
import torch
from torch_backend import TorchF, terminal_episode, terminal_logits, dataset, scores

if not __debug__: raise RuntimeError('Tests require assertions')
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
archive, data = map(Path, sys.argv[1:])
passed = 0

def check(name, condition):
    global passed
    assert bool(condition), name
    passed += 1
    print('PASS', name)

def reject(name, fn, error):
    try: fn()
    except ValueError as exc: check(name, str(exc) == error)
    else: raise AssertionError(name + ': accepted')

def equal_graph(a,b):
    return torch.equal(a[0],b[0]) and torch.equal(a[1],b[1]) and len(a[2])==len(b[2]) and all(x[0]==y[0] and torch.equal(x[1],y[1]) and torch.equal(x[2],y[2]) for x,y in zip(a[2],b[2]))

def fixture(z, folder, tmp):
    def lines(name):
        names=[n for n in z.namelist() if n.endswith('/'+folder+'/'+name+'.tsv')]
        assert len(names)==1
        return z.read(names[0]).decode().splitlines()
    rules={f[0]:f[1:3] for f in (line.split('\t') for line in lines('update1'))}
    initial=[]; expected={}
    for line in lines('weights'):
        n,r,c,x,g=line.split('\t');cap,box=rules[n]
        initial.append('\t'.join((n,r,c,cap,box,x)))
        expected[n]=torch.tensor([float(v) for v in g.split(',')],dtype=torch.float64).reshape(int(r),int(c))
    p=tmp/(folder+'.tsv');p.write_text('\n'.join(initial))
    events=[[float(v) for v in l.split('\t')[-1].split(',')] for l in lines('events')]
    rec,state,value,loss=lines('target')[0].split('\t')
    row=dict(x=torch.tensor(events,dtype=torch.float64),record=int(rec),state=float(state),value=float(value))
    return TorchF(p), row, expected, float(loss)

with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as z:
    check('archive CRC',z.testzip() is None)
    for folder in ('parity-singleton','parity','parity96'):
        model,row,expected,expected_loss=fixture(z,folder,Path(tmp));w=model.named_tensors()
        before={n:p.detach().clone() for n,p in w.items()}
        h,q,bank=terminal_episode(model,row['x'])
        check(folder+' causal prefix IDs',[s for s,_,_ in bank]==[i for i,f in enumerate(row['x'],1) if f[2]==1])
        for seq,k,v in bank:
            ph,pq,pb=model.episode(row['x'][:seq]);assert pb[-1][0]==seq
            assert torch.equal(k,pb[-1][1]) and torch.equal(v,pb[-1][2])
            assert torch.equal(k,torch.tanh(w['wk']@ph)) and torch.equal(v,torch.tanh(w['wv']@ph))
        check(folder+' all encoded writes equal causal prefix',True)
        # Isolate downstream value path from auxiliary CE/value labels.
        grads=torch.autograd.grad(h[0], [w[n] for n in ('wk','wq','wv')], retain_graph=True,allow_unused=True)
        maxima=[0. if g is None else g.abs().max().item() for g in grads]
        print(folder,'writes',len(bank),'task-only max |grad| wk,wq,wv',maxima)
        if len(bank)==1:
            check(folder+' task-only Wk and Wq zero',maxima[0]==maxima[1]==0.)
            check(folder+' task-only Wv nonzero',maxima[2]>0.)
        else:
            check(folder+' task-only gradients nonzero for these weights',min(maxima)>0.)
        loss=model.loss(row);loss.backward()
        err=max(((torch.zeros_like(p) if p.grad is None else p.grad)-expected[n]).abs().max().item() for n,p in w.items())
        check(folder+' archived loss parity',abs(loss.item()-expected_loss)<2e-13)
        check(folder+' all 142272 gradient coordinates',sum(p.numel() for p in w.values())==142272 and err<2e-13)
        print(folder,'max abs grad delta',err)
        # Spy on the actual model call, not a synthetic replacement of the bank.
        original=model.episode; captured=[]
        def spy(features,mode='full'):
            out=original(features,mode);captured.append(out);return out
        model.episode=spy
        changed=dict(row,state=-row['state'],value=row['value']+.125,record=bank[-1][0])
        actual1=model.loss(row);actual2=model.loss(changed)
        check(folder+' teacher changes cannot change forward',equal_graph(captured[0],captured[1]))
        target=next(i for i,(seq,_,_) in enumerate(bank) if seq==changed['record'])
        want=(h[0]-changed['state'])**2-.3*terminal_logits(q,bank).log_softmax(0)[target]+.2*(bank[target][2][0]-changed['value'])**2
        check(folder+' teacher applied only in loss',torch.equal(actual2,want) and not torch.equal(actual1,actual2))
        reject(folder+' missing teacher is miss',lambda:model.loss(dict(row,record=99999)),'RETRIEVAL_MISS')
        check(folder+' missing teacher does not insert entry',equal_graph(captured[0],captured[-1]))
        model.episode=original
        bad=row['x'].clone();bad[-1,2]=1.
        reject(folder+' terminal write rejected',lambda:model.loss(dict(row,x=bad,record=len(bad))),'TERMINAL_QUERY_REQUIRED')
        bad=row['x'].clone();bad[0,2]=-1.
        reject(folder+' premature query rejected',lambda:model.loss(dict(row,x=bad)),'NONCAUSAL_EVENT_SEQUENCE')
        check(folder+' unchanged weights',all(torch.equal(p,before[n]) for n,p in w.items()))
    # Use final actual model with zero previous writes; evaluate counts, not fake success.
    x=torch.tensor([[0.,0.,0.],[0.,0.,-1.]],dtype=torch.float64)
    empty=dict(x=x,record=1,state=.8,value=1.,label=1,id='test-empty-0')
    reject('empty actual bank loss miss',lambda:model.loss(empty),'RETRIEVAL_MISS')
    r=scores(model,[empty]);check('empty actual bank evaluation miss',r['presence_misses']==1 and r['retrieval_top1_n']==1 and r['retrieval_top1_correct']==0)
    class Broken:
        def episode(self,x,mode):
            h,q,b=model.episode(x,mode);return h,q,b+[(len(x),q,q)]
    reject('post-query bank injection rejected',lambda:terminal_episode(Broken(),x),'NONCAUSAL_BANK')
    reject('nonfinite teacher rejected',lambda:model.loss(dict(row,value=float('nan'))),'NONFINITE_TEACHER')

# Analytic local attention gradients, including multi-write degeneracy.
q=torch.tensor([.3,-.4],dtype=torch.float64,requires_grad=True)
k=torch.tensor([[.1,.9],[-.2,.4]],dtype=torch.float64,requires_grad=True)
v=torch.tensor([[.8,.2],[-.7,.1]],dtype=torch.float64,requires_grad=True)
g=torch.tensor([.6,-.1],dtype=torch.float64)
logits=terminal_logits(q,[(i+1,ki,vi) for i,(ki,vi) in enumerate(zip(k,v))]);p=logits.softmax(0);r=p@v
obj=g@r-.3*logits.log_softmax(0)[1]
dl,dv,dq,dk=torch.autograd.grad(obj,(logits,v,q,k))
expected=p*((v-r)@g)+.3*(p-torch.tensor([0.,1.],dtype=p.dtype))
check('analytic score gradient',torch.allclose(dl,expected,atol=1e-15,rtol=0))
check('analytic value gradient',torch.allclose(dv,p[:,None]*g,atol=1e-15,rtol=0))
check('analytic query/key gradient',torch.allclose(dq,k.T@expected/math.sqrt(2),atol=1e-15,rtol=0) and torch.allclose(dk,expected[:,None]*q/math.sqrt(2),atol=1e-15,rtol=0))
for n in (1,2,5):
    logits=torch.linspace(-.3,.4,n,dtype=torch.float64,requires_grad=True);values=torch.ones(n,2,dtype=torch.float64,requires_grad=True)
    prob=logits.softmax(0);read=prob@values
    a,b=torch.autograd.grad(read.sum(),(logits,values))
    check('equal values score degeneracy n='+str(n),a.abs().max()<1e-15)
    check('equal values nonzero value path n='+str(n),b.abs().min()>0)
    a,b=torch.autograd.grad((logits.softmax(0)@values).sum()*0,(logits,values))
    check('zero downstream n='+str(n),a.abs().max()==0 and b.abs().max()==0)

# Independent label derivation on the exact archived data; no predictions fitted.
rows={s:dataset(data/(s+'.tsv'),torch.float64,'cpu') for s in ('train','validation','test','erased')}
for split,rr in rows.items():
    for row in rr:
        x=row['x'].tolist();writes=[(i,f) for i,f in enumerate(x[:-1],1) if f[2]==1.]
        assert x[-1][2] in (-1.,-2.) and all(f[2] in (0.,1.) for f in x[:-1])
        if split=='erased': continue
        idx,f=writes[-1] if x[-1][2]==-2 else next((i,f) for i,f in reversed(writes) if f[1]==x[-1][1])
        value=f[1] if x[-1][2]==-2 else f[0]
        assert (idx,value,int(value>0))==(row['record'],row['value'],row['label'])
    check(split+' chronological contract and '+('erased shape' if split=='erased' else 'derived teacher')+' n='+str(len(rr)),True)
for a,b in zip(rows['test'],rows['erased']):
    assert all(a[n]==b[n] for n in ('record','value','label')) and len(a['x'])==len(b['x'])
    assert torch.equal(a['x'][:,2],b['x'][:,2])
    nonwrite=a['x'][:,2]!=1
    assert torch.equal(a['x'][nonwrite],b['x'][nonwrite])
check('320 aligned erased controls retain teacher and nonwrites',len(rows['test'])==len(rows['erased'])==320)
print('UNO_ERRATUM_07_PASS='+str(passed))
