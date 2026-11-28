"""Regression of the optimized projection against original and KKT conditions."""
import unittest
import torch
from train001_backend import project as reference, decoded_row_guard
from fast_projection import project

class ProjectionTests(unittest.TestCase):
    def test_against_reference_and_caps(self):
        torch.manual_seed(20261126)
        torch.set_num_threads(2)
        for dtype in (torch.float32, torch.float64):
            for cols in (1,16,64,256,512):
                for cap in (.9,1.,2.,8.):
                    for scale in (0.,1e-4,.01,1.,1e10):
                        x=torch.randn(32,cols,dtype=dtype)*scale
                        a,b=x.clone(),x.clone()
                        reference(a,cap)
                        project(b,cap)
                        tol=2e-7 if dtype==torch.float32 else 2e-13
                        torch.testing.assert_close(a,b,atol=tol,rtol=tol)
                        assert (b.double().abs().sum(-1)<=decoded_row_guard(cap,cols)).all()
                        feasible=x.double().abs().sum(-1)<=decoded_row_guard(cap,cols)
                        assert torch.equal(x[feasible],b[feasible])
    def test_independent_kkt(self):
        # Independently construct inputs with a known Euclidean L1 projection.
        # For nonzero output coordinates x=y+lambda*sign(y);
        # zero coordinates are within [-lambda,+lambda].
        torch.manual_seed(31)
        for cols in (64,256,512):
            for cap in (0.9,1.,2.,8.):
                y=torch.rand(24,cols,dtype=torch.float64)
                y[:,::3]=0
                y=y/y.sum(1,keepdim=True)*cap
                signs=torch.where(torch.rand_like(y)>.5,1.,-1.)
                y=y*signs
                lam=torch.rand(24,1,dtype=torch.float64)+.001
                x=torch.where(y!=0,y+lam*signs,(torch.rand_like(y)*2-1)*lam)
                b=x.clone()
                project(b,cap)
                torch.testing.assert_close(b,y,atol=1e-10,rtol=1e-10)
    def test_learning_rate_contract(self):
        from train import lr, config
        import math
        for step in range(1,2001):
            original=2e-4*step/1000 if step<=1000 else 2e-5+9e-5*(1+math.cos(math.pi*(step-1000)/1000))
            self.assertEqual(lr(step,2000,1000),original)
            if step<=64:
                self.assertAlmostEqual(lr(step,2000,16),2e-4*min(1,step/16),places=16)
            if step>1000:
                self.assertEqual(lr(step,2000,16),original)
        self.assertEqual(config(2000,2)["warmup"],16)
        self.assertEqual(config(2000,2,warmup=1000)["warmup"],1000)
    def test_invalid_inputs_fail_closed(self):
        for bad in (float("nan"),float("inf"),-float("inf")):
            row=torch.tensor([[1.,bad]])
            with self.assertRaises(ValueError):
                project(row,1.)
        for cap in (0.,-1.,float("nan"),9.):
            with self.assertRaises(ValueError):
                project(torch.ones(1,64),cap)

if __name__=="__main__":
    unittest.main(verbosity=2)
