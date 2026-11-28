"""Independent FIX03 regression: mathematical parity and malformed-state refusal."""
import copy
import tempfile
from pathlib import Path
import unittest
import torch
from torch.nn.functional import cross_entropy
from model import LanguageF
from analytic_backward import loss_and_grad
from train import Trainer,lr,config
from train001_backend import checkpoint,restore

class AuditTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)

    def test_analytic_all_gradients_and_initial_state(self):
        torch.manual_seed(811)
        for dtype in (torch.float32,torch.float64):
            for width,length in ((64,1),(64,16),(128,7),(512,16)):
                with self.subTest(dtype=dtype,width=width,length=length):
                    m=LanguageF(17,width).to(dtype)
                    f=copy.deepcopy(m)
                    tokens=torch.randint(17,(length,))
                    targets=torch.randint(17,(length,))
                    h=torch.randn(width,dtype=dtype).tanh().requires_grad_()
                    logits,state=m(tokens,h)
                    loss=cross_entropy(logits,targets)
                    loss.backward()
                    l,s,g=loss_and_grad(f,tokens,targets,h.detach())
                    tol=2e-7 if dtype==torch.float32 else 1e-12
                    torch.testing.assert_close(loss,l,rtol=0,atol=tol)
                    torch.testing.assert_close(state,s,rtol=0,atol=tol)
                    torch.testing.assert_close(h.grad,g,rtol=1e-4,atol=tol)
                    for (name,p),(name2,q) in zip(m.named_parameters(),f.named_parameters()):
                        self.assertEqual(name,name2)
                        torch.testing.assert_close(p.grad,q.grad,rtol=1e-4 if dtype==torch.float32 else 1e-10,atol=tol)

    def test_analytic_nonfinite_rejected(self):
        m=LanguageF(4,64)
        with torch.no_grad(): m.e[0]=float("nan")
        with self.assertRaisesRegex(ValueError,"nonfinite forward"):
            loss_and_grad(m,torch.tensor([0,1]),torch.tensor([1,2]),torch.zeros(64))

    def test_analytic_resume_exact(self):
        data=[torch.tensor([0,2,3,2,3,1]),torch.tensor([0,3,2,1])]
        cfg={"width":64,"steps":3,"window":2,"seed":11,"warmup":16,"gradient_backend":"analytic"}
        a=Trainer(data,4,cfg)
        a.update()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"latest.uno"
            a.save(p)
            b=Trainer(data,4,cfg)
            b.load(p)
            self.assertEqual(a.update(),b.update())
            for x,y in zip(a.model.parameters(),b.model.parameters()):
                self.assertTrue(torch.equal(x,y))
            self.assertTrue(torch.equal(a.state,b.state))

    def test_valid_checksum_does_not_admit_wrong_schema(self):
        data=[torch.tensor([0,2,3,1])]
        cfg={"width":64,"steps":2,"window":2,"seed":11,"warmup":16,"gradient_backend":"analytic"}
        a=Trainer(data,4,cfg);a.update()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"valid.uno";q=Path(d)/"malformed.uno"
            a.save(p)
            raw=restore(p)
            mutations=[
                lambda x:x["model"].__setitem__("E",x["model"]["E"].double()),
                lambda x:x["optimizer"]["state"].clear(),
                lambda x:x["optimizer"]["param_groups"][0].__setitem__("eps",0.1),
                lambda x:x["optimizer"]["state"][0].__setitem__("step",torch.tensor(1.5)),
                lambda x:x["optimizer"]["state"][0].__setitem__("exp_avg",x["optimizer"]["state"][0]["exp_avg"].double()),
                lambda x:x.__setitem__("targets",float(x["targets"])),
                lambda x:x.__setitem__("rng",torch.zeros(1,dtype=torch.uint8)),
                lambda x:x["model"].__setitem__("b_text",torch.full((4,),float("nan"))),
            ]
            for i,mutate in enumerate(mutations):
                with self.subTest(mutation=i):
                    bad=copy.deepcopy(raw);mutate(bad);checkpoint(q,bad)
                    with self.assertRaises(ValueError):
                        Trainer(data,4,cfg).load(q)
            Trainer(data,4,cfg).load(p)

    def test_tokenizer_rejects_invalid_mapping(self):
        from corpus_check import validate_tokenizer
        ids=list(range(514))
        known={str(i):bytes([i]).hex() for i in range(256)}
        tok={"active_ids":ids,"bos":256,"eos":257,"merges":[],"tokens_hex":known}
        with self.assertRaises(ValueError):
            validate_tokenizer(tok)
        tok["active_ids"][-1]=0
        with self.assertRaises(ValueError):
            validate_tokenizer(tok)

    def test_projection_does_not_publish_nonfinite_chunks(self):
        m=LanguageF(514,512)
        with torch.no_grad():m.A[-1,-1,-1,-1]=float("nan")
        with self.assertRaises(ValueError):
            m.project_()
        m=LanguageF(514,512)
        with torch.no_grad():m.b_text[0]=float("inf")
        with self.assertRaises(ValueError):
            m.project_()

if __name__=="__main__":
    unittest.main(verbosity=2)
