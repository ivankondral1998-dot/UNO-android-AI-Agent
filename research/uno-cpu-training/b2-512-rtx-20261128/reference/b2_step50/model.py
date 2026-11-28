"""Astra B2 inventory, shared S4/S5, fixed-route T1 language research only.
The fixed full route is a training control; S6 weights allocated, not used/trained.
No production tokenizer, no Android admission, no effects.
"""
import math, torch
from torch import nn
from torch.nn import functional as F

class B2(nn.Module):
    def __init__(self,d=512):
        super().__init__(); assert d%64==0
        self.d=d; self.n=d//64; self.p=nn.ParameterDict();self.rules={};self.frozen={}
        def mat(n,r,c,cap=8,freeze=None):
            x=torch.empty(r,c);nn.init.xavier_uniform_(x);self.p[n]=nn.Parameter(x);self.rules[n]=(cap,False)
            if freeze is not None:self.frozen[n]=freeze
        def vec(n,r,cap=8,freeze=None,small=False):
            self.p[n]=nn.Parameter(torch.empty(r).uniform_(-.01,.01) if small else torch.zeros(r));self.rules[n]=(cap,True)
            if freeze is not None:self.frozen[n]=freeze
        mat('E_text',32768,d);mat('W_audio',d,80);mat('W_image',d,768);mat('W_sensor',d,64);mat('W_meta',d,32);vec('e_modality',6*d,1,small=True);vec('b_z',d,1)
        for n in ('U_s','U_g'):mat(n,d,d,1)
        for n in ('W_q','W_k','W_v'):mat(n,128,d,2)
        mat('W_r',d,128,2)
        for j in range(self.n):
            for l in range(2):
                k=f'{j}_{l}';mat('A_'+k,256,d,1);mat('C_'+k,256,d,2);mat('B_'+k,64,256,.9);vec('a_'+k,256);vec('b_'+k,64)
        for n,r in [('verb',128),('outcome',128),('observable',128),('ctc',128),('belief',128),('speech',258),('V',1),('risk',1),('halt',1),('conf',1)]:
            freeze=list(range(24,128)) if n=='verb' else list(range(3))+list(range(24,128)) if n in ('outcome','observable') else None
            mat('W_'+n,r,d,freeze=freeze);vec('b_'+n,r,freeze=freeze)
        vec('b_text',32768);mat('W_mask',self.n,2*d+4);vec('b_mask',self.n);mat('W_wake',1,32);vec('b_wake',1)
        self.count=sum(p.numel() for p in self.parameters());expected=32768*d+951*d+2*d*d+4*128*d+2*(8*d*d+4*64*d+5*d)+902*(d+1)+32768+self.n*(2*d+5)+33
        assert self.count==expected,(self.count,expected)
        self.project()
        for n,rows in self.frozen.items():self.p[n].register_hook(lambda g,rows=rows:g.index_fill(0,torch.tensor(rows,device=g.device),0))
    @torch.no_grad()
    def project(self,opt=None):
        # Euclidean row-L1 projection, decoded FP32 check with rounding margin.
        for n,p in self.p.items():
            cap,box=self.rules[n]
            if not torch.isfinite(p).all():raise ValueError('nonfinite '+n)
            if box:p.clamp_(-cap,cap)
            else:
                x=p.double();mask=x.abs().sum(-1)>cap
                if mask.any():
                    a=x[mask];u=a.abs().sort(-1,descending=True).values;cs=u.cumsum(-1)-cap*(1-2e-7);k=torch.arange(1,u.shape[-1]+1,dtype=u.dtype,device=u.device);rho=(u>cs/k).sum(-1).clamp_min(1);theta=cs.gather(1,(rho-1)[:,None])/rho[:,None];p[mask]=(a.sign()*(a.abs()-theta).clamp_min(0)).float()
                if (p.double().abs().sum(-1)>cap).any():raise ValueError('decoded cap '+n)
            if n in self.frozen:
                p[self.frozen[n]]=0
                if opt:
                    for v in opt.state.get(p,{}).values():
                        if torch.is_tensor(v) and v.shape==p.shape:v[self.frozen[n]]=0
    def lin(self,x,w,b=None):return F.linear(x,self.p[w],self.p[b] if b else None)
    def packed(self):
        # Stack the same matrices once per sequence; not independent weights.
        p=self.p;keys=[f'{j}_{l}' for j in range(self.n) for l in range(2)]
        return (torch.cat([p['A_'+k] for k in keys]),torch.cat([p['C_'+k] for k in keys]),torch.stack([p['B_'+k] for k in keys]),torch.cat([p['a_'+k] for k in keys]),torch.stack([p['b_'+k] for k in keys]))
    def event(self,tok,s,g,meta,bank=(),K=1,packed=None):
        assert 1<=K<=8
        p=self.p;z0=torch.tanh(p['E_text'][tok]+self.lin(s,'U_s')+self.lin(g,'U_g')+self.lin(meta,'W_meta')+p['e_modality'].view(6,self.d)[0]+p['b_z'])
        query=torch.tanh(self.lin(z0,'W_q'));scores=None
        if bank:
            keys,vals=map(lambda a:torch.stack(a,1),zip(*bank));scores=torch.einsum('bm,bnm->bn',query,keys)/math.sqrt(128);r=torch.einsum('bn,bnm->bm',scores.softmax(-1),vals)
        else:r=torch.zeros_like(query)
        z=torch.tanh(z0+self.lin(r,'W_r'));h=.5*s+.5*z
        A,C,B,a,b=packed if packed is not None else self.packed()
        cz=F.linear(z,C,a);bs=len(tok)
        for _ in range(K):
            u=torch.tanh(F.linear(h,A)+cz).reshape(bs,self.n*2,256)
            branch=torch.tanh(torch.einsum('bnu,nou->bno',u,B)+b).reshape(bs,self.n,2,64)
            h=.5*h+.5*branch.mean(2).reshape(bs,self.d)
        return h,scores
    def language(self,x,active_ids,K=1):
        B,L=x.shape;s=torch.zeros(B,self.d,device=x.device);g=torch.zeros_like(s);states=[];pack=self.packed()
        for t in range(L):
            meta=torch.zeros(B,32,device=x.device);meta[:,1]=1;meta[:,4]=1;meta[:,14]=t/max(1,L)
            s,_=self.event(x[:,t],s,g,meta,K=K,packed=pack);states.append(s)
        h=torch.stack(states,1)
        return F.linear(h,self.p['E_text'][active_ids],self.p['b_text'][active_ids])
