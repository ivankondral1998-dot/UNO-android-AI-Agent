#!/usr/bin/env python3
"""S4-form memory softmax dilution, not training or full UNO."""
import math,json
t=64/math.sqrt(128)
rows=[]
for n in (0,2,16,64,256,1024,4094):
 r=(math.exp(t)-math.exp(-t))/(math.exp(t)+math.exp(-t)+n)
 q=1/(1+math.exp(-4*r))
 rows.append(dict(n=n,live=n+2,retrieved=r,q=q))
assert rows[0]['q']>.98 and rows[-1]['q']<.57
print(json.dumps(rows,indent=2))
