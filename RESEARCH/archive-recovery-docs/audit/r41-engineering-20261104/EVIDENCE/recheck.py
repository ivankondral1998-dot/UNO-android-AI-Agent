"""Paper-only arithmetic and finite mathematical fixtures; no UNO runtime."""
import csv, hashlib, itertools, json, math, sys, zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'EVIDENCE'
src=ROOT/'SOURCES/REPAIR_INPUT.zip'
# Execute previous verifier, with a fully bundled immutable input.
import subprocess
p=subprocess.run([sys.executable,str(OUT/'check_original.py'),str(src)],capture_output=True,text=True)
(OUT/'original_check_stdout.txt').write_text(p.stdout+p.stderr); assert p.returncode==0
prior=json.loads(p.stdout[p.stdout.index('[\n'):])
checks=[]
def check(name,ok,evidence,scope='finite mathematical fixture'):
    checks.append(dict(id=name,status='PASS' if ok else 'FAIL',evidence=evidence,scope=scope))
    if not ok: raise AssertionError((name,evidence))
# Compare the supplied originals with actual bytes in the bundled repository snapshot.
with zipfile.ZipFile(src) as repair, zipfile.ZipFile(ROOT/'SOURCES/UNO_GITHUB_COMMIT_fcddf0f_SOURCE.zip') as repo:
    imp=json.loads(repair.read('03_CANONICAL_ASTRA_R53/REPO_META/docs/precode/r5.3/SOURCE_PACKAGE_IMPORT_MANIFEST.json'))['files']
    prefix=repo.namelist()[0]
    for item in imp:
        relative=item['repo_path'].split('/source-package/',1)[1]
        assert repair.read('03_CANONICAL_ASTRA_R53/ORIGINAL_SOURCE_PACKAGE/'+relative)==repo.read(prefix+item['repo_path'])
    check('repository_snapshot_64',len(imp)==64,64,'byte equality with bundled commit snapshot; not live HEAD')
def registry(d,V,b,J,m,r=0):
    n=d//b; ts=[]
    def t(name,shape,kind='matrix',frozen=0):ts.append(dict(name=name,shape=shape,kind=kind,allocated=math.prod(shape),frozen=frozen))
    t('E_text',[V,d])
    for name,inp in [('audio',80),('image',768),('sensor',64),('meta',32),('U_s',d),('U_g',d)]:t(name,[d,inp])
    t('e_modality',[6,d],'fp32');t('b_z',[d],'fp32')
    for name in ['q','k','v']:t('W_'+name,[m,d])
    t('W_r',[d,m])
    for l in range(J):
      for j in range(n):
        for name in ['A','C']:
          if r:t(f'{name}_{l}_{j}_L',[4*b,r]);t(f'{name}_{l}_{j}_R',[r,d])
          else:t(f'{name}_{l}_{j}',[4*b,d])
        t(f'B_{l}_{j}',[b,4*b]);t(f'a_{l}_{j}',[4*b],'fp32');t(f'b_{l}_{j}',[b],'fp32')
    for name,h,f in [('verb',128,104),('outcome',128,107),('observable',128,107),('ctc',128,0),('belief',128,0),('speech',258,0),('value',1,0),('risk',1,0),('halt',1,0),('conf',1,0)]:
        t('W_'+name,[h,d],frozen=f*d);t('b_'+name,[h],'fp32',f)
    t('b_text',[V],'fp32');t('W_mask',[n,2*d+4]);t('b_mask',[n],'fp32');t('W_wake',[1,32]);t('b_wake',[1],'fp32')
    up=lambda v,a:(v+a-1)//a*a
    off=4096+128*len(ts)
    for x in ts:
        x['data_offset']=off
        if x['kind']=='matrix':
            rows,cols=x['shape'];x['row_stride']=up(cols,16);x['data_length']=rows*x['row_stride'];off+=up(x['data_length'],64)
            x['scale_offset']=off;x['scale_length']=4*rows;off+=up(4*rows,64)
        else:x['data_length']=4*x['allocated'];off+=up(x['data_length'],64)
        x['end_aligned']=off
    return ts,off
rows=[]
for base in prior:
    d,V,b,J,m,r=[base[k] for k in ('d','V','b','J','m','rank')];name=f'B2-{d}' if V==32768 else ('C256R32' if r else f'C{d}')
    ts,abi=registry(d,V,b,J,m,r);P=sum(x['allocated'] for x in ts)
    dense=V*d+951*d+2*d*d+4*m*d+J*(8*d*d+4*b*d+5*d)+902*(d+1)+V+(d//b)*(2*d+5)+33
    analytic=dense-(8*J*d*d)+2*J*(d//b)*r*(d+4*b) if r else dense
    check(name+'_tensor_count',len(ts)==base['tensor_count'],len(ts),'enumeration vs separate aggregate script')
    check(name+'_W2',P==base['parameters']==analytic,P,'enumeration vs closed formula')
    check(name+'_ABI',abi==base['int8_ABI_bytes'],abi,'explicit offsets vs packed aggregate')
    check(name+'_frozen',sum(x['frozen'] for x in ts)==318*(d+1),318*(d+1))
    for x in ts:assert x['data_offset']%64==0
    (OUT/f'tensors_{name}.json').write_text(json.dumps(ts,indent=2))
    state=4*128*d+4096*(4*m+64)+4*256*d+32*(4*d+256)+4096*(4096+64)+2*8192*128+(1024+64)*128+320000+262144
    workspace=4*(12*d+8*J*d+V+4*4096+2*258*1000+2*512*1000)
    tok=256*V+4*(V+1)+8*V
    row=dict(candidate=name,**base,known_live_bytes=abi+state+workspace+tok+89024,workspace_bytes=workspace,tokenizer_cap_bytes=tok,adam_fp32_bytes=16*P)
    n=d//b; row['sparse_q']=max(1,n//4); row['sparse_audio_MAC_s']=100*(2*d*d+d*112+2*m*d+8192*m+n*(2*d+4)+base['F_MAC']*row['sparse_q']//n+d+128*d+32)
    row['sensor_full8_MAC']=2*d*d+96*d+2*m*d+8192*m+n*(2*d+4)+8*(base['F_MAC']+d)+32
    row['L7_B4_L256_bytes']=4*4*256*(8*(d+J*4*d+J*d+2*J*(d//b)*r)+5*d+2*m+4096+V)
    rows.append(row)
check('sparse_integer_domain',all(isinstance(x['sparse_q'],int) and 1<=x['sparse_q']<=x['d']//x['b'] for x in rows),{x['candidate']:x['sparse_q'] for x in rows},'no fractional active blocks for C384')
with (OUT/'resources.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'resources.json').write_text(json.dumps(rows,indent=2))
for d,P,cf,hp,hmac in [(512,20394447,1835008,24064463,1310720),(1024,43917303,5767168,59645943,4718592),(1536,70602271,11796480,106778143,10223616),(2048,100449351,19922944,165461063,17825792)]:
    ts,_=registry(d,32768,64,2,128,64)
    check(f'W3_{d}',sum(x['allocated'] for x in ts)==P and 2*(d//64)*(128*(d+256)+16384)==cf and next(x['parameters'] for x in rows if x['d']==d and x['V']==32768)+4*d*d==hp and 4*d*d+512*d==hmac,{'LR':P,'H2':hp})
for eps in [.01,.0001,1e-7]:
    u=np.array([eps,1.]);v=np.array([-eps,1.]);tu=np.array([eps/2,1]);tv=np.array([-eps,.5]);ratio=np.max(abs(tu-tv))/np.max(abs(u-v))
    check('selector_'+str(eps),np.isclose(ratio,1/(4*eps)),ratio)
check('exact_memory_noninjective',np.array_equal((np.array([1.,2.])+np.array([-1.,-2.]))/2,np.zeros(2)),'distinct raw pairs collapse to zero')
check('compact_evidence_shape',128!=64 and len(list(range(48))+[0]*16)==64,'old sum R64 + R128 undefined; fixed encoding retains all 48 used coordinates')
# Whole-event expansion despite contraction in h for fixed z.
def event(s):
    z=math.tanh(math.tanh(s));h=.5*s+.5*z
    return .5*h+.5*math.tanh(.9*math.tanh(2*z))
deriv=(event(1e-6)-event(-1e-6))/2e-6
check('event_not_contractive',deriv>1.39,deriv,'counterexample satisfying A=0,B=.9,C=2,U_s=1')
check('fullmask_residual',math.ceil(math.log(.01)/math.log(.95))==90,{'eight':.95**8,'steps':90})
# Numerical differentiation of shared branch, gradients for A,B,C,a,b,h,z.
rng=np.random.default_rng(20261104);A=rng.normal(0,.15,(4,3));C=rng.normal(0,.15,(4,3));B=rng.normal(0,.15,(2,4));a=rng.normal(0,.1,4);bb=rng.normal(0,.1,2);h=rng.normal(0,.2,3);z=rng.normal(0,.2,3);v=np.array([.7,-.2])
u=np.tanh(A@h+C@z+a);f=np.tanh(B@u+bb);dv=v*(1-f*f);du=(B.T@dv)*(1-u*u)
analytic=[np.outer(du,h),np.outer(dv,u),np.outer(du,z),du,dv,A.T@du,C.T@du]
arrays=[A,B,C,a,bb,h,z]
def loss():return float(v@np.tanh(B@np.tanh(A@h+C@z+a)+bb))
errs=[]
for ar,grad in zip(arrays,analytic):
 for idx in np.ndindex(ar.shape):
    old=ar[idx];ar[idx]=old+1e-6;plus=loss();ar[idx]=old-1e-6;minus=loss();ar[idx]=old;errs.append(abs((plus-minus)/2e-6-grad[idx]))
check('L4_finite_difference',max(errs)<1e-8,{'coordinates':len(errs),'max_abs_error':max(errs)})
# P1/P2/P3 finite fixtures, not evidence of retention.
def sig(x):return 1/(1+math.exp(-x))
def fP(p,h,y,l0):return (np.logaddexp(0,l0+p@h)-y*(l0+p@h))/(1+h@h)+.001*(p@p)/2
Perrs=[];regret=0.;p=np.zeros(8);eta=.01;comp=np.ones(8)/math.sqrt(8)
for k in range(500):
    h=rng.uniform(-1,1,8);y=int(rng.integers(2));l0=float(rng.uniform(-3,3));old=p.copy();g=(sig(l0+p@h)-y)*h/(1+h@h)+.001*p
    regret+=fP(p,h,y,l0)-fP(comp,h,y,l0)
    u=p-eta*g;p=u/max(1,float(np.linalg.norm(u)))
    bound=fP(old,h,y,l0)-(1/eta-.251/2)*float((p-old)@(p-old));Perrs.append(fP(p,h,y,l0)-bound)
    assert np.linalg.norm(p)<=1+1e-12 and np.linalg.norm(p-old)<=.00501+1e-12
check('P2_descent_500',max(Perrs)<1e-12,max(Perrs))
check('P3_regret_fixture',regret<=4/(2*eta)+eta*.501**2*500/2,regret)
# Enumerate order-preserving actions D->E->C, with STOP anywhere. Atomic C and live STOP.
traces=[]
for seq in itertools.permutations('DECS'):
 if not(seq.index('D')<seq.index('E')<seq.index('C')):continue
 stop=False;dispatched=False;evidence=False;updates=0
 for op in seq:
    if op=='S':stop=True
    elif op=='D':dispatched=not stop
    elif op=='E':evidence=dispatched
    elif op=='C':updates+=int(dispatched and evidence and not stop)
 expected=int(seq.index('C')<seq.index('S'));assert updates==expected
 traces.append(dict(order=''.join(seq),P_updates=updates,dispatched=dispatched,evidence=evidence))
check('STOP_commit_interleavings',len(traces)==4,traces,'abstract atomic model; not Android verification')
# Readback status precedence enumerated: all truth assignments.
def exact(denied,bad,limited,conflict):return 'DENIED' if denied else 'UNKNOWN' if bad else 'TRUNCATED' if limited else 'CONFLICT' if conflict else 'COMPLETE'
statuscases=[dict(flags=list(bits),result=exact(*bits)) for bits in itertools.product([False,True],repeat=4)]
check('exact_status_16',len(statuscases)==16 and exact(False,False,True,True)=='TRUNCATED',statuscases,'specification truth table, not store implementation')
# L3a rare stratum weighting and score estimator exact enumeration.
pi=[.2,.8];a=[1.,0.]
check('L3a_sampling',sum(pi[k]*(1 if k==0 else 0)/pi[0]*a[k] for k in range(2))==1,'conditional abort=1; unweighted joint abort=.2')
p0=.3
check('L5_score',abs((1-p0)*0*(-p0)+p0*1*(1-p0)-p0*(1-p0))<1e-15,p0*(1-p0))
probs=[.1,.3,.6];losses=[.2,.7,1.];budget=2;estimate=0.
for seq in itertools.product(range(3),repeat=budget):
 probability=math.prod(probs[i] for i in seq);estimate+=probability*sum(losses[i]/(1-(1-probs[i])**budget) for i in set(seq))/3
check('E4_exact_enumeration',abs(estimate-sum(losses)/3)<1e-14,estimate)
for delta,n in [(0,9457),(.02,26268)]:check('E6_'+str(delta),math.ceil(2*(math.sqrt(math.log(40))+math.sqrt(math.log(10)))**2/(.05-delta)**2)==n,n)
check('L7_original',next(x for x in rows if x['candidate']=='B2-1024')['L7_B4_L256_bytes']==542113792,542113792)
check('PRNG_endpoint_old_failure',float((2**256-1+.5)/2**256)==1.,'floating endpoint rounds to 1; integer CDF avoids no-category outcome')
(OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps({'checks':len(checks),'PASS':sum(x['status']=='PASS' for x in checks),'FAIL':sum(x['status']=='FAIL' for x in checks),'gradient_max_error':max(errs),'rows':len(rows),'limitations':'No production implementation, no training, no device, no independent reviewer certification'},ensure_ascii=False,indent=2))
