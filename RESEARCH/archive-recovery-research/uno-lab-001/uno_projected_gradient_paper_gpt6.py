#!/usr/bin/env python3
"""Paper-only checks of conditional projected-gradient claim; no training."""
import math
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm2(a): return dot(a,a)
def projector(g_new,g_old):
 scale=dot(g_new,g_old)/norm2(g_old)
 return tuple(x-scale*y for x,y in zip(g_new,g_old))
old_grad=(1.,0.)
new_grad=(0.,-1.)
projected=projector(new_grad,old_grad)
assert projected==(0.,-1.)
for eta in (.1,.5,1.):
 delta=tuple(-eta*x for x in projected)
 old_before=.5
 old_after=.5*(1+delta[0])**2
 new_before=.5
 new_after=.5*(delta[1]-1)**2
 assert old_after==old_before and new_after<new_before
assert projector((1.,0.),old_grad)==(0.,0.)
# Active projection invalidates an unprojected first-order guarantee.
eta=.1
x=1/math.sqrt(1+eta*eta)
y=-eta/math.sqrt(1+eta*eta)
old_loss_increase=1-x
assert old_loss_increase>.0049
# First-order orthogonality does not imply exact old loss retention.
assert .5*eta*eta>0
print("PAPER_ONLY_PROJECTION_CHECKS_PASS",old_loss_increase)
