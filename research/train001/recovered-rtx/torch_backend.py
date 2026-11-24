"""Research port of existing Kotlin TRAIN001 S4/S5, d64/m128/b64/chi4/J2/K2.
Parity against Kotlin is mandatory; not Android, S6, AMP, or a production weight ABI.
Inputs from Kotlin `prepare`; labels are consumed only after building the causal graph.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math,os,pathlib,tempfile,time,contextlib
import torch
from torch import nn

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(p):return sha(p.read_bytes())
def require(condition,reason):
    if not condition:raise ValueError(reason)

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def atomic(path,data):
    fd,tmp=tempfile.mkstemp(prefix='uno-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def project(row,cap):
    """Euclidean projection in gap coordinates, same stable contract as Kotlin."""
    # All row work vectorized. Sort ascending gaps; active rows found before delta update.
    x=row.detach().double().reshape(-1,row.shape[-1]);outside=x.abs().sum(-1)>cap
    if not bool(outside.any()):return row
    active=x[outside];largest=active.abs().amax(-1,keepdim=True);gaps=(largest-active.abs()).sort(-1).values
    delta=torch.full((len(active),),cap,dtype=torch.float64,device=row.device)
    for i in range(1,x.shape[-1]):
        delta=torch.where(gaps[:,i]<delta,delta+(gaps[:,i]-delta)/(i+1),delta)
    x[outside]=active.sign()*torch.clamp(delta[:,None]-(largest-active.abs()),min=0)
    row.copy_(x.reshape_as(row).to(row.dtype))
    return row

class TorchF(nn.Module):
    def __init__(self,initial:pathlib.Path,dtype=torch.float64,device='cpu'):
        super().__init__();self.names=[];self.rules=[];numbers=[]
        for line in initial.read_text().splitlines():
            name,rows,cols,cap,box,values=line.split('\t');rows=int(rows);cols=int(cols)
            require(name not in self.names and rows>0 and cols>0 and rows*cols<=2_000_000,"INPUT_OR_MANIFEST_REJECTED")
            self.names.append(name);self.rules.append((name,rows,cols,float(cap),box=='true'))
            numbers.append(nn.Parameter(torch.tensor([float(v) for v in values.split(',')],dtype=dtype,device=device).reshape(rows,cols)))
        self.slots=nn.ParameterList(numbers)
        require(len(self.names)==len(set(self.names)) and len(self.names)<=256,"INPUT_OR_MANIFEST_REJECTED")
        expected={'projection':(64,3),'us':(64,64),'ug':(64,64),'meta':(64,32),'e':(64,1),'bias':(64,1),'wq':(128,64),'wr':(64,128),'wk':(128,64),'wv':(128,64)}
        for l in (0,1):
            for suffix,shape in [('a',(256,64)),('c',(256,64)),('b',(64,256)),('ab',(256,1)),('bb',(64,1))]:expected[f'branch.{l}.0.{suffix}']=shape
        require({n:tuple(p.shape) for n,p in self.named_tensors().items()}==expected,"INPUT_OR_MANIFEST_REJECTED")
        caps={'a':1.,'c':2.,'b':.9,'ab':8.,'bb':8.}
        for n,r,c,cap,box in self.rules:
            expected_cap=caps[n.rsplit('.',1)[1]] if n.startswith('branch.') else {'projection':8.,'meta':8.,'us':1.,'ug':1.,'e':1.,'bias':1.,'wq':2.,'wr':2.,'wk':2.,'wv':2.}[n]
            require(cap==expected_cap and box==(n in ('e','bias') or n.endswith(('.ab','.bb'))),"INPUT_OR_MANIFEST_REJECTED")
        self.validate()
    def named_tensors(self):return dict(zip(self.names,self.slots))
    def validate(self):
        for (n,r,c,cap,box),p in zip(self.rules,self.slots):
            if not bool(torch.isfinite(p).all()):raise ValueError('NONFINITE_PARAMETER '+n)
            norm=p.detach().double().abs().max() if box else p.detach().double().abs().sum(-1).max()
            # Explicit FP32 arithmetic tolerance; not a strict decoded-cap/export certificate.
            tol=1e-10 if p.dtype==torch.float64 else 2e-6
            if norm>cap+tol:raise ValueError(f'PARAMETER_NORM {n} norm={norm.item()} cap={cap} dtype={p.dtype}')
    def project_(self):
        with torch.no_grad():
            for (_,_,_,cap,box),p in zip(self.rules,self.slots):
                if box:p.clamp_(-cap,cap)
                else:project(p,cap)
        self.validate()
    def episode(self,features,mode='full'):
        """Only raw observable features enter F. Return bank for loss *after* graph construction."""
        require(features.ndim==2 and features.shape[1]==3 and 1<=len(features)<=96 and mode in ('full','memory_off','zero_values'),"INPUT_OR_MANIFEST_REJECTED")
        w=self.named_tensors();s=features.new_zeros(64);bank=[]
        for index,f in enumerate(features):
            z0=torch.tanh(w['projection']@f+w['us']@s+w['e'][:,0]+w['bias'][:,0])
            q=torch.tanh(w['wq']@z0)
            if bank and mode!='memory_off':
                keys=torch.stack([k for _,k,_ in bank]);values=torch.stack([v for _,_,v in bank])
                prob=torch.softmax(keys@q/math.sqrt(128),0)
                r=prob@(values if mode=='full' else torch.zeros_like(values))
            else:r=features.new_zeros(128)
            z=torch.tanh(z0+w['wr']@r);h=.5*s+.5*z
            cached=[w[f'branch.{l}.0.c']@z for l in (0,1)]
            for _ in range(2):
                out=[]
                for l in (0,1):
                    n=f'branch.{l}.0';u=torch.tanh(w[n+'.a']@h+cached[l]+w[n+'.ab'][:,0])
                    out.append(torch.tanh(w[n+'.b']@u+w[n+'.bb'][:,0]))
                h=.5*h+.25*(out[0]+out[1])
            s=h
            if float(f[2])==1.:
                # Append only after event finishes. No external keys, raw-value shortcut, or detach.
                bank.append((index+1,torch.tanh(w['wk']@s),torch.tanh(w['wv']@s)))
        return s,q,bank
    def loss(self,row):
        h,q,bank=terminal_episode(self,row['x'])
        require(math.isfinite(row['state']) and math.isfinite(row['value']), 'NONFINITE_TEACHER')
        target=[i for i,(seq,_,_) in enumerate(bank) if seq==row['record']]
        if not target:raise ValueError('RETRIEVAL_MISS')
        logits=terminal_logits(q,bank)
        return (h[0]-row['state'])**2+.3*(-logits.log_softmax(0)[target[0]])+.2*(bank[target[0]][2][0]-row['value'])**2

def terminal_episode(model,features,mode='full'):
    """TRAIN001 supervised contract only: noise/WRITE, then exactly one QUERY.
    Teacher ID, value and label never enter this function. Validate chronological
    membership against observed writes; do not filter candidates by the teacher.
    This is the accumulating TRAIN001 bank, not address-overwrite or Android.
    """
    require(features.ndim==2 and features.shape[1]==3 and 1<=len(features)<=96
            and bool(torch.isfinite(features).all()), 'INPUT_OR_MANIFEST_REJECTED')
    flags=features[:,2].detach().tolist()
    require(flags[-1] in (-1.,-2.), 'TERMINAL_QUERY_REQUIRED')
    require(all(flag in (0.,1.) for flag in flags[:-1]), 'NONCAUSAL_EVENT_SEQUENCE')
    h,q,bank=model.episode(features,mode)
    expected=[i for i,flag in enumerate(flags[:-1],1) if flag==1.]
    require([seq for seq,_,_ in bank]==expected, 'NONCAUSAL_BANK')
    return h,q,bank

def terminal_logits(q,bank):
    require(bool(bank), 'RETRIEVAL_MISS')
    logits=torch.stack([k for _,k,_ in bank])@q/math.sqrt(q.numel())
    require(bool(torch.isfinite(logits).all()), 'NONFINITE_RETRIEVAL_LOGITS')
    return logits

def dataset(path,dtype,device):
    rows=[]
    for line in path.read_text().splitlines():
        name,label,record,value,raw=line.split('\t')
        x=torch.tensor([[float(v) for v in f.split(',')] for f in raw.split(';')],dtype=dtype,device=device)
        require(bool(torch.isfinite(x).all()) and x.shape[1]==3 and 1<=len(x)<=96 and int(label) in (0,1),"INPUT_OR_MANIFEST_REJECTED")
        rows.append({'id':name,'label':int(label),'record':int(record),'value':float(value),'state':.8 if int(label) else -.8,'x':x})
    require(rows and len({r['id'] for r in rows})==len(rows),"INPUT_OR_MANIFEST_REJECTED")
    return rows

def checkpoint(path,state):
    buf=io.BytesIO();torch.save(state,buf);body=buf.getvalue()
    if len(body)>64*1024*1024:raise ValueError('CHECKPOINT_SIZE')
    atomic(path,b'UNO-TORCH-S4/V1\n'+sha(body).encode()+b'\n'+body)
def restore(path):
    if not 1<=path.stat().st_size<=64*1024*1024+128:raise ValueError('CHECKPOINT_SIZE')
    head,digest,body=path.read_bytes().split(b'\n',2)
    if head!=b'UNO-TORCH-S4/V1' or sha(body).encode()!=digest:raise ValueError('CHECKPOINT_INTEGRITY')
    return torch.load(io.BytesIO(body),map_location='cpu',weights_only=True)
def rate(step,total):
    return 2e-4*step/1000 if step<=1000 else 2e-5+(2e-4-2e-5)*.5*(1+math.cos(math.pi*(step-1000)/(max(2000,total)-1000)))
def update(model,opt,rows,step,total):
    opt.zero_grad(set_to_none=True);loss=0.
    for row in rows:loss=loss+model.loss(row)/len(rows)
    if not bool(torch.isfinite(loss)):raise ValueError('NONFINITE_LOSS')
    loss.backward()
    if any(p.grad is not None and not bool(torch.isfinite(p.grad).all()) for p in model.parameters()):raise ValueError('NONFINITE_GRADIENT')
    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
    for g in opt.param_groups:g['lr']=rate(step,total)
    opt.step();model.project_();return loss.item(),float(norm)

def scores(model,rows,mode='full'):
    """Erratum 13: SSE and MSE are distinct; bank presence is not retrieval.
    Schema 2: terminal-query attention top-1, not end-to-end task quality.
    All read-enabled queries enter the denominator, including missing targets.
    memory_off has no attention read, so its retrieval rate is undefined.
    Preserve legacy task-correct and global MSE definitions on TRAIN001 data.
    """
    require(bool(rows) and mode in ('full','memory_off','zero_values'), 'EVALUATION_INPUT')
    out={}
    def counts():return {'n':0,'correct':0,'sse':0.,'presence_misses':0,'retrieval_top1_n':0,'retrieval_top1_correct':0}
    with torch.no_grad():
        for row in rows:
            h,q,bank=terminal_episode(model,row['x'],mode)
            group='-'.join(row['id'].split('-')[1:-1]);r=out.setdefault(group,counts())
            hit=any(seq==row['record'] for seq,_,_ in bank)
            r['n']+=1;r['correct']+=int(hit and (float(h[0])>=0)==bool(row['label']))
            r['sse']+=(float(h[0])-row['state'])**2;r['presence_misses']+=int(not hit)
            if mode!='memory_off':
                r['retrieval_top1_n']+=1
                if bank:
                    logits=terminal_logits(q,bank)
                    # torch.argmax returns the first maximum in chronological bank order.
                    r['retrieval_top1_correct']+=int(bank[int(logits.argmax())][0]==row['record'])
    def finish(r):
        r['mse']=r['sse']/r['n']
        r['retrieval_top1_accuracy']=(r['retrieval_top1_correct']/r['retrieval_top1_n'] if r['retrieval_top1_n'] else None)
        return r
    total=finish({k:sum(v[k] for v in out.values()) for k in counts()})
    return {'metric_schema':2,**total,'groups':{k:finish(v) for k,v in out.items()}}

@contextlib.contextmanager
def output_lock(output):
    output.parent.mkdir(parents=True,exist_ok=True)
    path=output.with_name(output.name+'.lock')
    with open(path,'a+b') as f:
        if path.stat().st_size==0:f.write(b'0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:raise RuntimeError('OUTPUT_BUSY: another process owns this run') from exc
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def run(a):
    if a.device=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE; no CPU fallback')
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in (':4096:8',':16:8'):raise RuntimeError('Set CUBLAS_WORKSPACE_CONFIG=:4096:8 before starting Python')
        if torch.cuda.device_count()!=1 or os.environ.get('CUDA_VISIBLE_DEVICES') not in (None,'0'):raise RuntimeError('GPU guard currently supports one visible physical GPU0 only')
    require(1<=a.steps<=10000 and 1<=a.batch<=16 and a.max_seconds>0,"INPUT_OR_MANIFEST_REJECTED")
    if a.device=='cuda':
        require(a.cuda_receipt is not None,'CUDA_CHECK_RECEIPT_REQUIRED')
        receipt=json.loads(a.cuda_receipt.read_text())
        require(receipt.get('status')=='CUDA_MECHANISM_CHECK_PASS_NOT_QUALITY' and receipt.get('backend_sha256')==file_sha(pathlib.Path(__file__)) and receipt.get('torch')==torch.__version__ and receipt.get('gpu')==torch.cuda.get_device_name(0),'CUDA_CHECK_RECEIPT_MISMATCH')
    dtype={'double':torch.float64,'float32':torch.float32}[a.precision]
    torch.set_num_threads(2);torch.manual_seed(a.seed);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    model=TorchF(a.data/'initial.tsv',dtype,a.device);opt=torch.optim.Adam(model.parameters(),lr=2e-4)
    data={s:dataset(a.data/f'{s}.tsv',dtype,a.device) for s in ('train','validation')} # test stays unopened
    cfg={'version':1,'source':file_sha(pathlib.Path(__file__)),'input':{p.name:file_sha(p) for p in a.data.glob('*.tsv')},'steps':a.steps,'batch':a.batch,'seed':a.seed,'precision':a.precision,'device':a.device,'torch':str(torch.__version__),'cuda':torch.version.cuda,'cublas':os.environ.get('CUBLAS_WORKSPACE_CONFIG'),'gpu':torch.cuda.get_device_name(0) if a.device=='cuda' else None,'geometry':'d64/m128/b64/chi4/J2/K2,alpha=rho=.5,full-route,f_e=0','fp32_cap_tolerance':2e-6,'projection':'FP64 threshold then cast to master dtype','tf32':False,'deterministic':True}
    if a.resume:
        require(json.loads((a.output/'manifest.json').read_text())==cfg,"RUN_MANIFEST_MISMATCH")
        state=restore(a.output/'latest.uno');require(state['config']==cfg,"INPUT_OR_MANIFEST_REJECTED")
        model.load_state_dict(state['weights'],strict=True);model.validate();opt.load_state_dict(state['optimizer'])
        step=state['step'];require(0<=step<=a.steps and state['cursor']==step*a.batch,"INPUT_OR_MANIFEST_REJECTED")
        history=state['history'];best=state['best'];best_loss=state['best_loss'];selected=state['selected']
        torch.set_rng_state(state['cpu_rng'])
        if a.device=='cuda':torch.cuda.set_rng_state_all(state['cuda_rng'])
    else:
        a.output.mkdir(parents=True,exist_ok=False);atomic(a.output/'manifest.json',canonical(cfg).encode())
        step=0;history=[];best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};best_loss=scores(model,data['validation'])['mse'];selected=0
    def save():
        checkpoint(a.output/'latest.uno',{'config':cfg,'weights':model.state_dict(),'optimizer':opt.state_dict(),'step':step,'cursor':step*a.batch,'cpu_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if a.device=='cuda' else [],'history':history,'best':best,'best_loss':best_loss,'selected':selected})
    def guard():
        if a.device=='cuda':
            import subprocess
            # Fail closed on monitoring failure; guard errors leave the last optimizer boundary.
            fields=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True,timeout=5).splitlines()[0].split(',')
            if float(fields[0])>=a.max_temp or float(fields[1])>=a.max_mib:raise RuntimeError('GPU_GUARD_STOP')
    if a.resume and step==a.steps:
        print('ALREADY_FINISHED; checkpoint unchanged',flush=True);return
    save();start=time.monotonic()
    while step<a.steps:
        if time.monotonic()-start>=a.max_seconds:print('TIME_BUDGET_STOP at',step,flush=True);return
        guard()
        batch=[data['train'][(step*a.batch+j)%len(data['train'])] for j in range(a.batch)]
        loss,norm=update(model,opt,batch,step+1,a.steps);step+=1
        row={'step':step,'loss':loss,'grad_norm':norm}
        if step%50==0 or step==a.steps:
            row['validation']=scores(model,data['validation'])
            if row['validation']['mse']<best_loss:
                best_loss=row['validation']['mse'];selected=step;best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        history.append(row);save();print(canonical(row),flush=True)
    # Evaluation is a separate explicit command; never open test during training.
    atomic(a.output/'training.json',canonical({'config':cfg,'selected':selected,'best_validation_mse':best_loss,'history':history,'status':'TRAIN_FINISHED_QUALITY_UNASSESSED'}).encode())

def evaluate(a):
    torch.set_num_threads(2)
    cfg=json.loads((a.output/'manifest.json').read_text());require(cfg['source']==file_sha(pathlib.Path(__file__)) and cfg['torch']==str(torch.__version__),"EVALUATION_RUNTIME_OR_SOURCE_MISMATCH")
    require(cfg['input']=={p.name:file_sha(p) for p in a.data.glob('*.tsv')},"INPUT_OR_MANIFEST_REJECTED")
    state=restore(a.output/'latest.uno');require(state['config']==cfg and state['step']==cfg['steps'],"INPUT_OR_MANIFEST_REJECTED")
    pin=canonical({'checkpoint':file_sha(a.output/'latest.uno'),'selected':state['selected']})
    marker=a.output/'test-selected.json';report=a.output/'test.json'
    if marker.exists():require(marker.read_text()==pin,"LOCKED_TEST_SELECTION_CHANGED")
    else:atomic(marker,pin.encode())
    if report.exists():print(report.read_text());return
    dtype={'double':torch.float64,'float32':torch.float32}[cfg['precision']]
    model=TorchF(a.data/'initial.tsv',dtype,'cpu');model.load_state_dict(state['best']);model.validate()
    test=dataset(a.data/'test.tsv',dtype,'cpu');erased=dataset(a.data/'erased.tsv',dtype,'cpu')
    result={'selected':state['selected'],'full':scores(model,test),'erased':scores(model,erased),'memory_off':scores(model,test,'memory_off'),'zero_values':scores(model,test,'zero_values'),'evaluation_device':'cpu','training_device':cfg['device']}
    atomic(report,canonical(result).encode());print(canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['train','evaluate']);p.add_argument('data',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
    p.add_argument('--steps',type=int,default=1000);p.add_argument('--batch',type=int,default=4);p.add_argument('--seed',type=int,default=150015);p.add_argument('--device',choices=['cuda','cpu'],default='cuda');p.add_argument('--precision',choices=['double','float32'],default='float32');p.add_argument('--resume',action='store_true')
    p.add_argument('--cuda-receipt',type=pathlib.Path)
    p.add_argument('--max-seconds',type=float,default=1800);p.add_argument('--max-temp',type=float,default=78);p.add_argument('--max-mib',type=float,default=6500)
    a=p.parse_args()
    with output_lock(a.output):
        if a.command=='train':run(a)
        else:evaluate(a)
