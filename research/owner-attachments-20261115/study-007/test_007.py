import hashlib, math, tempfile, unittest
from pathlib import Path
import torch
from torch.nn import functional as F
from uno_s4_wm_007 import (SOURCE_SHA, SEED_SHA, sha, slot_codes, bank_codes,
    SeparatedS4, exact_oracle, score, atomic_save)
from uno_ladder_005 import make_batch

ROOT=Path(__file__).parent
class MemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(17);torch.set_num_threads(2)
    def model(self,rung='r2_two',mode='s4'):
        return SeparatedS4(rung,mode,ROOT/'seed_F_006_research_only.pt')
    def test_sha_original_and_pretrained(self):
        self.assertEqual(sha(ROOT/'uno_f_pilot.py'),SOURCE_SHA)
        self.assertEqual(sha(ROOT/'seed_F_006_research_only.pt'),SEED_SHA)
    def test_slot_keys_distinct_and_orthogonal(self):
        for k in (2,3):
            bank=bank_codes(k)
            dot=bank@bank.T
            self.assertTrue(torch.allclose(dot-torch.diag(dot.diag()),torch.zeros_like(dot)))
    def test_oracle_independent_of_labels(self):
        for rung in ('r2_two','r3_three','r4_overwrite'):
            gen=torch.Generator().manual_seed(235)
            x,y=make_batch(512,24,rung,gen)
            self.assertTrue(torch.equal(exact_oracle(x,rung)>0,y.bool()),rung)
    def test_erased_evidence_destroys_oracle(self):
        for rung in ('r2_two','r3_three','r4_overwrite'):
            gen=torch.Generator().manual_seed(62)
            x,y=make_batch(1024,24,rung,gen,erase=True)
            acc=((exact_oracle(x,rung)>0)==y.bool()).float().mean().item()
            self.assertGreater(acc,.45)
            self.assertLess(acc,.55)
    def test_writes_are_persistent_and_overwritten(self):
        m=self.model('r4_overwrite')
        gen=torch.Generator().manual_seed(40)
        x,y=make_batch(128,24,'r4_overwrite',gen)
        v,seen,s=m.scan(x)
        idx=torch.zeros(128,dtype=torch.long)
        for j,c in enumerate(slot_codes('r4_overwrite')):
            idx=torch.where(x[:,-1,1]==c,j,idx)
        self.assertTrue(seen.all())
        self.assertTrue(torch.equal((v.gather(1,idx[:,None]).squeeze()>0),y.bool()))
    def test_f_processes_noise_without_memory_overwrite(self):
        m=self.model('r2_two')
        x,_=make_batch(8,12,'r2_two',torch.Generator().manual_seed(80))
        x2=x.clone();x2[:, -2, 0]+=3.0  # penultimate is noise event, not WRITE
        self.assertTrue((x[:,-2,2]==0).all())
        a,seen_a,s=m.scan(x);b,seen_b,s2=m.scan(x2)
        self.assertTrue(torch.equal(a,b))
        self.assertGreater(float((s-s2).abs().max()),1e-8)
    def test_s4_memory_path_has_nonzero_gradients(self):
        m=self.model('r2_two')
        x,y=make_batch(16,12,'r2_two',torch.Generator().manual_seed(44))
        logit,_=m.sequence(x)
        F.binary_cross_entropy_with_logits(logit,y).backward()
        self.assertIsNotNone(m.core.Wq.weight.grad)
        self.assertIsNotNone(m.core.Wr.weight.grad)
        self.assertGreater(float(m.core.Wq.weight.grad.abs().sum()),0.)
        self.assertGreater(float(m.core.Wr.weight.grad.abs().sum()),0.)
        self.assertIsNone(m.core.Us.weight.grad)
    def test_no_memory_path_disables_query_weights(self):
        m=self.model('r2_two','no_memory')
        x,y=make_batch(16,12,'r2_two',torch.Generator().manual_seed(32))
        loss=F.binary_cross_entropy_with_logits(m.sequence(x)[0],y)
        loss.backward()
        self.assertIsNone(m.core.Wq.weight.grad)
        self.assertIsNone(m.core.Wr.weight.grad)
    def test_readout_and_s4_constrained(self):
        m=self.model()
        with torch.no_grad():
            m.core.Wq.weight.fill_(2.)
            m.core.Wr.weight.fill_(2.)
            m.readout.weight.fill_(2.)
        m.after_step()
        self.assertLessEqual(float(m.core.Wq.weight.detach().abs().sum(-1).max()),2.00001)
        self.assertLessEqual(float(m.core.Wr.weight.detach().abs().sum(-1).max()),2.00001)
        self.assertLessEqual(float(m.readout.weight.detach().abs().sum(-1).max()),8.00001)
    def test_saved_weights_reproduce_output(self):
        m=self.model();x,_=make_batch(8,12,'r2_two',torch.Generator().manual_seed(94))
        with torch.no_grad():a=m.sequence(x)[0]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pt';atomic_save(m.state_dict(),p)
            n=self.model();n.load_state_dict(torch.load(p,weights_only=True))
            with torch.no_grad():b=n.sequence(x)[0]
            self.assertTrue(torch.equal(a,b))
    def test_keys_values_within_astra_range(self):
        m=self.model('r3_three','s4_goal')
        self.assertLessEqual(float(m.key_bank.abs().max()),1.)
        x,_=make_batch(16,24,'r3_three',torch.Generator().manual_seed(29))
        values,seen,_=m.scan(x)
        semantic_values=values[:,:,None]*m.value_axis[None,None,:]
        self.assertTrue(seen.all())
        self.assertLessEqual(float(semantic_values.abs().max()),1.)
    def test_query_goal_only_contains_address(self):
        m=self.model('r3_three','s4_goal')
        x,_=make_batch(32,24,'r3_three',torch.Generator().manual_seed(30))
        goal=m.encode_goal(x[:,-1])
        self.assertTrue(torch.equal(goal[:,:3].sum(1),torch.ones(32)))
        self.assertTrue((goal[:,3:]==0).all())
    def test_goal_encoder_and_query_receive_gradients(self):
        m=self.model('r3_three','s4_goal')
        x,y=make_batch(32,24,'r3_three',torch.Generator().manual_seed(31))
        logits,trace=m.sequence(x)
        loss=F.binary_cross_entropy_with_logits(logits,y)+.25*F.cross_entropy(trace['route_logits'],trace['route_target'])
        loss.backward()
        for p in (m.core.Ug.weight,m.core.Wq.weight,m.core.Wr.weight):
            self.assertIsNotNone(p.grad)
            self.assertGreater(float(p.grad.detach().abs().sum()),0.)

    def test_no_knowledge_from_query_value(self):
        m=self.model()
        x,_=make_batch(16,12,'r2_two',torch.Generator().manual_seed(39))
        self.assertTrue((x[:,-1,0]==0).all())
        with torch.no_grad():
            a=m.sequence(x)[0]
            copy=x.clone();copy[:,-1,0]=0
            b=m.sequence(copy)[0]
            self.assertTrue(torch.equal(a,b))

if __name__=='__main__':unittest.main(verbosity=2)
