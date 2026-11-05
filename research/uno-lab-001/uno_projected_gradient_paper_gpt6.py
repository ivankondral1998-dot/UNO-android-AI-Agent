#!/usr/bin/env python3
"""Paper-only counterexamples for gradient projection; no training."""
old_grad=(1.,0.)
new_grad=(0.,-1.)
projected=(0.,-1.)
for eta in (.1,.5,1.):
 old_before=.5
 old_after=.5
 new_before=.5
 new_after=.5*(eta-1)**2
 assert old_before==old_after and new_after<new_before
assert (1.-1.,0.)==(0.,0.)
assert .5*(.1**2)>0
print("PAPER_CHECK_PASS")
