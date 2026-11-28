import unittest,torch,random,tempfile,time
from pathlib import Path
from model_audit import B2
from fast_model03 import FastB2
from train_cuda_fast03 import Codec,Records,batch,objective,save,restore,validate_weights,validate_optimizer
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  torch.set_num_threads(3);torch.manual_seed(77);cls.ids=torch.tensor(Codec().ids);cls.initial=torch.load(Path(__file__).parent/'latest.uno',weights_only=True,map_location='cpu')['weights']
 def models(self):
  a=B2(512);b=FastB2(512);a.load_state_dict(self.initial);b.load_state_dict(self.initial);b.compact(self.ids);return a,b
 def test_full_updates(self):
  a,b=self.models();oa=torch.optim.Adam(a.parameters(),lr=2e-4,foreach=False);ob=torch.optim.Adam([p for p in b.parameters() if p.requires_grad],lr=2e-4,foreach=False)
  gen=torch.Generator().manual_seed(444);max_l=0;max_g=0;max_w=0
  for j in range(3):
   x=self.ids[torch.randint(len(self.ids),(2,8),generator=gen)];y=torch.randint(len(self.ids),(2,8),generator=gen)
   oa.zero_grad(set_to_none=True);ob.zero_grad(set_to_none=True);za=a.language(x,self.ids);zb=b.language(x,self.ids);max_l=max(max_l,float((za-zb).abs().max().detach()));torch.testing.assert_close(za,zb,atol=2e-6,rtol=2e-5)
   torch.nn.functional.cross_entropy(za.flatten(0,1),y.flatten()).backward();torch.nn.functional.cross_entropy(zb.flatten(0,1),y.flatten()).backward()
   for n,p in b.p.items():
    q=a.p[n]
    if p.grad is None:
     self.assertTrue(q.grad is None or not bool(q.grad.any()),n);continue
    g=q.grad[self.ids] if n in ('E_text','b_text') else q.grad
    max_g=max(max_g,float((g-p.grad).abs().max()));torch.testing.assert_close(g,p.grad,atol=2e-6,rtol=2e-4)
   torch.nn.utils.clip_grad_norm_(a.parameters(),1.);torch.nn.utils.clip_grad_norm_(b.parameters(),1.);oa.step();ob.step();a.project(oa,active_ids=self.ids);b.project_fast(ob)
   for n,w in b.canonical_weights().items():
    v=a.state_dict()[n];max_w=max(max_w,float((w-v).abs().max()));torch.testing.assert_close(w,v,atol=1e-5,rtol=1e-3)
  print('PARITY max logit',max_l,'gradient',max_g,'weight',max_w,flush=True);validate_weights(b);validate_optimizer(b,ob,self.ids)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'test.uno';save(p,{'weights':b.canonical_weights(),'optimizer':ob.state_dict()});c=restore(p);fresh=FastB2(512);fresh.load_state_dict(self.initial);fresh.compact(self.ids);fresh.load_canonical(c['weights']);opt=torch.optim.Adam([p for p in fresh.parameters() if p.requires_grad]);opt.load_state_dict(c['optimizer']);validate_optimizer(fresh,opt,self.ids)
   torch.testing.assert_close(fresh.language(x,self.ids),b.language(x,self.ids),atol=0,rtol=0)
   for n,w in fresh.canonical_weights().items():self.assertTrue(torch.equal(w,c['weights'][n]),n)
 def test_projection_violating_caps(self):
  a,b=self.models()
  for n in ('A_0_0','A_0_1','b_z','E_text','b_text'):
   p=b.p[n];q=a.p[n];p.data[0].fill_(20.);p.grad=torch.zeros_like(p);q.grad=torch.zeros_like(q)
   if n in ('E_text','b_text'):q.data[self.ids[0]].fill_(20.)
   else:q.data[0].fill_(20.)
  a.project(torch.optim.Adam(a.parameters()),active_ids=self.ids);b.project_fast(None)
  for n,w in b.canonical_weights().items():self.assertTrue(torch.equal(w,a.state_dict()[n]),n)
  validate_weights(b)
 def test_causal(self):
  _,b=self.models();x=self.ids[torch.arange(16).reshape(2,8)];y=x.clone();y[:,5:]=self.ids[100];torch.testing.assert_close(b.language(x,self.ids)[:,:5],b.language(y,self.ids)[:,:5],atol=0,rtol=0)
if __name__=='__main__':unittest.main()
