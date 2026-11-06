"""Paper fixtures only; no UNO runtime, training, Android or network."""
import hashlib,json,math,struct
from pathlib import Path
out=[]
def check(name,condition):
 out.append({'check':name,'result':'PASS' if condition else 'FAIL'})
 if not condition: raise AssertionError(name)
old=Path(__file__).resolve().parent.parent/'uno_vnext'
if old.exists():
 for name,digest in json.loads((old/'SHA256_MANIFEST.json').read_text()).items():
  check('original_hash:'+name,hashlib.sha256((old/name).read_bytes()).hexdigest()==digest)
for d,V,b,J,m,rank,expected in [(256,8192,32,1,64,32,3012047),(256,8192,32,1,64,0,3339727),(384,16384,64,1,64,0,8698053),(512,32768,64,2,128,0,23015887),(1024,32768,64,2,128,0,55451639)]:
 n=d//b; ru=4*b
 branch=J*n*(2*ru*d+ru*b+ru+b) if rank==0 else J*n*(2*(ru*rank+rank*d)+ru*b+ru+b)
 total=V*d+951*d+2*d*d+4*m*d+branch+902*(d+1)+V+n*(2*d+5)+33
 check('parameter_sum:'+str((d,rank)),total==expected)
check('record_prefix_104',struct.calcsize('<4Q3I2H2IB7x5Q')==104)
check('record_p32_232',((104+4*32+7)//8)*8==232)
check('record_capacity_4096',232*4096==950272)
check('norm_budget_counterexample',0.9*(1+0.05)>0.9)
check('new_bound',abs((0.5+0.5*0.9*1.05)-0.9725)<1e-14)
check('alpha_zero_not_contraction',1-0+0*0.9==1)
# Exact scalar projected logistic step, includes adverse old-task label.
sig=lambda x:1/(1+math.exp(-x))
loss=lambda w,y:math.log1p(math.exp(w))-y*w
w=0.; eta=1.; wp=max(-1,min(1,w+eta*(1-sig(w))))
check('one_label_descent',loss(wp,1)<loss(w,1))
check('opposite_label_forgetting',loss(wp,0)>loss(w,0))
check('summary_collision',0.5*1+0.5*(-1)==0)
print(json.dumps(out,indent=2,ensure_ascii=False))
