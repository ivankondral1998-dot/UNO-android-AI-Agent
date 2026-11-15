"""Explicit owner's local CUDA qualification. Never creates a successful receipt on CPU."""
import argparse,pathlib,subprocess,sys,json,time,os
import torch
from engine import canonical,atomic,require
from study import hardware,source_identity,load_plan,guard

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=pathlib.Path);p.add_argument('--receipt',type=pathlib.Path,required=True);a=p.parse_args()
    if not __debug__:raise RuntimeError('Tests require unoptimized Python')
    plan=load_plan(a.root);hw=hardware('cuda');guard('cuda');require(not a.receipt.exists(),'CHECK_RECEIPT_EXISTS')
    initial=a.root/f'initial-{plan["seeds"][0]}.tsv';here=pathlib.Path(__file__).resolve().parent;logs=[]
    for device in ('cpu','cuda'):
        for script,args in [('test_stage002.py',['--initial',str(initial),'--device',device]),('crash_test.py',[str(initial),device])]:
            guard('cuda');result=subprocess.run([sys.executable,str(here/script),*args],capture_output=True,text=True,timeout=600)
            logs.append({'test':script,'device':device,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr});print(result.stdout);print(result.stderr,flush=True)
            if result.returncode:
                atomic(a.receipt.with_suffix('.failed.json'),canonical({'source':source_identity(),'hardware':hw,'tests':logs}).encode());raise RuntimeError('CUDA_QUALIFICATION_FAILED')
    # Actual CUDA work and allocations, in addition to F/gradient/optimizer tests on device.
    x=torch.randn(256,256,device='cuda');begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
    begin.record();y=x@x;end.record();torch.cuda.synchronize();require(y.device.type=='cuda' and begin.elapsed_time(end)>0,'CUDA_EXECUTION_NOT_CONFIRMED')
    receipt={'status':'CUDA_MECHANISM_PASS_NOT_QUALITY','source':source_identity(),'hardware':hw,'plan':str(a.root/'study.json'),'plan_sha':__import__('hashlib').sha256((a.root/'study.json').read_bytes()).hexdigest(),'kernel_ms':begin.elapsed_time(end),'peak_allocated':torch.cuda.max_memory_allocated(),'tests':logs,'limit':'short diagnostics only, not new task quality; no new locked test evaluation'}
    atomic(a.receipt,canonical(receipt).encode());print('CUDA_CHECK_PASS_NOT_QUALITY',a.receipt)
