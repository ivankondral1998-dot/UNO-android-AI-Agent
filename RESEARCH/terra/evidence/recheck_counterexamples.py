#!/usr/bin/env python3
"""Deterministic mathematical checks only; no model training or Android actions."""
import hashlib, json, math

def total(d):
    V,m,b,chi,J,H=32768,128,64,4,2,902
    return V*d+951*d+2*d*d+4*m*d+J*(2*chi*d*d+chi*b*d+(chi+1)*d)+H*(d+1)+V+(d//b)*(2*d+5)+33

out={}
for d,expected in [(512,23015887),(1024,55451639)]:
    p=total(d); assert p==expected
    out[f'd{d}']={'allocated':p,'free':p-318*(d+1), 'fp32_adam_16bytes_MiB':16*p/(2**20),'raw_fp16_MiB':2*p/(2**20)}

# One eligible memory candidate gives p=1 and exactly zero softmax CE gradient.
q,k=0.73,1.21
p=math.exp(q*k)/math.exp(q*k)
loss=-math.log(p); grad=(p*k-k)
assert loss==0 and grad==0
out['singleton_retrieval']={'probability':p,'loss':loss,'d_loss_d_q':grad}

# Identical observable logs, different unobservable physical success rates.
world_a={'R1_Y1':0.5,'R0_Y0':0.5}; world_b={'R1_Y1':0.5,'R0_Y1':0.5}
assert world_a['R1_Y1']==world_b['R1_Y1']
out['censoring']={'world_a_success':0.5,'world_b_success':1.0,'both_observed_R1Y1':0.5}

# Shared parameter used twice: h1=w*h0+x, h2=w*h1+x; sum both paths.
w,h0,x=0.4,0.7,0.2
f=lambda w:w*(w*h0+x)+x
exact=2*w*h0+x; eps=1e-6; fd=(f(w+eps)-f(w-eps))/(2*eps)
last_only=w*h0+x
assert abs(exact-fd)<1e-9 and abs(last_only-fd)>0.1
out['shared_weight_gradient']={'exact':exact,'central_difference':fd,'wrong_last_use_only':last_only}

# Fixed, full mask versus an inactive coordinate; no global contraction follows.
alpha,gamma=0.5,0.9; factor=(1-alpha)+alpha*gamma
assert abs(factor-0.95)<1e-15 and (1-alpha*0*(1-gamma))==1
out['contraction']={'full_mask_bound':factor,'eight_steps_bound':factor**8,'inactive_coordinate_bound':1.0}

# Fixed observed proposal permits consent at prepare and misses expiry on later dispatch,
# according to reviewed host-controller predicates. This models conditions; it does not run Kotlin.
t_prepare,t_dispatch,expires,deadline=100,150,120,200
prepared=(t_prepare<expires and t_prepare<deadline)
legacy_dispatch=(t_dispatch<deadline)
correct_dispatch=(t_dispatch<deadline and t_dispatch<expires)
assert prepared and legacy_dispatch and not correct_dispatch
out['consent_expiry_logic']={'prepare':prepared,'source_dispatch_predicate':legacy_dispatch,'candidate_dispatch_predicate':correct_dispatch,'simulated':True}

print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
