#!/usr/bin/env python3
"""Shared coefficient conflicting-label no-go, restricted scalar S5 only."""
import math
def sig(t): return 1/(1+math.exp(-t))
def q(x,c):
 z=math.tanh(math.tanh(x))
 h=(1-2**-8)*math.tanh(.9*math.tanh(c*z))+2**-9*z
 return sig(4*h)
old_at_zero=q(.47,0)
new_at_zero=q(.42,0)
assert old_at_zero<.9 and new_at_zero>.1
for c in [-2,-1,-.01,0,.01,1,2]:
 old=q(.47,c);new=q(.42,c)
 assert not (old>=.9 and new<=.1)
print("CONDITIONAL_NO_GO",old_at_zero,new_at_zero)
