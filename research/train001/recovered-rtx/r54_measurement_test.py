"""Host checks; only synthetic/frozen forward and explicit parameter mutation, no training."""
import math,sys,tempfile,unittest
from pathlib import Path
import torch
from r54_measurement import *
from torch_backend import dataset,scores

class Tests(unittest.TestCase):
    def test_floor(self):
        self.assertAlmostEqual(value_loss_floor(1),.00025880299904035303)
        self.assertEqual(value_loss_floor(-1),value_loss_floor(1))
        self.assertEqual(value_loss_floor(.5),0)
        for cap in (0.,.1,2.,3.):
            for v in (-1.,-.8,0.,.8,1.):
                for x in (-cap,0.,cap):
                    self.assertLessEqual(value_loss_floor(v,cap),.2*(math.tanh(x)-v)**2+1e-15)
        with self.assertRaises(ValueError):value_loss_floor(1,-1)
    def test_identity(self):
        a=[(0.,-0.,0.),(.2,0.,1.),(0.,0.,-1.)];b=[(-0.,0.,-0.),(-.2,0.,1.),(0.,0.,-1.)]
        ka,kb=trajectory_keys(a),trajectory_keys(b)
        self.assertNotEqual(ka[0],kb[0]);self.assertEqual(ka[1],kb[1])
        with self.assertRaises(ValueError):trajectory_keys([(float('nan'),0,1)])
    def test_group(self):
        r=group_accuracy([('a',1),('a',1),('b',0)])
        self.assertEqual(r['accuracy'],2/3);self.assertEqual(r['equal_family_accuracy'],.5)
        self.assertFalse(r['independence_established'])
        with self.assertRaises(ValueError):group_accuracy([])
    def test_wilson(self):
        for n in (1,2,320,512,2048):
            for c in (0,n//2,n):
                r=wilson95(c,n);lo,hi=r['wilson95'];self.assertLess(lo,hi)
                self.assertLessEqual(lo,c/n+1e-15);self.assertGreaterEqual(hi,c/n-1e-15)
                self.assertEqual(recover_rounded_count(round(c/n,4),n),c)
        with self.assertRaises(ValueError):recover_rounded_count(.5,100000)
        with self.assertRaises(ValueError):wilson95(2,1)
    def test_overwrite(self):
        self.assertEqual(overwrite_info([(1,0,1),(-1,0,1),(0,0,-1)]),dict(first=1,last=0,overwritten=True,hard=True))
        self.assertFalse(overwrite_info([(1,0,1),(1,0,1),(0,0,-1)])['hard'])
        with self.assertRaises(ValueError):overwrite_info([(1,1,1),(0,0,-1)])
    def test_pair(self):
        r=paired_counts([('a',1,0,True),('b',0,1,False),('c',1,1,False),('d',0,0,True)])
        self.assertEqual(r['all']['paired_accuracy_delta_left_minus_right'],0)
        self.assertEqual(r['hard']['paired_accuracy_delta_left_minus_right'],.5)
        with self.assertRaises(ValueError):paired_counts([('a',0,1,True),('a',1,0,True)])
        self.assertIsNone(paired_counts([('a',1,1,False)])['hard']['paired_accuracy_delta_left_minus_right'])
    def test_loss_and_delta(self):
        self.assertAlmostEqual(loss_components(.2,.8,.25)['total_loss'],.4)
        m=torch.nn.Linear(2,1);m.bias.requires_grad_(False);before={k:v.detach().clone() for k,v in m.named_parameters()}
        self.assertEqual(parameter_delta(before,m)['changed_count_vs_snapshot'],0)
        with torch.no_grad():m.weight[0,0]+=1
        d=parameter_delta(before,m);self.assertEqual(d['trainable_count'],2);self.assertEqual(d['changed_count_vs_snapshot'],1);self.assertAlmostEqual(d['delta_l2'],1,places=6)
    def test_trainer_lineage(self):
        class Frozen:
            def episode(self,x,mode):return torch.tensor([0.]),torch.tensor([1.]),[(1,torch.tensor([1.]),torch.tensor([0.]))]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.tsv';p.write_text('test-r1-0\t1\t1\t1\t1,0,1;0,0,-1\ntest-r1-1\t0\t1\t-1\t-1,0,1;0,0,-1\n')
            rows=dataset(p,torch.float32,'cpu');self.assertNotEqual(rows[0]['trajectory_sha256'],rows[1]['trajectory_sha256']);self.assertEqual(rows[0]['noise_family_sha256'],rows[1]['noise_family_sha256'])
            r=scores(Frozen(),rows);self.assertEqual(r['lineage']['noise_families'],1);self.assertEqual(r['lineage']['accuracy'],.5)
            del rows[1]['noise_family_sha256']
            with self.assertRaisesRegex(ValueError,'MIXED_LINEAGE_METADATA'):scores(Frozen(),rows)
    def test_objective_components_and_gradients(self):
        import torch.nn.functional as F
        logits=torch.tensor([.3,-.5],requires_grad=True);route=torch.tensor([[.1,.9],[-.2,.3]],requires_grad=True)
        y=torch.tensor([1.,0.]);target=torch.tensor([1,0]);trace={'route_logits':route,'route_target':target}
        a,b,total=answer_objective(logits,y,trace,.25)
        old=F.binary_cross_entropy_with_logits(logits,y)+.25*F.cross_entropy(route,target)
        self.assertTrue(torch.equal(total,old));self.assertTrue(all(torch.equal(x,y) for x,y in zip(torch.autograd.grad(total,(logits,route),retain_graph=True),torch.autograd.grad(old,(logits,route)))))
        zero_bce,_,zero_total=answer_objective(logits,y,trace,0.)
        self.assertIs(zero_bce,zero_total)
        self.assertIsNone(answer_objective(logits,y,None,.25)[1])
        with self.assertRaises(ValueError):answer_objective(logits,y,trace,-1.)
    def test_split_lineage(self):
        def row(length,tr,noise):return {'x':[0]*length,'trajectory_sha256':tr,'noise_family_sha256':noise}
        r=split_lineage({'train':[row(12,'a','n1')],'validation':[row(48,'b','n2')],'test':[row(48,'c','n2'),row(96,'d','n3')]})
        self.assertEqual(r['unseen_in_training_lengths'],[48,96]);self.assertEqual(r['also_used_in_validation_lengths'],[48])
        self.assertEqual(r['overlap']['validation__test']['noise_family_sha256'],1)
        self.assertEqual(r['overlap']['validation__test']['trajectory_sha256'],0)
    def test_real_generator_pair(self):
        from uno_ladder_005 import make_batch
        import uno_s4_wm_007_r54 as study
        class Oracle(torch.nn.Module):
            def __init__(self,last):super().__init__();self.last=last
            def sequence(self,x):
                info=[overwrite_info(e) for e in x.tolist()];return x.new_tensor([1. if t['last' if self.last else 'first'] else -1. for t in info]),None
        a,b=Oracle(True),Oracle(False)
        r=paired_overwrite_evaluate(a,b,make_batch,length=24,seed=777,n=2048,chunk=128)['comparison']
        self.assertEqual(r['all']['both_wrong']+r['all']['right_only'],0)
        self.assertGreater(r['hard']['n'],0);self.assertEqual(r['hard']['left_only'],r['hard']['n'])
        self.assertTrue(a.training and b.training)
        stats=study.score(Oracle(True),'r4_overwrite',24,777,2048,'cpu',chunk=128)
        self.assertEqual(stats['correct'],2048);self.assertEqual(stats['overwrite_changed_sign']['n'],r['hard']['n']);self.assertEqual(stats['overwrite_changed_sign']['accuracy'],1.)
        print('actual generator paired hard',r['hard']['n'],'of 2048; first-write correct',r['all']['both_correct'])

if __name__=='__main__':unittest.main(verbosity=2)
