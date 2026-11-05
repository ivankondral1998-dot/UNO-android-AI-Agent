import math
z=math.tanh(math.tanh(.47))
h=(1-2**-8)*math.tanh(.9*math.tanh(2*z))+2**-9*z
q=1/(1+math.exp(-4*h))
assert q<.9
print(q)
