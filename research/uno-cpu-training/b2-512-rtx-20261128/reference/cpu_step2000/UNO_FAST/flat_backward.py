"""Experimental flattened matrix-vector TBPTT; same F and gradients."""
import torch
from torch.nn import functional as F

@torch.no_grad()
def loss_and_grad(model, tokens, targets, initial):
    if tokens.ndim != 1 or tokens.shape != targets.shape or not tokens.numel():
        raise ValueError("invalid TBPTT window")
    states, z0s, zs, h0s, us, vs, hs = [], [], [], [], [], [], []
    state = initial
    af = model.A.view(-1, model.width)
    cf = model.C.view(-1, model.width)
    layout = model.a.shape
    for token in tokens.unbind():
        states.append(state)
        z0 = torch.tanh(model.E[token]+model.Us@state+model.e+model.bz)
        z = torch.tanh(z0)
        h0 = .5*state+.5*z
        u = torch.tanh((af@h0).view(layout)+(cf@z).view(layout)+model.a)
        v = torch.tanh((model.B@u.unsqueeze(-1)).squeeze(-1)+model.b)
        state = .5*h0+.5*v.mean(0).reshape(model.width)
        z0s.append(z0); zs.append(z); h0s.append(h0); us.append(u); vs.append(v); hs.append(state)
    hs=torch.stack(hs)
    logits=F.linear(hs,model.E,model.b_text)
    loss=F.cross_entropy(logits,targets)
    if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(state).all()):
        raise ValueError("nonfinite forward")
    dl=torch.softmax(logits,dim=-1)
    dl.scatter_add_(1,targets[:,None],-torch.ones_like(targets[:,None],dtype=dl.dtype))
    dl.div_(tokens.numel())
    gh=dl@model.E
    carry=torch.zeros_like(initial)
    dvs,dus,dps=[],[],[]
    at=af.T
    ct=cf.T
    bt=model.B.transpose(-1,-2)
    for i in range(tokens.numel()-1,-1,-1):
        g=gh[i]+carry
        dv=.25*g.reshape(-1,64).unsqueeze(0)*(1-vs[i].square())
        du=(bt@dv.unsqueeze(-1)).squeeze(-1)*(1-us[i].square())
        gh0=.5*g+at@du.reshape(-1)
        gz=.5*gh0+ct@du.reshape(-1)
        dp=gz*(1-zs[i].square())*(1-z0s[i].square())
        carry=.5*gh0+model.Us.T@dp
        dvs.append(dv);dus.append(du);dps.append(dp)
    dv=torch.stack(dvs[::-1],dim=2) # J,blocks,T,64
    du=torch.stack(dus[::-1],dim=2) # J,blocks,T,256
    dp=torch.stack(dps[::-1])
    u=torch.stack(us,dim=2)
    model.A.grad=du.transpose(-1,-2)@torch.stack(h0s)
    model.C.grad=du.transpose(-1,-2)@torch.stack(zs)
    model.B.grad=dv.transpose(-1,-2)@u
    model.Us.grad=dp.T@torch.stack(states)
    model.E.grad=dl.T@hs
    model.E.grad.index_add_(0,tokens,dp)
    model.a.grad=du.sum(2)
    model.b.grad=dv.sum(2)
    model.e.grad=dp.sum(0)
    model.bz.grad=model.e.grad.clone()
    model.b_text.grad=dl.sum(0)
    return loss,state,carry
