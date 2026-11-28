"""Fixed K1 language route: compact active rows in RAM, canonical weights on disk."""
import torch
from torch import nn
from torch.nn import functional as F
from model_audit import B2

class FastB2(B2):
    def compact(self, ids):
        assert not hasattr(self,'full_text')
        self.active_ids=ids.detach().cpu().clone()
        self.full_text={n:self.p[n].detach().cpu().clone() for n in ('E_text','b_text')}
        for n in self.full_text:
            self.p[n]=nn.Parameter(self.p[n].detach().index_select(0,ids).clone())
        # In this fixed language route these tensors have identically zero or no gradient.
        # They remain in the canonical state, but no optimizer slots are allocated.
        used={'E_text','b_text','U_s','W_meta','e_modality','b_z'}
        used.update(n for n in self.p if n.startswith(('A_','B_','C_','a_','b_')) and n.split('_')[1].isdigit())
        for n,p in self.p.items():p.requires_grad_(n in used)
        self.register_buffer('remap_text',torch.full((32768,),-1,dtype=torch.long,device=ids.device),persistent=False)
        self.remap_text[ids]=torch.arange(len(ids),device=ids.device)
        self.trainable_count=sum(p.numel() for p in self.p.values() if p.requires_grad)
        return self
    def canonical_weights(self):
        result=super().state_dict()
        for n,base in self.full_text.items():
            q=base.clone();q.index_copy_(0,self.active_ids,self.p[n].detach().cpu());result['p.'+n]=q
        return result
    def load_canonical(self,weights):
        # Inactive text rows must remain byte-identical to the initialization lineage.
        compact=dict(weights)
        for n,base in self.full_text.items():
            q=weights['p.'+n].detach().cpu();inactive=torch.ones(32768,dtype=torch.bool);inactive[self.active_ids]=False
            if q.shape!=base.shape or not torch.equal(q[inactive],base[inactive]):raise ValueError('INACTIVE_ROWS_CHANGED '+n)
            compact['p.'+n]=q.index_select(0,self.active_ids)
        return self.load_state_dict(compact,strict=True)
    def language(self,x,active_ids,K=1):
        if K!=1:raise ValueError('FIXED_K1_ONLY')
        B,L=x.shape;p=self.p;s=torch.zeros(B,self.d,device=x.device);states=[]
        A,C,Bmat,a,b=self.packed()
        # Metadata is shared by batch members. Input-dependent work is done once.
        meta=torch.zeros(L,32,device=x.device);meta[:,1]=1;meta[:,4]=1;meta[:,14]=torch.arange(L,device=x.device)/max(1,L)
        mb=F.linear(meta,p['W_meta']);embedded=p['E_text'][self.remap_text[x]]
        em=p['e_modality'].view(6,self.d)[0];bias=p['b_z']
        for t in range(L):
            z0=torch.tanh(embedded[:,t]+F.linear(s,p['U_s'])+mb[t]+em+bias)
            z=torch.tanh(z0);h=.5*s+.5*z
            u=torch.tanh(F.linear(h,A)+F.linear(z,C,a)).reshape(B,self.n*2,256)
            branch=torch.tanh(torch.bmm(u.transpose(0,1),Bmat.transpose(1,2)).transpose(0,1)+b).reshape(B,self.n,2,64)
            s=.5*h+.5*branch.mean(2).reshape(B,self.d);states.append(s)
        return F.linear(torch.stack(states,1),p['E_text'],p['b_text'])
    @torch.no_grad()
    def project_fast(self,opt):
        # Same row-wise L1 Euclidean projection, batched by compatible shape/cap.
        groups={};checks=[]
        for n,p in self.p.items():
            if p.grad is None:continue
            cap,box=self.rules[n]
            if n in self.frozen:raise ValueError('UNEXPECTED_ACTIVE_FROZEN_ROWS '+n)
            groups.setdefault((tuple(p.shape),cap,box),[]).append(p)
        for (shape,cap,box),ps in groups.items():
            q=torch.stack(ps);checks.append(torch.isfinite(q).all())
            if box:q.clamp_(-cap,cap)
            else:
                x=q.reshape(-1,shape[-1]).double();mask=x.abs().sum(-1)>cap
                if mask.any():
                    a=x[mask];u=a.abs().sort(-1,descending=True).values;cs=u.cumsum(-1)-cap*(1-2e-7);k=torch.arange(1,u.shape[-1]+1,dtype=u.dtype,device=u.device);rho=(u>cs/k).sum(-1).clamp_min(1);theta=cs.gather(1,(rho-1)[:,None])/rho[:,None];x[mask]=(a.sign()*(a.abs()-theta).clamp_min(0)).to(q.dtype).double()
                q=x.reshape(q.shape).to(q.dtype);checks.append((q.double().abs().sum(-1)<=cap).all())
            torch._foreach_copy_(ps,list(q.unbind(0)))
        if not checks or not bool(torch.stack(checks).all()):raise ValueError('PROJECT_NONFINITE_OR_CAP')
