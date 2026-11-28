import importlib.util, pathlib, random, tempfile, json, torch
from train_cuda import Codec, Records, batch, objective, save,restore,validate_weights,identity,ROOT
from tokenizer import encode
from model import B2
spec=importlib.util.spec_from_file_location('old_model',str(ROOT/'model_original.py'));old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
torch.set_num_threads(3);torch.manual_seed(19)
c=Codec();merges=json.loads((ROOT/'tokenizer.json').read_text())['merges'];r=random.Random(1)
for i in range(256):
 s=''.join(r.choice('абвгдеёжзиклмнопрстуфхцчшщэюя .123ABC\n') for _ in range(r.randrange(1,400)));assert c.encode(s)==encode(s.encode(),merges)
print('BPE parity 256/256')
t,m=c.record({'messages':[{'role':'user','text':'Как меня зовут?'},{'role':'assistant','text':'Иван.'}]},'dialogue');assert [x for x,y in zip(t,m) if y]==c.encode('Иван.')+[c.eos];print('assistant-only mask PASS')
a=old.B2(128);b=B2(128);b.load_state_dict(a.state_dict());ids=torch.tensor(c.ids);x=torch.tensor([[256,12,513,257],[256,88,72,257]]);u=a.language(x,ids);v=b.language(x,ids);assert torch.equal(u,v);u.square().mean().backward();v.square().mean().backward();mx=0
for (n,p),(k,q) in zip(a.named_parameters(),b.named_parameters()):
 assert n==k and (p.grad is None)==(q.grad is None)
 if p.grad is not None:mx=max(mx,float((p.grad-q.grad).abs().max()));assert torch.allclose(p.grad,q.grad,atol=1e-8,rtol=1e-5),n
print('original vs packed embedding forward exact, backward max abs',mx)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'ck.uno';save(p,{'x':torch.arange(5)});assert torch.equal(restore(p)['x'],torch.arange(5));x=bytearray(p.read_bytes());x[-1]^=1;p.write_bytes(x)
 try:restore(p);raise AssertionError('accepted corruption')
 except ValueError as e:assert str(e)=='CHECKPOINT_HASH'
print('checkpoint roundtrip + corruption rejection PASS')
