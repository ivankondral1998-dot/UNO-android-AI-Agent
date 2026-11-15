"""Independent torch *oracle*, not an authorized replacement trainer or GPU backend.
Consumes exact Kotlin fixture; checks all named gradients, FP32 and FP16 forward drift.
Requires torch; never loads pickle/checkpoints. No training loop here.
"""
import argparse, pathlib, math, struct
import torch

def run(path,dtype,half_memory=False):
    weights={};expected={}
    for line in (path/'weights.tsv').read_text().splitlines():
        name,rows,cols,x,g=line.split('\t')
        tensor=torch.tensor([float(v) for v in x.split(',')],dtype=dtype).reshape(int(rows),int(cols))
        weights[name]=tensor.requires_grad_();expected[name]=torch.tensor([float(v) for v in g.split(',')],dtype=torch.float64)
    def mv(name,x):return weights[name]@x
    s=torch.zeros(64,dtype=dtype);bank=[]
    target,ys,yv,loss=(path/'target.tsv').read_text().split('\t');target=int(target)
    for line in (path/'events.tsv').read_text().splitlines():
        seq,write,features=line.split('\t');seq=int(seq)
        f=torch.tensor([float(v) for v in features.split(',')],dtype=dtype)
        z0=torch.tanh(mv('projection',f)+mv('us',s)+weights['e'][:,0]+weights['bias'][:,0])
        q=torch.tanh(mv('wq',z0))
        if bank:
            keys=torch.stack([k for _,k,_ in bank]);values=torch.stack([v for _,_,v in bank])
            logits=keys@q/math.sqrt(128);r=logits.softmax(0)@values
        else:r=torch.zeros(128,dtype=dtype)
        z=torch.tanh(z0+mv('wr',r));h=.5*s+.5*z
        cz=[mv(f'branch.{l}.0.c',z) for l in range(2)]
        for _ in range(2):
            branches=[]
            for l in range(2):
                n=f'branch.{l}.0'
                u=torch.tanh(mv(n+'.a',h)+cz[l]+weights[n+'.ab'][:,0])
                branches.append(torch.tanh(mv(n+'.b',u)+weights[n+'.bb'][:,0]))
            h=.5*h+.25*(branches[0]+branches[1])
        s=h
        if write=='true':
            k=torch.tanh(mv('wk',s));v=torch.tanh(mv('wv',s))
            if half_memory:k=k.half().to(dtype);v=v.half().to(dtype)
            bank.append((seq,k,v))
    ix=[i for i,(seq,_,_) in enumerate(bank) if seq==target][0]
    objective=(s[0]-float(ys))**2+.3*(-logits.log_softmax(0)[ix])+.2*(bank[ix][2][0]-float(yv))**2
    if half_memory:
        print('FP16_MEMORY_FORWARD_ONLY loss',objective.item(),'drift',abs(objective.item()-float(loss)))
        return
    objective.backward()
    max_error=0.;max_scaled=0.
    for name,p in weights.items():
        actual=torch.zeros_like(p).flatten() if p.grad is None else p.grad.flatten()
        error=(actual.double()-expected[name]).abs()
        tolerance=(2e-13 if dtype==torch.float64 else 2e-7)+(2e-9 if dtype==torch.float64 else 2e-3)*expected[name].abs()
        assert bool((error<=tolerance).all()),(name,error.max().item())
        max_error=max(max_error,error.max().item());max_scaled=max(max_scaled,(error/tolerance).max().item())
    assert abs(objective.item()-float(loss))<(1e-13 if dtype==torch.float64 else 2e-6)
    print(dtype,'ALL_NAMED_GRADIENTS_PASS','loss',objective.item(),'max_abs',max_error,'max_tolerance_ratio',max_scaled)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fixture',type=pathlib.Path);a=parser.parse_args()
    torch.set_num_threads(2)
    print('torch',torch.__version__,'cuda',torch.cuda.is_available())
    run(a.fixture,torch.float64);run(a.fixture,torch.float32);run(a.fixture,torch.float32,True)
    q=lambda x:struct.unpack('e',struct.pack('e',x))[0]
    assert (q(1+1e-5)-q(1-1e-5))/(2e-5)==0
    print('ROUNDING_COUNTEREXAMPLE derivative=0 smooth=1; no AMP or FP16 gradient equivalence claim')

    # Two projected-Adam updates against Kotlin weights and both moments. These use exact
    # exported Double gradients cast to FP32 to isolate optimizer arithmetic from graph error.
    # Forward/backward precision was independently checked above.
    for dtype in (torch.float64,torch.float32):
        params={}
        for line in (a.fixture/'weights.tsv').read_text().splitlines():
            name,rows,cols,x,_=line.split('\t');params[name]=torch.tensor([float(v) for v in x.split(',')],dtype=dtype).reshape(int(rows),int(cols))
        moments={n:torch.zeros_like(v) for n,v in params.items()};squares={n:torch.zeros_like(v) for n,v in params.items()}
        errors=[0.,0.,0.]
        for step in (1,2):
            rows=[line.split('\t') for line in (a.fixture/f'update{step}.tsv').read_text().splitlines()]
            grads={n:torch.tensor([float(v) for v in grad.split(',')],dtype=dtype).reshape_as(params[n]) for n,cap,box,grad,x,m,v in rows}
            norm=torch.sqrt(sum((g*g).sum() for g in grads.values()));factor=min(1.,1./norm.item())
            for name,cap,box,grad,x,m,v in rows:
                g=grads[name]*factor;moments[name]=.9*moments[name]+.1*g;squares[name]=.999*squares[name]+.001*g*g
                params[name]=params[name]-(2e-4*step/1000)*(moments[name]/(1-.9**step))/(torch.sqrt(squares[name]/(1-.999**step))+1e-8)
                cap=float(cap)
                if box=='true':params[name].clamp_(-cap,cap)
                else:
                    # gap-space projection avoids catastrophic maxAbs-cap subtraction.
                    projected=[]
                    for row in params[name]:
                        if row.abs().sum()<=cap:projected.append(row);continue
                        largest=row.abs().max();gaps=(largest-row.abs()).sort().values;delta=torch.tensor(cap,dtype=dtype)
                        for i in range(1,len(gaps)):
                            if gaps[i]>=delta:break
                            delta=delta+(gaps[i]-delta)/(i+1)
                        projected.append(row.sign()*torch.clamp(delta-(largest-row.abs()),min=0))
                    params[name]=torch.stack(projected)
                for j,(actual,expected) in enumerate(zip((params[name],moments[name],squares[name]),(x,m,v))):
                    expected=torch.tensor([float(f) for f in expected.split(',')],dtype=torch.float64).reshape_as(actual)
                    error=(actual.double()-expected).abs().max().item();errors[j]=max(errors[j],error)
                    assert error<(2e-13 if dtype==torch.float64 else (2e-7,2e-8,2e-10)[j]),(dtype,name,step,j,error)
        print(dtype,'TWO_PROJECTED_ADAM_STEPS_PASS weights_m_v_max_abs',errors)
