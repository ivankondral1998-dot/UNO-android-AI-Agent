import json,random,tempfile,unittest
from pathlib import Path
import torch
from train_cuda_audit02 import Codec,Records,batch,objective,evaluate,selection_score
from model_audit import B2
class Check(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.c=Codec();self.p=Path(self.tmp.name)
  (self.p/'d.jsonl').write_text(json.dumps({'messages':[{'role':'user','text':'Сколько будет два плюс два?'},{'role':'assistant','text':'Четыре.'}]},ensure_ascii=False)+'\n',encoding='utf8')
  (self.p/'l.jsonl').write_text(json.dumps({'text':'Русский язык. Хороший день.'},ensure_ascii=False)+'\n',encoding='utf8')
  self.d=Records(self.p/'d.jsonl','dialogue'); self.l=Records(self.p/'l.jsonl','language')
 def tearDown(self):self.tmp.cleanup()
 def test_anchor_full_context_and_single_target(self):
  t,m,targets=self.d.encoded(0,self.c);i=next(j for j in targets if not m[j-1]);x,y,mask=self.d.row(random.Random(1),self.c,128,True);self.assertEqual(sum(mask),1);self.assertEqual(y[i-1],t[i]);self.assertEqual(x[:i],t[:i]);self.assertTrue(mask[i-1])
 def test_short_context_no_future_label_leak(self):
  for L in (2,8,16,64):
   for k in range(10):
    x,y,m=self.d.row(random.Random(k),self.c,L,True);self.assertEqual(sum(m),1);j=m.index(True);self.assertEqual(y[j],self.c.encode('Четыре.')[0]);self.assertEqual(x[j+1] if j+1<L else y[j],y[j])
 def test_eval_and_gradient(self):
  from types import SimpleNamespace
  torch.set_num_threads(2);torch.manual_seed(123);model=B2(128);ids=torch.tensor(self.c.ids);remap=torch.full((32768,),-1,dtype=torch.long);remap[ids]=torch.arange(len(ids));a=SimpleNamespace(eval_batches=1,context=8,batch=2,device='cpu')
  o=objective(model,batch(self.d,random.Random(2),self.c,8,2,'cpu',remap),ids)[0];o.backward();self.assertTrue(torch.isfinite(o));self.assertTrue(any(x.grad is not None for x in model.parameters()));r=evaluate(model,{'language':self.l,'dialogue':self.d},self.c,ids,remap,a);self.assertEqual(r['dialogue_start']['targets'],2);self.assertAlmostEqual(selection_score(r),(r['dialogue']['nll']+r['language']['nll'])/2)
if __name__=='__main__':unittest.main()
