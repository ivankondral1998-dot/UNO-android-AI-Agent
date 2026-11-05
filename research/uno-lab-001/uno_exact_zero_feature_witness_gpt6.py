import math,json

def sigmoid(x): return 1/(1+math.exp(-x))

def forward(x, c):
    z=[math.tanh(math.tanh(v)) for v in x]
    h=[.5*v for v in z]
    for _ in range(8):
        f0=math.tanh(.9*math.tanh(c*z[2]))
        f1=math.tanh(.9*math.tanh(2*z[3]))
        h=[.5*h[0]+.5*f0,.5*h[1]+.5*f1,.5*h[2],.5*h[3]]
    return h

out=[]
for sign in (-1,1):
    xn=[0,0,sign*.5,0]
    xo=[0,0,0,sign*.5]
    n0=forward(xn,0);n1=forward(xn,2)
    o0=forward(xo,0);o1=forward(xo,2)
    qn0=sigmoid(4*n0[0]);qn1=sigmoid(4*n1[0]);qo0=sigmoid(4*o0[1]);qo1=sigmoid(4*o1[1])
    assert qn0==.5 and (qn1>.9 if sign==1 else qn1<.1)
    assert qo0==qo1
    out.append(dict(sign=sign,new_before=qn0,new_after=qn1,old_before=qo0,old_after=qo1))
print(json.dumps({'status':'EXACT_PRECHANGE_NONSEPARABILITY_AND_PROTECTED_ORTHOGONAL_OLD_CHANNEL','changed_coefficients':2,'c_before':0,'c_after':2,'results':out,'limitations':'hand-set; not a learning algorithm; fixed full mask; single-event; no generalization or Android'},indent=2))
