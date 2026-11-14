#!/usr/bin/env python3
"""Independent reimplementation of Grok sequential small-weight paper experiment.
No code imports from Grok. Same declared dataset, gradients and frozen criteria.
"""
import json, math, platform, random, sys
SEED=20261105
ETA=.05
N=400
STEPS=300
PASS=.9

def logistic(t):
    if t>=0: return 1/(1+math.exp(-t))
    e=math.exp(t)
    return e/(1+e)

def scalar(a,b):return sum(x*y for x,y in zip(a,b))
def old_label(x):return int(x[1]>0)
def new_label(x):return int(sum(x)>0)
def shift(x):return (x[0]+1, x[1], x[2], x[3])
def accuracy(func, data, label):return sum(func(row)==label(row) for row in data)/len(data)

class SharedNetwork:
    def __init__(self, allow_shared_change, anchor):
        self.matrix=[[float(i==j) for j in range(4)] for i in range(4)]
        self.heads=[[0.,0.,0.,0.],[0.,0.,0.,0.]]
        self.bias=[0.,0.]
        self.allow_shared_change=allow_shared_change
        self.anchor=anchor
        self.first_snapshot=None
    def latent(self,x):return [scalar(row,x) for row in self.matrix]
    def pred(self,which,x):
        return int(logistic(scalar(self.heads[which],self.latent(x))+self.bias[which])>=.5)
    def learn(self,which,examples,oracle):
        for _ in range(STEPS):
            gw=[0.]*4; gb=0.; gm=[[0.]*4 for _ in range(4)]
            for x in examples:
                h=self.latent(x)
                residual=logistic(scalar(self.heads[which],h)+self.bias[which])-oracle(x)
                gb+=residual
                for i in range(4):
                    gw[i]+=residual*h[i]
                    if self.allow_shared_change:
                        for j in range(4): gm[i][j]+=residual*self.heads[which][i]*x[j]
            inv=1/len(examples)
            for i in range(4):self.heads[which][i]-=ETA*gw[i]*inv
            self.bias[which]-=ETA*gb*inv
            if self.allow_shared_change:
                for i in range(4):
                    for j in range(4):
                        penalty=0 if which==0 or self.first_snapshot is None else self.anchor*(self.matrix[i][j]-self.first_snapshot[i][j])
                        self.matrix[i][j]-=ETA*(gm[i][j]*inv+penalty)
        if which==0:self.first_snapshot=[row[:] for row in self.matrix]

def evaluate(label,update,shiftflag,old_rows,new_rows,adapt):
    model=SharedNetwork(update,label)
    model.learn(0,adapt,old_label)
    pre=accuracy(lambda x:model.pred(0,x),old_rows,old_label)
    model.learn(1,adapt,new_label)
    post=accuracy(lambda x:model.pred(0,x),old_rows,old_label)
    new=accuracy(lambda x:model.pred(1,x),new_rows,new_label)
    translated=[shift(x) for x in new_rows]
    shifted=accuracy(lambda x:model.pred(1,x),translated,new_label)
    old_shifted=accuracy(lambda x:model.pred(0,x),[shift(x) for x in old_rows],old_label)
    return dict(old_before=round(pre,4),old_after=round(post,4),new=round(new,4),transfer=round(shifted,4),old_transfer=round(old_shifted,4),pass_all=post>=PASS and new>=PASS and shifted>=PASS,
                trunk_displacement=sum(abs(model.matrix[i][j]-float(i==j)) for i in range(4) for j in range(4)))

def main():
    rng=random.Random(SEED)
    cases=[(rng.uniform(-1.,0.),rng.uniform(-1.,1.),rng.uniform(-1.,1.),rng.uniform(-1.,1.)) for _ in range(N)]
    train=cases[:200]; accept=cases[200:280]; old_cases=cases[280:340]; new_cases=cases[340:400]
    assert len(set(cases))==400 and all(-1<=shift(x)[0]<=1 for x in cases)
    assert all(old_label(x)==old_label(shift(x)) for x in cases)
    results={
        'frozen':evaluate(0.,False,False,old_cases,new_cases,train),
        'anchor':evaluate(.1,True,False,old_cases,new_cases,train),
        'free':evaluate(0.,True,False,old_cases,new_cases,train),
    }
    assert len(accept)==80 # held apart, not trained against
    print(json.dumps(dict(status='INDEPENDENT_PAPER_REPLAY_NOT_UNO',seed=SEED,split={'adapt':200,'accept_unused':80,'old_eval':60,'new_eval':60},
                          criteria={'old_after':PASS,'new':PASS,'T_new':PASS},env={'python':sys.version,'platform':platform.platform()},results=results),indent=2,sort_keys=True))
if __name__=='__main__':main()
