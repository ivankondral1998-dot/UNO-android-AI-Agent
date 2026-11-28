import torch
from model import B2
from reference128 import B2 as Old

torch.set_num_threads(3);torch.manual_seed(43)
a=Old();a.fixed_route=True;b=B2(128);b.load_state_dict(a.state_dict());
with torch.no_grad():
 for bank in [[],[(torch.rand(3,128)*2-1,torch.rand(3,128)*2-1) for _ in range(3)]]:
  s=torch.rand(3,128)*2-1;g=torch.rand(3,128)*2-1;m=torch.rand(3,32)*2-1;t=torch.tensor([1,52,543]);h,scores,_,_=a.event(t,s,g,m,bank,3);hh,ss=b.event(t,s,g,m,bank,K=2);err=(h-hh).abs().max().item();assert err<2e-6;print('fixed-route parity',len(bank),'max abs',err)
  if scores is not None:assert torch.equal(scores,ss)
  p=b.language(torch.tensor([[1,2,3],[4,5,6]]),torch.tensor([0,1,2,3,4,5,6]),K=1);q=b.language(torch.tensor([[1,2,10],[4,5,20]]),torch.tensor([0,1,2,3,4,5,6]),K=1);assert torch.equal(p[:,:2],q[:,:2]);print('causality PASS')
for d,expected in [(512,23015887)]:
 m=B2(d);assert m.count==expected;print('inventory',d,m.count,len(m.p),'free',m.count-318*(d+1));del m
