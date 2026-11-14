#!/usr/bin/env python3
"""Analytic ceiling of fixed-head scalar S5, no optimization or training."""
import math
import json

def sigmoid(t):
    return 1/(1+math.exp(-t))

def state(x,c):
    z=math.tanh(math.tanh(x))
    return (1-2**-8)*math.tanh(.9*math.tanh(c*z))+2**-9*z

def probability(x,c):
    return sigmoid(4*state(x,c))

rows=[]
for x in (.47,.5):
    qmin=probability(x,-2)
    qzero=probability(x,0)
    qmax=probability(x,2)
    assert qmin<qzero<qmax
    rows.append({"x":x,"qmin":qmin,"qzero":qzero,"qmax":qmax,
                 "needed_head_at_cap":math.log(9)/state(x,2)})
assert rows[0]["qmax"]<.9<rows[1]["qmax"]
print(json.dumps({"status":"CONDITIONAL_SCALAR_CEILING",
                  "fixed_head":4,"C_cap":2,"K":8,
                  "note":"q(c) monotone for positive x; cap sets global max within this scalar fixture",
                  "rows":rows},indent=2))
