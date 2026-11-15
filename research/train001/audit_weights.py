"""Read supplied 005B state_dicts with torch weights_only; no training/unrestricted pickle.
Run with compact archive extraction root. Source SHA must match pinned uploaded implementation.
"""
import hashlib,pathlib,sys,torch
root=pathlib.Path(sys.argv[1]);source=root/'UNO_F_LADDER_005B'
assert hashlib.sha256((source/'uno_f_pilot.py').read_bytes()).hexdigest()=='d290ff97eb9c58fd609d97a3c74c2a06c2b5fc0a561a3c9489776e9f8913046a'
sys.path.insert(0,str(source))
from uno_ladder_005 import build
print('torch',torch.__version__,'cuda',torch.cuda.is_available())
for p in sorted((root/'uno_ladder_005b_gpu').glob('*.weights.pt')):
    name=p.name.split('__')[1].split('.')[0];model=build(name)
    weights=torch.load(p,map_location='cpu',weights_only=True);model.load_state_dict(weights,strict=True)
    assert all(torch.isfinite(v).all() for v in weights.values())
    violation=0.0
    if name=='uno_f':
        for w,cap,box in model.m.constrained():
            # Decode FP32 values in Double, so norm sum error does not hide cap excess.
            actual=w.detach().double().abs()
            norm=actual.max().item() if box else actual.sum(-1).max().item()
            violation=max(violation,norm-cap)
    print(p.name,'sha256',hashlib.sha256(p.read_bytes()).hexdigest(),'strict_shapes_finite',sum(v.numel() for v in weights.values()),'decoded_max_cap_excess',violation)
