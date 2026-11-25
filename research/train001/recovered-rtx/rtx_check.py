"""Explicit user-run CUDA qualification. Never treats CPU checks as CUDA evidence.
Runs Kotlin fixture parity at lengths12/96, singleton/empty-read controls, CPU crash test,
then verifies CUDA kernel timing/placement. No long or quality training and no test set access.
"""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
import torch
if not __debug__:raise RuntimeError('Tests require Python without -O')
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
if not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE: install CUDA wheel/driver; no CPU fallback')
if torch.cuda.device_count()!=1:raise RuntimeError('Single GPU check required')
if os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in (':4096:8',':16:8'):raise RuntimeError('Set CUBLAS_WORKSPACE_CONFIG before Python startup')
if a.output.exists():raise RuntimeError('RECEIPT_EXISTS')
root=pathlib.Path(__file__).resolve().parent
checks=['parity','parity96','parity-singleton']
logs=[]
for fixture in checks:
    for device in ('cpu','cuda'):
        command=[sys.executable,str(root/'torch_backend_test.py'),str(root/fixture),device]
        r=subprocess.run(command,capture_output=True,text=True,timeout=600)
        logs.append({'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(r.stdout,flush=True)
        if r.returncode:print(r.stderr);raise RuntimeError('PARITY_OR_RESUME_TEST_FAILED')
for device in ('cpu','cuda'):
    r=subprocess.run([sys.executable,str(root/'torch_crash_test.py'),str(root/'parity'),device],capture_output=True,text=True,timeout=600)
    logs.append({'test':device+' process crash','exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(r.stdout)
    if r.returncode:print(r.stderr);raise RuntimeError('CRASH_TEST_FAILED '+device)
# CUDA events time actual device work; no wall-clock-only timing or CPU fallback.
x=torch.randn(256,256,device='cuda');begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
begin.record();y=x@x;end.record();torch.cuda.synchronize()
if y.device.type!='cuda' or begin.elapsed_time(end)<=0:raise RuntimeError('CUDA_EXECUTION_NOT_CONFIRMED')
receipt={'status':'CUDA_MECHANISM_CHECK_PASS_NOT_QUALITY','torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'cublas':os.environ['CUBLAS_WORKSPACE_CONFIG'],'kernel_ms':begin.elapsed_time(end),'peak_allocated':torch.cuda.max_memory_allocated(),'backend_sha256':hashlib.sha256((root/'torch_backend.py').read_bytes()).hexdigest(),'measurement_sha256':hashlib.sha256((root/'r54_measurement.py').read_bytes()).hexdigest(),'checks':logs,'limitations':['bounded mechanism checks; not learning quality or 8GB full-run VRAM certification','CPU and CUDA process-kill tests use only short synthetic fixtures; full-run GPU-driver/power-loss recovery not certified','no S6, AMP, FP16 derivative equivalence, Android or 007']}
a.output.write_text(json.dumps(receipt,indent=2));print('CUDA_CHECK_RECEIPT',a.output)
