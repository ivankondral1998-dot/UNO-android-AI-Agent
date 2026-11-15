import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from organizer import Chronology

class Headers(unittest.TestCase):
    def test_causal_links_versions_and_rollback_on_invalid_append(self):
        s=Chronology();a=s.append(2,-1,'k1','v1');b=s.append(5,1,'k2','v2');c=s.append(9,-1,'k3','v3')
        self.assertEqual((a.ordinal,a.next,b.previous,b.next,c.previous),(1,5,2,9,5))
        self.assertEqual((a.version,c.version,c.previous_version),(1,2,2))
        self.assertEqual([x.sequence for x in s.history(-1)],[2,9])
        self.assertEqual(s.neighbor(5,'previous').sequence,2)
        self.assertEqual(s.neighbor(5,'next').sequence,9)
        self.assertEqual(s.neighbor(None,'last').sequence,9)
        self.assertIsNone(s.neighbor(2,'previous'))
        self.assertIsNone(s.neighbor(999,'next'))
        before=repr(s.records)
        with self.assertRaises(ValueError):s.append(5,0,'bad','bad')
        self.assertEqual(repr(s.records),before)


import tempfile,torch
from engine import OrganizedF,make_model
from torch_backend import TorchF,update
from data import generate,load,pair,erase,oracle
INITIAL=None
DEVICE='cpu'

class DatasetContract(unittest.TestCase):
    def test_balanced_disjoint_paired_causal_oracles(self):
        root=pathlib.Path(tempfile.mkdtemp())/'data'
        m=generate(root,seed=42,train_pairs=1,val_pairs=1,test_pairs=1)
        self.assertTrue(all(not any(v.values()) for v in m['overlaps'].values()))
        for split in ('train','validation','test'):
            rows=load(root/(split+'.jsonl'),torch.float64,'cpu')
            self.assertTrue(all(v['n']==2*v['positive'] for v in m['balanced'][split].values()))
            by_pair={}
            for r in rows:by_pair.setdefault(r['pair'],[]).append(r)
            for a,b in by_pair.values():self.assertTrue(torch.equal(erase(a)['x'],erase(b)['x']))
            for row in rows:
                erased=erase(row);self.assertEqual(erased['label'],row['label'])
                self.assertEqual(erased['record'],row['record'])
                writes=[i+1 for i,f in enumerate(row['x']) if f[2]==1]
                self.assertIn(row['record'],writes);self.assertLess(row['record'],len(row['x']))

class NeuralContract(unittest.TestCase):
    def row(self,family='r2_two',length=12):
        r=pair('diagnostic',family,length,0,91)[0];r['x']=torch.tensor(r['x'],dtype=torch.float64,device=DEVICE);return r
    def test_baseline_forward_and_all_gradients_equal_train001(self):
        for length in (12,96):
            row=self.row(length=length)
            old=TorchF(INITIAL,torch.float64,DEVICE);new=OrganizedF(INITIAL,torch.float64,DEVICE,payload='legacy')
            a=old.loss(row);b=new.loss(row)
            self.assertTrue(torch.equal(a,b));a.backward();b.backward()
            for x,y in zip(old.parameters(),new.parameters()):
                if x.grad is None:self.assertIsNone(y.grad)
                else:self.assertTrue(torch.equal(x.grad,y.grad))
    def test_chronology_gradients_gold_independence_and_storage_permutation(self):
        row=self.row();model=OrganizedF(INITIAL,torch.float64,DEVICE,.5,payload='typed')
        with torch.no_grad():
            for p in model.parameters():p.mul_(.9)
        g=model.replay(row['x']);loss=model.loss(row);loss.backward()
        ids=[r.sequence for r in g['store'].records]
        with self.assertRaisesRegex(ValueError,'RETRIEVAL_MISS'):model.loss(dict(row,record=9999))
        self.assertEqual(ids,[r.sequence for r in model.replay(row['x'])['store'].records])
        reversed_graph=model.replay(row['x'],'reverse_pairs')
        self.assertTrue(torch.allclose(g['state'],reversed_graph['state'],atol=1e-13,rtol=1e-13))
        for name in ('wk','wv','wq','wr'):
            param=model.named_tensors()[name];flat=param.grad.flatten();ix=int(flat.abs().argmax());analytic=float(flat[ix]);epsilon=1e-5
            with torch.no_grad():
                original=float(param.flatten()[ix]);param.flatten()[ix]=original+epsilon;a=float(model.loss(row));param.flatten()[ix]=original-epsilon;b=float(model.loss(row));param.flatten()[ix]=original
            self.assertLess(abs((a-b)/(2*epsilon)-analytic),1e-9+abs(analytic)*1e-4)
            self.assertGreater(abs(analytic),1e-15)
    def test_fp32_chronology_matches_double_objective_and_gradients(self):
        row=self.row('r9_previous_version',96)
        reference=OrganizedF(INITIAL,torch.float64,'cpu',.5)
        candidate=OrganizedF(INITIAL,torch.float32,DEVICE,.5)
        a=reference.loss(dict(row,x=row['x'].cpu().double()));b=candidate.loss(dict(row,x=row['x'].to(device=DEVICE,dtype=torch.float32)))
        a.backward();b.backward();self.assertLess(abs(float(a.detach())-float(b.detach())),2e-6)
        for x,y in zip(reference.parameters(),candidate.parameters()):
            if x.grad is None:self.assertIsNone(y.grad)
            else:self.assertLess(float((x.grad-y.grad.cpu().double()).abs().max()),2e-6)
        self.assertEqual(b.device.type,DEVICE)
    def test_future_query_cannot_change_written_payload_and_typed_targets(self):
        model=OrganizedF(INITIAL,torch.float64,DEVICE)
        x=torch.zeros(12,3,dtype=torch.float64,device=DEVICE);x[0]=x.new_tensor([.5,1.,1.]);x[2]=x.new_tensor([.25,-1.,1.]);y=x.clone();x[-1]=x.new_tensor([0.,-1.,-1.]);y[-1]=y.new_tensor([0.,0.,-2.])
        a=model.replay(x)['store'].records;b=model.replay(y)['store'].records
        self.assertTrue(torch.equal(a[-1].value,b[-1].value))
        self.assertTrue(torch.equal(x[2,:2],y[2,:2]))
        self.assertAlmostEqual(.2*(.25+1.)**2/4,.078125)
    def test_freeze_random_keys_and_no_memory_are_genuine_controls(self):
        row=self.row()
        for arm in ('frozen_write','random_keys','f_no_memory','gru'):
            dtype=torch.float32 if DEVICE=='cuda' and arm=='gru' else torch.float64
            current=dict(row,x=row['x'].to(dtype=dtype))
            model=make_model(INITIAL,arm,2,dtype,DEVICE);opt=torch.optim.Adam(model.parameters(),lr=2e-4)
            before={n:p.clone() for n,p in model.named_tensors().items()} if arm!='gru' else {}
            update(model,opt,[current],1,2000)
            if arm=='frozen_write':
                for n in ('wk','wv'):self.assertTrue(torch.equal(before[n],model.named_tensors()[n]))
            if arm=='random_keys':self.assertIsNone(model.named_tensors()['wk'].grad)
            if arm=='f_no_memory':
                for n in ('wk','wv','wq','wr'):self.assertIsNone(model.named_tensors()[n].grad)
                self.assertEqual(model.episode(row['x'])[2],[])

class PairedStatistics(unittest.TestCase):
    def test_shared_pairs_and_shared_test_seeds_are_not_pooled(self):
        from study_stats import paired,hierarchical
        a=[{'id':str(i),'pair':str(i//2),'label':i%2,'correct':True} for i in range(4)]
        b=[dict(r,correct=False) for r in a]
        self.assertEqual(paired(a,b,draws=32)['clusters'],2)
        h=hierarchical([(a,b),(a,b),(a,b)],draws=32)
        self.assertEqual(h['test_clusters'],2);self.assertEqual(h['hierarchical_paired_ci95'],[1.,1.])

class StudyIdentity(unittest.TestCase):
    def test_pinned_bytes_cannot_change(self):
        import study,hashlib
        from engine import checkpoint
        path=pathlib.Path(tempfile.mkdtemp())/'c.uno';checkpoint(path,{'step':1})
        expected=hashlib.sha256(path.read_bytes()).hexdigest();self.assertEqual(study.snapshot(path,expected)[0]['step'],1)
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'PINNED_CHECKPOINT_CHANGED'):study.snapshot(path,expected)
    def test_interrupted_initialization_never_publishes_partial_run(self):
        import study
        from prepare import prepare
        from unittest.mock import patch
        root=pathlib.Path(tempfile.mkdtemp());prepared=root/'study';prepare(prepared,INITIAL.parent,diagnostic=True)
        with patch('study.metrics',side_effect=RuntimeError('INITIAL_VALIDATION_INTERRUPTED')):
            with self.assertRaisesRegex(RuntimeError,'INITIAL_VALIDATION_INTERRUPTED'):study.run(prepared,root/'runs','chrono_typed',260015,'cpu')
        self.assertFalse((root/'runs/chrono_typed__260015').exists())
    def test_incomplete_study_never_parses_test_labels(self):
        import study
        from prepare import prepare
        from unittest.mock import patch
        root=pathlib.Path(tempfile.mkdtemp());prepared=root/'study';prepare(prepared,INITIAL.parent,diagnostic=True)
        with patch('study.load',side_effect=AssertionError('TEST_LABELS_OPENED')) as parsed:
            with self.assertRaises(FileNotFoundError):study.evaluate(prepared,root/'missing-runs')
            parsed.assert_not_called()

    def test_mislabelled_arm_checkpoint_is_rejected_before_test(self):
        import study,json
        from engine import checkpoint,canonical,atomic,file_sha
        root=pathlib.Path(tempfile.mkdtemp());out=root/'output';root.joinpath('study.json').write_text('{}')
        arm='chrono_typed';seed=260015;run=out/f'{arm}__{seed}';run.mkdir(parents=True)
        cfg={'plan_sha':file_sha(root/'study.json'),'source':study.source_identity(),'arm':'baseline_typed','seed':seed,'steps':1,'batch':1}
        atomic(run/'config.json',canonical(cfg).encode());checkpoint(run/'latest.uno',{'config':cfg,'step':1,'cursor':1,'selected':1})
        with self.assertRaises(ValueError):study.pin_selections(root,out,{'arms':[arm],'seeds':[seed],'steps':1,'batch':1})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--initial',type=pathlib.Path,required=True);p.add_argument('--device',choices=['cpu','cuda'],default='cpu');a=p.parse_args();INITIAL=a.initial;DEVICE=a.device
    if not __debug__:raise RuntimeError('Tests require Python without -O')
    torch.set_num_threads(2)
    if DEVICE=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE; no CPU fallback')
        torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False
    unittest.main(argv=[sys.argv[0]])
