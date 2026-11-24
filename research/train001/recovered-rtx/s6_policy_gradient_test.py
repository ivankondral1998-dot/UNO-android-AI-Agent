"""Frozen CPU gradient regressions; no optimizer or model weight update.
Run with host_verify.log from same revision. Enumerate all finite trajectories,
compare surrogate expectation to direct differentiation and finite differences.
"""
import math
import sys
from pathlib import Path
import torch
from s6_policy_gradient import Decision, prefix_log_probs, halt_log_prob, score_objective

torch.set_num_threads(1)
DT=torch.float64
passed=0

def t(x,grad=False): return torch.tensor(x,dtype=DT,requires_grad=grad)
def check(name,ok):
    global passed
    if not bool(ok): raise AssertionError(name)
    passed+=1
    print('PASS',name)

def reject(name,fn,reason):
    try:fn()
    except ValueError as e:check(name,str(e)==reason)
    else:raise AssertionError(name)

def grad(out,x):return torch.autograd.grad(out,x,retain_graph=True)[0]

def near(a,b,tol=1e-11):return bool(torch.as_tensor(a-b).abs().max()<tol)

# Independent scalar law, no use of PyTorch helper.
def plain_prefix(x,n,turn,eps,temp):
    a=[sum(x[(turn+i)%len(x)] for i in range(q))/math.sqrt(q) for q in range(1,n+1)]
    e=[math.exp((v-max(a))/temp) for v in a]
    return [eps/n+(1-eps)*v/sum(e) for v in e]

max_delta=max_fd=0.
count=0
for line in Path(sys.argv[1]).read_text().splitlines():
    if not line.startswith('ASTRA12_PREFIX\t'):continue
    _,n,turn,eps,temp,x,p=line.split('\t');n,turn,eps,temp=int(n),int(turn),float(eps),float(temp)
    x=list(map(float,x.split(',')));p=t(list(map(float,p.split(','))))
    logits=t(x,True);lp=prefix_log_probs(logits,n,turn,eps,temp)
    max_delta=max(max_delta,float((lp.exp()-p).abs().max().detach()))
    for i in range(n):
        g=grad(lp[i],logits)
        for j in range(len(x)):
            a=x.copy();b=x.copy();a[j]+=1e-5;b[j]-=1e-5
            fd=(math.log(plain_prefix(a,n,turn,eps,temp)[i])-math.log(plain_prefix(b,n,turn,eps,temp)[i]))/2e-5
            max_fd=max(max_fd,abs(g[j].item()-fd))
        if n==1 or eps==1:assert g.abs().max()==0
        assert all(g[(turn+j)%len(x)]==0 for j in range(n,len(x)))
    assert near((lp.exp().detach()[:,None]*torch.stack([grad(l,logits) for l in lp])).sum(0),torch.zeros_like(logits))
    count+=1
check('96 actual runtime prefix laws',count==96 and max_delta<2e-15)
check('all 960 prefix score coordinates vs finite difference',max_fd<1e-9)
print('prefix_max_prob_delta',max_delta,'prefix_max_fd_delta',max_fd)

# Baseline of second decision can depend on first decision, not vice versa.
x=t(math.log(.3/.7),True);p=x.sigmoid();bad=t(0);good=t(0)
for a in (False,True):
    lp1=halt_log_prob(x,a)
    for b in (False,True):
        lp2=halt_log_prob(x,b);mass=(lp1+lp2).detach().exp()
        loss=x*0;baseline2=t(float(a))
        good+=mass*score_objective(loss,[Decision(lp1,loss,t(0)),Decision(lp2,loss,baseline2)])
        bad+=mass*(-baseline2)*(lp1+lp2)
check('Astra baseline counterexample corrected',near(grad(good,x),t(0)))
check('wrong shared baseline reproduces -0.21',near(grad(bad,x),t(-.21)))

# Tiny bounded recurrent witness, NOT new F architecture or trained model.
# S5-form update with two possible prefixes, shared theta, state-dependent halt.
# q=1 permits up to 3 steps; q=2 up to 2. Forced final halt has zero score.
# Baselines depend on prior state and theta but are detached in surrogate.
def trajectories(theta,eps):
    lps=prefix_log_probs(torch.stack((theta[0]+theta[1],theta[2]-.2)),2,1,eps,.8)
    out=[]
    for q in (1,2):
        cap=4-q;h=theta[2]*.2;lpq=lps[q-1];previous=[];mass=lpq.exp()
        for k in range(1,cap+1):
            h=.5*h+.5*torch.tanh(theta[1]*h+theta[0]*q/2)
            loss=(h-.6)**2+.07*q*k
            if k==cap:
                ds=[Decision(lpq,loss,theta[0]**2)] + [Decision(lp,loss-t(.07*q*j),base) for lp,base,j in previous]
                out.append((mass,loss,score_objective(loss,ds)))
            else:
                z=theta[2]+h*theta[0];base=h+theta[1]**2
                stop=halt_log_prob(z,True);cont=halt_log_prob(z,False)
                ds=[Decision(lpq,loss,theta[0]**2)] + [Decision(lp,loss-t(.07*q*j),base0) for lp,base0,j in previous] + [Decision(stop,loss-t(.07*q*k),base)]
                out.append((mass*stop.exp(),loss,score_objective(loss,ds)))
                mass=mass*cont.exp();previous.append((cont,base,k))
    return out

def plain_objective(x,eps):
    probs=plain_prefix([x[0]+x[1],x[2]-.2],2,1,eps,.8);v=0.
    for q in (1,2):
        h=x[2]*.2;mass=probs[q-1];cap=4-q
        for k in range(1,cap+1):
            h=.5*h+.5*math.tanh(x[1]*h+x[0]*q/2)
            loss=(h-.6)**2+.07*q*k
            p=1. if k==cap else 1/(1+math.exp(-(x[2]+h*x[0])))
            v+=mass*p*loss;mass*=1-p
    return v

for eps in (0.,.05,.6,1.):
    theta=t([.4,-.3,.1],True);paths=trajectories(theta,eps)
    exact=sum(m*l for m,l,_ in paths);sur=sum(m.detach()*s for m,_,s in paths)
    check(f'mass and unchanged path value eps={eps}',near(sum(m for m,_,_ in paths),t(1)) and all(l.detach()==s.detach() for _,l,s in paths))
    actual=grad(sur,theta);expected=grad(exact,theta)
    check(f'causal shared theta score + direct derivative eps={eps}',near(actual,expected))
    fd=[];x=theta.detach().tolist()
    for j in range(3):
        a=x.copy();b=x.copy();a[j]+=1e-5;b[j]-=1e-5
        fd.append((plain_objective(a,eps)-plain_objective(b,eps))/2e-5)
    check(f'independent finite difference eps={eps}',near(actual,t(fd),1e-9))
    print('eps',eps,'grad',actual.tolist(),'max_error',float((actual-t(fd)).abs().max()))

x=t(.7,True);b=t(2,True);cost=t(3,True);l=x*x
s=score_objective(l,[Decision(halt_log_prob(x,True),cost,b)])
check('baseline and reward detached',torch.autograd.grad(s,[b,cost],allow_unused=True,retain_graph=True)==(None,None))
check('direct loss preserved',s.item()==l.item() and near(grad(s,x),2*x.detach()+1-x.detach().sigmoid()))
check('forced or terminal zero decisions',score_objective(l,[]) is l)
reject('empty support',lambda:prefix_log_probs(t([1.,2.]),0,0),'FIXED_NONEMPTY_SUPPORT')
reject('invalid rotation',lambda:prefix_log_probs(t([1.,2.]),2,-1),'TURN')
reject('nonfinite input',lambda:prefix_log_probs(t([1.,float('nan')]),2,0),'LOGITS')
reject('overflow prefix',lambda:prefix_log_probs(t([1e308,1e308]),2,0),'PREFIX_OVERFLOW')
reject('invalid temperature',lambda:prefix_log_probs(t([1.,2.]),2,0,temperature=math.inf),'POLICY_DOMAIN')
reject('underflow',lambda:prefix_log_probs(t([0.,-2000.]),2,0),'SOFTMAX_UNDERFLOW')
reject('saturated trainable hazard',lambda:halt_log_prob(t(1000.),True),'HALT_SATURATION')
reject('invalid log probability',lambda:score_objective(l,[Decision(t(1.),t(1.),t(0.))]),'LOG_PROB')
reject('advantage overflow',lambda:score_objective(l,[Decision(t(-1.),t(1e308),t(-1e308))]),'ADVANTAGE_OVERFLOW')
print('ASTRA12_CPU_PASS='+str(passed))
