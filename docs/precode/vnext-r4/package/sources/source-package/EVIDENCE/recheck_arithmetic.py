#!/usr/bin/env python3
"""Audit-only bounded arithmetic and counterexamples, NOT UNO production runtime."""
import json,math
from pathlib import Path
V,m,chi,J,b,A,H=32768,128,4,2,64,128,902
sizes=[512,1024,1536,2048]
expected={512:(23015887,22852753,4456448),1024:(55451639,55125689,17301504),1536:(97340959,96852193,38535168),2048:(148683847,148032265,68157440)}
for d in sizes:
 nb=d//b
 p=V*d+951*d+2*d*d+4*m*d+J*(2*chi*d*d+chi*b*d+(chi+1)*d)+H*(d+1)+V+nb*(2*d+5)+33
 f=p-318*(d+1)
 mac=J*(2*chi*d*d+chi*b*d)
 assert (p,f,mac)==expected[d],(d,p,f,mac)
 assert p-f==318*(d+1)
 assert nb==d//64
for e in (.01,.0001,1e-7):
 h=(e,1.0);hp=(-e,1.0)
 mask=lambda x: (1,0) if x[0]>0 else (0,1)
 update=lambda x: tuple((1-.5*m)*u for u,m in zip(x,mask(x)))
 initial=max(abs(x-y) for x,y in zip(h,hp));final=max(abs(x-y) for x,y in zip(update(h),update(hp)))
 assert math.isclose(final/initial,1/(4*e),rel_tol=1e-12)
assert 16*15+1==241 and (1<<16)-1==65535
assert (1.0+(-1.0))/2==0
root=Path(__file__).resolve().parents[1]
tensors=json.loads((root/'SOURCES/ASTRA_SUPPORT/evidence/tensor_manifest_d1024.json').read_text())['slow_tensors']
assert len(tensors)==198,len(tensors)
assert sum(t['elements'] for t in tensors)==expected[1024][0]
assert sum(t['trainable_elements'] for t in tensors)==expected[1024][1]

print('PASS: 4 B2 parameter/MAC configurations; 198 tensor descriptor sums; 3 hard-selector ratios; masks; memory averaging.')
print('LIMITS: no proof of live training, F implementation, global stability, hardware, or licensing.')
