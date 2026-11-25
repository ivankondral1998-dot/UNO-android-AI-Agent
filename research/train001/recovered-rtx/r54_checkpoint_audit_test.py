"""Exact rational oracle for inward rounding; no optimizer or training."""
import math
import pathlib
import tempfile
import unittest
from fractions import Fraction

import torch
from torch_backend import TorchF, project
from r54_checkpoint_audit import exact_tensor_report


def exact_rows(x):
    return [sum((Fraction(abs(v)) for v in row), Fraction(0))
            for row in x.tolist()]


class DecodedCapsTest(unittest.TestCase):
    def test_original_rounding_counterexample(self):
        x = torch.full((1, 3), 1/3, dtype=torch.float32)
        self.assertGreater(exact_rows(x)[0], 1)
        self.assertEqual(exact_tensor_report('fixture', x, 1, 3, 1., False,
                                            torch.float32)['violating_rows'], 1)
        project(x, 1.)
        self.assertLessEqual(exact_rows(x)[0], 1)

    def test_decimal_point_nine(self):
        x = torch.tensor([[.9]], dtype=torch.float64)
        self.assertGreater(exact_rows(x)[0], Fraction('0.9'))
        project(x, .9)
        self.assertLessEqual(exact_rows(x)[0], Fraction('0.9'))

    def test_random_exact_and_idempotent(self):
        g = torch.Generator().manual_seed(5410)
        for dtype in (torch.float32, torch.float64):
            for cap in (.9, 1., 2., 8.):
                for n in (1, 3, 64, 128, 256):
                    with self.subTest(dtype=dtype, cap=cap, cols=n):
                        x = torch.randn((17, n), dtype=dtype, generator=g)*100
                        project(x, cap)
                        self.assertTrue(all(v <= Fraction(str(cap)) for v in exact_rows(x)))
                        old = x.clone()
                        project(x, cap)
                        self.assertTrue(torch.equal(old, x))

    def test_interior_unchanged_and_zero(self):
        for dtype in (torch.float32, torch.float64):
            x = torch.tensor([[.125, -.25, 0.], [0., 0., 0.]], dtype=dtype)
            old = x.clone()
            project(x, .9)
            self.assertTrue(torch.equal(old, x))

    def test_extreme_finite_rows(self):
        for dtype in (torch.float32, torch.float64):
            m = torch.finfo(dtype).max
            x = torch.tensor([[m, -m, m], [m, 0., -1.]], dtype=dtype)
            project(x, .9)
            self.assertTrue(all(v <= Fraction('0.9') for v in exact_rows(x)))
            self.assertGreater(float(x[1, 0]), .89)

    def test_nonfinite_rejected_before_copy(self):
        for v in (math.inf, -math.inf, math.nan):
            x = torch.tensor([[10., 2.], [v, 0.]])
            old = x.clone()
            with self.assertRaisesRegex(ValueError, 'NONFINITE_PARAMETER'):
                project(x, 1.)
            torch.testing.assert_close(old, x, rtol=0., atol=0., equal_nan=True)

    def test_box_nonfinite_rejected_before_projection(self):
        inventory=[('projection',64,3,8.,False),('us',64,64,1.,False),
                   ('ug',64,64,1.,False),('meta',64,32,8.,False),
                   ('e',64,1,1.,True),('bias',64,1,1.,True),
                   ('wq',128,64,2.,False),('wr',64,128,2.,False),
                   ('wk',128,64,2.,False),('wv',128,64,2.,False)]
        for l in (0,1):
            inventory.extend((f'branch.{l}.0.{s}',r,c,cap,box) for s,r,c,cap,box in
                             [('a',256,64,1.,False),('c',256,64,2.,False),
                              ('b',64,256,.9,False),('ab',256,1,8.,True),('bb',64,1,8.,True)])
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp)/'zero.tsv'
            p.write_text(''.join(f'{n}\t{r}\t{c}\t{cap}\t{str(box).lower()}\t'+
                                 ','.join(['0']*(r*c))+'\n' for n,r,c,cap,box in inventory))
            model=TorchF(p,torch.float32)
            with torch.no_grad():
                model.named_tensors()['e'][0,0]=math.inf
                model.named_tensors()['us'][0,0]=2.
            with self.assertRaisesRegex(ValueError,'NONFINITE_PARAMETER'):
                model.project_()
            self.assertEqual(float(model.named_tensors()['us'][0,0].detach()),2.)
            self.assertTrue(torch.isinf(model.named_tensors()['e'][0,0]))

    def test_wrong_geometry_and_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, 'TENSOR_GEOMETRY'):
            exact_tensor_report('bad', torch.zeros(2, 3), 3, 2, 1., False, torch.float32)
        with self.assertRaisesRegex(ValueError, 'NONFINITE_TENSOR'):
            exact_tensor_report('bad', torch.tensor([[math.nan]]), 1, 1, 1., True, torch.float32)


if __name__ == '__main__':
    torch.set_num_threads(2)
    unittest.main(verbosity=2)
