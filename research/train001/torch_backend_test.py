"""Two synthetic diagnostic updates only; never a task-quality training run."""
import pathlib,sys,tempfile,torch
from torch_backend import TorchF,update,checkpoint,restore,output_lock
device=sys.argv[2] if len(sys.argv)>2 else 'cpu'
if device=='cuda':
    if not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE; no CPU fallback')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    print('CUDA_DEVICE',torch.cuda.get_device_name(0),'runtime',torch.version.cuda)
if not __debug__:raise RuntimeError('Tests require Python without -O')
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(tempfile.mkdtemp(prefix='uno-port-test-'))
rules={f[0]:f[1:3] for f in (line.split('\t') for line in (p/'update1.tsv').read_text().splitlines())}
initial=[];expected_grad={}
for line in (p/'weights.tsv').read_text().splitlines():
    n,r,c,x,g=line.split('\t');cap,box=rules[n];initial.append('\t'.join((n,r,c,cap,box,x)));expected_grad[n]=torch.tensor([float(v) for v in g.split(',')],dtype=torch.float64)
(out/'initial.tsv').write_text('\n'.join(initial))
raw=[]
for line in (p/'events.tsv').read_text().splitlines():raw.append([float(v) for v in line.split('\t')[-1].split(',')])
record,state,value,loss=(p/'target.tsv').read_text().split('\t')
torch.set_num_threads(2)
for dtype,tol in ((torch.float64,2e-13),(torch.float32,2e-6)):
    row={'x':torch.tensor(raw,dtype=dtype,device=device),'record':int(record),'state':float(state),'value':float(value)}
    model=TorchF(out/'initial.tsv',dtype,device);objective=model.loss(row);objective.backward()
    assert objective.device.type==device and all(p.device.type==device for p in model.parameters())
    for line in (p/'controls.tsv').read_text().splitlines():
        mode,want=line.split('\t');h,_,_=model.episode(row['x'],mode);assert abs(h[0].item()-float(want))<tol
    assert abs(objective.item()-float(loss))<tol
    for name,param in model.named_tensors().items():
        actual=torch.zeros_like(param).flatten() if param.grad is None else param.grad.flatten()
        error=(actual.cpu().double()-expected_grad[name]).abs().max().item();assert error<tol,(name,error)
    missing=dict(row,record=999999)
    try:model.loss(missing);raise AssertionError('FABRICATED_MISSING_TARGET')
    except ValueError as exc:assert 'RETRIEVAL_MISS' in str(exc)
    opt=torch.optim.Adam(model.parameters(),lr=2e-4)
    for step in (1,2):
        update(model,opt,[row],step,2000)
        assert all(p.grad is None or p.grad.device.type==device for p in model.parameters())
        assert all(s['exp_avg'].device.type==device and s['exp_avg_sq'].device.type==device for s in opt.state.values())
        for line in (p/f'update{step}.tsv').read_text().splitlines():
            name,cap,box,grad,weights,m,v=line.split('\t')
            param=model.named_tensors()[name];actual=(param.detach().flatten().cpu().double())
            expected=torch.tensor([float(f) for f in weights.split(',')],dtype=torch.float64)
            assert (actual-expected).abs().max()<tol,(dtype,name,step)
        if step==1:
            checkpoint(out/'resume.uno',{'weights':model.state_dict(),'optimizer':opt.state_dict(),'cursor':1})
    saved=restore(out/'resume.uno');resumed=TorchF(out/'initial.tsv',dtype,device);resumed.load_state_dict(saved['weights'])
    resumed_opt=torch.optim.Adam(resumed.parameters(),lr=2e-4);resumed_opt.load_state_dict(saved['optimizer']);update(resumed,resumed_opt,[row],2,2000)
    assert all(torch.equal(v,resumed.state_dict()[n]) for n,v in model.state_dict().items())
    for left,right in zip(opt.state.values(),resumed_opt.state.values()):
        for key in left:assert torch.equal(left[key],right[key]),key
    print(dtype,'PORT_ALL_GRADIENTS_TWO_UPDATES_KOTLIN_PARITY_AND_'+device.upper()+'_EXACT_RESUME_PASS')
    body=(out/'resume.uno').read_bytes();(out/'broken.uno').write_bytes(body[:-5])
    try:restore(out/'broken.uno');raise AssertionError('CORRUPTION_ACCEPTED')
    except ValueError:pass
with output_lock(out/'lock-test'):
    try:
        with output_lock(out/'lock-test'):raise AssertionError('CONCURRENT_WRITER_ACCEPTED')
    except RuntimeError:pass
print('CHECKPOINT_CORRUPTION_AND_CONCURRENT_WRITER_REJECTED')
if device=='cuda':
    torch.cuda.synchronize();assert torch.cuda.max_memory_allocated()>0
    print('CUDA_EXECUTION_CONFIRMED peak_allocated_bytes',torch.cuda.max_memory_allocated())
else:print('CUDA_NOT_TESTED')
