"""Exercise existing Kotlin UnoFReference with pinned TRAIN001 host fixtures.
No product ABI, device admission, optimizer, dataset scoring, or weight export.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import pathlib
import subprocess
import tempfile
import zipfile

import torch
from torch_backend import TorchF
from r54_checkpoint_audit import audit_selected, exact_tensor_report

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE_SHA = '43bcbf5206401f4d1755bccfd639d225409176ebb3da7673f6ce2c90ab30f5bc'


def checked(condition, reason):
    if not condition:
        raise AssertionError(reason)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def serialize(weights, path):
    # Private, temporary host fixture. Never consumed by Android production code.
    path.write_text(''.join(f'{n}\t{p.shape[0]}\t{p.shape[1]}\t'+
                            ','.join(repr(float(v)) for v in p.detach().flatten())+'\n'
                            for n,p in weights.items()))


def run_jar(jar, *args):
    r = subprocess.run(['java','-cp',str(jar),'org.unovyra.uno.core.R54CoreParityKt',
                        *map(str,args)], capture_output=True, text=True, timeout=120)
    checked(r.returncode == 0, r.stderr)
    return r.stdout


def fixture(z, folder, tmp):
    def read(n):
        names = [p for p in z.namelist() if p.endswith('/'+folder+'/'+n+'.tsv')]
        checked(len(names)==1, 'fixture member')
        return z.read(names[0]).decode().splitlines()
    rules = {f[0]:f[1:3] for f in (l.split('\t') for l in read('update1'))}
    initial = tmp/'layout.tsv'
    initial.write_text('\n'.join('\t'.join((n,r,c,*rules[n],x)) for n,r,c,x,g
                                 in (l.split('\t') for l in read('weights'))))
    model = TorchF(initial, torch.float64, 'cpu')
    model.project_() # only synthetic fixtures, never the real checkpoint
    w = model.named_tensors()
    for name,rows,cols,cap,box in model.rules:
        checked(exact_tensor_report(name,w[name],rows,cols,cap,box,torch.float64)['violating_rows']==0,
                'fixture decoded cap')
    weights, events = tmp/'weights.tsv', tmp/'events.csv'
    serialize(w, weights)
    raw = [l.split('\t')[-1] for l in read('events')]
    events.write_text('\n'.join(raw))
    x = torch.tensor([[float(v) for v in l.split(',')] for l in raw],dtype=torch.float64)
    return model, weights, events, x


def compare(model, x, raw):
    states={}; banks={}
    def vec(s): return torch.tensor([float(v) for v in s.split(',')],dtype=torch.float64)
    for line in raw.splitlines():
        t,mode,*f=line.split('\t')
        if t=='STATE': states[mode]=vec(f[0])
        elif t=='BANK': banks.setdefault(mode,[]).append((int(f[0]),vec(f[1]),vec(f[2])))
        else: raise AssertionError('unexpected Kotlin output')
    maxerr=0.; coords=0
    with torch.no_grad():
        for mode in ('full','memory_off','zero_values'):
            h,_,bank=model.episode(x,mode)
            pairs=[(h,states[mode])]
            actual=banks.get(mode,[])
            checked([a[0] for a in actual]==[b[0] for b in bank], 'causal IDs')
            for (_,k,v),(_,ak,av) in zip(bank,actual): pairs.extend(((k,ak),(v,av)))
            for a,b in pairs:
                checked(a.shape==b.shape,'shape mismatch')
                error=float((a-b).abs().max());coords+=a.numel();maxerr=max(maxerr,error)
                checked(error<2e-13,'Kotlin reference parity '+mode+' '+str(error))
    return coords,maxerr


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixture_archive',type=pathlib.Path)
    p.add_argument('core_sources',type=pathlib.Path)
    p.add_argument('checkpoint',type=pathlib.Path)
    p.add_argument('initial',type=pathlib.Path)
    p.add_argument('--sha256',required=True)
    a=p.parse_args()
    torch.set_num_threads(2)
    checked(sha(a.fixture_archive.read_bytes())==FIXTURE_SHA,'fixture archive digest')
    with tempfile.TemporaryDirectory(prefix='uno-r54-core-') as folder:
        tmp=pathlib.Path(folder);jar=tmp/'probe.jar'
        sources=sorted(a.core_sources.glob('*.kt'))
        checked(any(s.name=='UnoFReference.kt' for s in sources),'reference source missing')
        subprocess.run(['kotlinc',*map(str,sources),str(HERE/'R54CoreParity.kt'),
                        '-include-runtime','-d',str(jar)],check=True,timeout=240)
        with zipfile.ZipFile(a.fixture_archive) as z:
            for name in ('parity','parity96','parity-singleton'):
                model,weights,events,x=fixture(z,name,tmp)
                coords,error=compare(model,x,run_jar(jar,'fixture',weights,events))
                print('PASS',name,'all compared state/key/value coordinates',coords,'max_delta',error,flush=True)
        audit=audit_selected(a.checkpoint,a.initial,a.sha256)
        checked(audit['status']=='REJECTED_DECODED_CAP','expected original checkpoint violation')
        blob=a.checkpoint.read_bytes()
        checked(sha(blob)==a.sha256,'checkpoint changed')
        state=torch.load(io.BytesIO(blob.split(b'\n',2)[2]),map_location='cpu',weights_only=True)
        layout=TorchF(a.initial,torch.float32,'cpu')
        weights=tmp/'original-selected.tsv'
        serialize({n:state['best'][f'slots.{i}'] for i,n in enumerate(layout.names)},weights)
        result=run_jar(jar,'reject',weights).strip()
        checked(result.startswith('CORE_REJECTED_DECODED_NORM\t'),'actual F constructor did not reject')
        print(result,flush=True)
        checked(sha(a.checkpoint.read_bytes())==a.sha256,'checkpoint changed after probe')
        print('CORE_PARITY_PASS_NOT_RUNTIME_ADMISSION')


if __name__=='__main__':
    main()
