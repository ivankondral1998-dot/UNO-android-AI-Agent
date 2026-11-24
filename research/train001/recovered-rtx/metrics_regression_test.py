"""Frozen synthetic forward fixtures, no optimizer, no training. Erratum 13."""
import math
import torch
from torch_backend import scores

class Frozen:
    def episode(self,x,mode):
        # Query favors first entry, while the teacher may label the second.
        bank=[(1,torch.tensor([1.]),torch.tensor([0.])),(2,torch.tensor([-1.]),torch.tensor([0.]))] if x[0,0]>0 else []
        return torch.tensor([0.]),torch.tensor([1.]),bank

def row(id,record,present,state):
    return dict(id=id,record=record,x=torch.tensor([[present,0,present],[0,0,present],[0,0,-1]],dtype=torch.float64),state=state,label=1)
rows=[row('test-a-0',1,1,1.),row('test-a-1',2,1,2.),row('test-b-0',1,0,3.)]
for mode in ('full','zero_values','memory_off'):
    s=scores(Frozen(),rows,mode)
    assert s['metric_schema']==2 and s['n']==3 and s['correct']==2
    assert s['sse']==14 and math.isclose(s['mse'],14/3)
    assert s['groups']['a']['sse']==5 and s['groups']['a']['mse']==2.5
    assert s['groups']['b']['sse']==9 and s['groups']['b']['mse']==9
    assert s['presence_misses']==1 and s['groups']['a']['presence_misses']==0
    if mode=='memory_off':
        assert s['retrieval_top1_n']==0 and s['retrieval_top1_accuracy'] is None
    else:
        assert s['retrieval_top1_n']==3 and s['retrieval_top1_correct']==1 and math.isclose(s['retrieval_top1_accuracy'],1/3)
        assert s['groups']['a']['retrieval_top1_accuracy']==.5
    print('PASS',mode,'SSE_MSE_PRESENCE_RETRIEVAL')
try:
    scores(Frozen(),[])
    raise AssertionError('empty evaluation accepted')
except ValueError as exc:assert str(exc)=='EVALUATION_INPUT'
bad=row('test-a-3',1,1,1.);bad['x'][-1,2]=1
try:
    scores(Frozen(),[bad]);raise AssertionError('terminal write accepted')
except ValueError as exc:assert str(exc)=='TERMINAL_QUERY_REQUIRED'
print('PASS EMPTY_AND_NONQUERY_REJECTED')
