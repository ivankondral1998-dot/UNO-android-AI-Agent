"""Budgeted paired study orchestration; reuses TRAIN001 update/checkpoint/lock, never trains on test."""
import argparse,pathlib,json,hashlib,time,os,sys,gzip,types,tempfile
import torch
from engine import *
from torch_backend import update
from data import load,erase,FAMILIES
from study_stats import hierarchical

SEEDS=[260015,260016,260017]
def source_identity():
    here=pathlib.Path(__file__).resolve().parent
    paths=[here/name for name in ('study.py','engine.py','organizer.py','data.py','study_stats.py')]+[here.parent/'train001/torch_backend.py']
    return hashlib.sha256(canonical({p.name:file_sha(p) for p in paths}).encode()).hexdigest()
def load_plan(root):
    plan=json.loads((root/'study.json').read_text());require(plan['stage']=='TRAIN-002' and plan['source']==source_identity(),'STUDY_SOURCE_MISMATCH')
    require(1<=plan['steps']<=1000 and 1<=plan['batch']<=16 and 1<=len(plan['seeds'])<=3 and len(set(plan['seeds']))==len(plan['seeds']) and bool(plan['arms']) and len(set(plan['arms']))==len(plan['arms']) and set(plan['arms']).issubset(ARMS),'STUDY_BUDGET_OR_ARM')
    for name,digest in plan['files'].items():require(file_sha(root/name)==digest,'STUDY_DATA_MISMATCH '+name)
    return plan

def hardware(device):
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    if device=='cuda':
        require(torch.cuda.is_available(),'CUDA_UNAVAILABLE; no CPU fallback')
        require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') in (':4096:8',':16:8'),'CUBLAS_WORKSPACE_CONFIG_REQUIRED')
        require(torch.cuda.device_count()==1 and os.environ.get('CUDA_VISIBLE_DEVICES') in (None,'0'),'SINGLE_PHYSICAL_GPU0_REQUIRED')
    driver=None
    if device=='cuda':
        import subprocess
        driver=subprocess.check_output(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],text=True,timeout=5).splitlines()[0].strip()
    return {'driver':driver,'cudnn':torch.backends.cudnn.version() if device=='cuda' else None,'compute_capability':list(torch.cuda.get_device_capability(0)) if device=='cuda' else None,'torch':str(torch.__version__),'cuda':torch.version.cuda,'device':device,'gpu':torch.cuda.get_device_name(0) if device=='cuda' else None,'tf32':False,'deterministic':True,'cublas':os.environ.get('CUBLAS_WORKSPACE_CONFIG')}
def guard(device,max_temp=78,max_mib=6500):
    if device=='cuda':
        import subprocess
        fields=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True,timeout=5).splitlines()[0].split(',')
        require(float(fields[0])<max_temp and float(fields[1])<max_mib,'GPU_RESOURCE_STOP')

def run(root,output,arm,seed,device='cuda',resume=False,max_seconds=1800,receipt=None):
    plan=load_plan(root);require(arm in plan['arms'] and seed in plan['seeds'] and 0<max_seconds<=1800,'UNDECLARED_RUN')
    hw=hardware(device)
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    if device=='cuda':
        require(receipt is not None,'CUDA_CHECK_RECEIPT_REQUIRED');check=json.loads(receipt.read_text())
        require(check['source']==source_identity() and check['hardware']==hw and check.get('plan_sha')==file_sha(root/'study.json') and check['status']=='CUDA_MECHANISM_PASS_NOT_QUALITY','CUDA_CHECK_MISMATCH')
    require(device=='cuda' or plan.get('diagnostic',False),'CPU_MAIN_TRAINING_FORBIDDEN')
    cfg={'plan_sha':file_sha(root/'study.json'),'source':source_identity(),'arm':arm,'seed':seed,'steps':plan['steps'],'batch':plan['batch'],'hardware':hw,'dtype':'float32','projection':'FP64 threshold then cast FP32; cap tolerance2e-6','loss':'state1 retrieval.3 value.2; typed payload by arm; state-only without S4/GRU'}
    data={s:load(root/'data'/f'{s}.jsonl',torch.float32,device) for s in ('train','validation')}
    model=make_model(root/f'initial-{seed}.tsv',arm,seed,torch.float32,device);opt=torch.optim.Adam(model.parameters(),lr=2e-4)
    run_path=output/f'{arm}__{seed}'
    with output_lock(run_path):
        checkpoint_dir=run_path
        if resume:
            require(json.loads((run_path/'config.json').read_text())==cfg,'RUN_CONFIG_MISMATCH')
            saved=restore(run_path/'latest.uno');require(saved['config']==cfg,'CHECKPOINT_CONFIG_MISMATCH')
            model.load_state_dict(saved['weights'],strict=True);model.project_() if arm=='gru' else model.validate()
            opt.load_state_dict(saved['optimizer']);step=saved['step'];require(0<=step<=cfg['steps'] and saved['cursor']==step*cfg['batch'],'CURSOR_MISMATCH')
            torch.set_rng_state(saved['cpu_rng'])
            if device=='cuda':torch.cuda.set_rng_state_all(saved['cuda_rng'])
            history=saved['history'];best=saved['best'];best_loss=saved['best_loss'];selected=saved['selected'];elapsed=saved['elapsed'];peak=saved['peak_cuda_allocated']
        else:
            require(not run_path.exists(),'OUTPUT_EXISTS')
            checkpoint_dir=pathlib.Path(tempfile.mkdtemp(prefix=f'.{arm}__{seed}-initializing-',dir=run_path.parent))
            atomic(checkpoint_dir/'config.json',canonical(cfg).encode());step=0;history=[];elapsed=0.;peak=0
            best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};best_loss=metrics(model,data['validation'])[0]['mse'];selected=0
        def save():
            nonlocal peak
            if device=='cuda':peak=max(peak,torch.cuda.max_memory_allocated())
            checkpoint(checkpoint_dir/'latest.uno',{'config':cfg,'weights':model.state_dict(),'optimizer':opt.state_dict(),'step':step,'cursor':step*cfg['batch'],'cpu_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all() if device=='cuda' else [],'history':history,'best':best,'best_loss':best_loss,'selected':selected,'elapsed':elapsed,'peak_cuda_allocated':peak})
        def finish():
            allocated=sum(p.numel() for p in model.parameters());trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
            resources={'allocated_parameters':allocated,'trainable_parameters':trainable,'forward_backward_update_seconds':elapsed,'peak_cuda_allocated':peak,'parameters_with_optimizer_state':sum(p.numel() for p in opt.state),'optimizer_state_bytes':sum(t.numel()*t.element_size() for state in opt.state.values() for t in state.values() if isinstance(t,torch.Tensor)),'compute_note':'equal data/update/batch/LR/clip, not equal FLOPs; F constrained, GRU unconstrained; timing excludes validation/checkpoint'}
            atomic(run_path/'finished.json',canonical({'config':cfg,'selected':selected,'validation_mse':best_loss,'resources':resources,'status':'FINISHED_TEST_UNOPENED'}).encode())
        if resume and step==cfg['steps']:
            if not (run_path/'finished.json').exists():finish()
            print('ALREADY_FINISHED checkpoint unchanged',flush=True);return
        save()
        if checkpoint_dir!=run_path:
            require(not run_path.exists(),'OUTPUT_EXISTS')
            os.rename(checkpoint_dir,run_path)
            checkpoint_dir=run_path
        start=time.monotonic()
        while step<cfg['steps']:
            if time.monotonic()-start>=max_seconds:print('TIME_BOUNDARY_STOP',step,flush=True);return
            guard(device);t0=time.monotonic()
            batch=[data['train'][(step*cfg['batch']+j)%len(data['train'])] for j in range(cfg['batch'])]
            loss,norm=update(model,opt,batch,step+1,cfg['steps']);step+=1
            if device=='cuda':torch.cuda.synchronize()
            elapsed+=time.monotonic()-t0
            row={'step':step,'loss':loss,'gradient_norm':norm}
            if step%100==0 or step==cfg['steps']:
                validation,_=metrics(model,data['validation']);row['validation']=validation
                if validation['mse']<best_loss:best_loss=validation['mse'];selected=step;best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            history.append(row);save();print(canonical(row),flush=True)
        finish()

def snapshot(path,expected=None):
    require(1<=path.stat().st_size<=64*1024*1024+128,'CHECKPOINT_SIZE')
    blob=path.read_bytes();digest=hashlib.sha256(blob).hexdigest()
    if expected is not None:require(digest==expected,'PINNED_CHECKPOINT_CHANGED')
    class Envelope:
        def stat(self):return types.SimpleNamespace(st_size=len(blob))
        def read_bytes(self):return blob
    return restore(Envelope()),digest

def validate_run(saved,cfg,root,plan,arm,seed):
    require(saved['config']==cfg and cfg['arm']==arm and cfg['seed']==seed,'CHECKPOINT_ATTRIBUTION_MISMATCH')
    require(cfg['plan_sha']==file_sha(root/'study.json') and cfg['source']==source_identity() and cfg['steps']==plan['steps'] and cfg['batch']==plan['batch'],'CHECKPOINT_PLAN_MISMATCH')
    require(cfg['hardware']['device']=='cuda' or plan.get('diagnostic',False),'NON_CUDA_STUDY')
    require(cfg['hardware']['torch'].split('+')[0]==str(torch.__version__).split('+')[0],'EVALUATION_TORCH_VERSION')
    require(saved['step']==plan['steps'] and saved['cursor']==plan['steps']*plan['batch'] and 0<=saved['selected']<=saved['step'],'INCOMPLETE_STUDY')

def pin_selections(root,output,plan):
    pins={}
    for arm in plan['arms']:
        for seed in plan['seeds']:
            p=output/f'{arm}__{seed}';saved,digest=snapshot(p/'latest.uno');cfg=json.loads((p/'config.json').read_text())
            validate_run(saved,cfg,root,plan,arm,seed)
            pins[f'{arm}__{seed}']={'checkpoint':digest,'selected':saved['selected']}
    return pins

def evaluate(root,output):
    plan=load_plan(root)
    with output_lock(output/'locked-test'):
        # All predeclared arms/seeds must finish before any new test labels enter evaluation.
        pins=pin_selections(root,output,plan);encoded=canonical({'plan':file_sha(root/'study.json'),'selections':pins})
        marker=output/'test-selected.json'
        if marker.exists():require(marker.read_text()==encoded,'LOCKED_SELECTION_CHANGED')
        else:atomic(marker,encoded.encode())
        final=output/'test-report.json'
        if final.exists():
            cached=json.loads(final.read_text());require(cached['selections']==pins and cached['plan']==plan,'CACHED_TEST_REPORT_MISMATCH');print(final.read_text());return
        torch.set_num_threads(2);test=load(root/'data/test.jsonl',torch.float32,'cpu');erased=[erase(r) for r in test];reports={};predictions={}
        for arm in plan['arms']:
            reports[arm]={};predictions[arm]={}
            for seed in plan['seeds']:
                key=f'{arm}__{seed}';saved,_=snapshot(output/key/'latest.uno',pins[key]['checkpoint'])
                validate_run(saved,json.loads((output/key/'config.json').read_text()),root,plan,arm,seed)
                model=make_model(root/f'initial-{seed}.tsv',arm,seed,torch.float32,'cpu');model.load_state_dict(saved['best']);model.project_() if arm=='gru' else model.validate()
                modes=['primary','erased']+([] if arm in ('gru','f_no_memory','random_keys','permuted_values') else ['memory_off','zero_values','random_keys','permute_values','clock_shuffle','reverse_pairs'])
                per={};predictions[arm][seed]=None
                for mode in modes:
                    summary,preds=metrics(model,erased if mode=='erased' else test,None if mode in ('primary','erased') else mode,details=True)
                    if mode=='erased':require(summary['correct']*2==summary['n'],'ERASED_PAIR_LEAK_OR_NONDETERMINISM')
                    if mode=='primary':predictions[arm][seed]=preds
                    per[mode]=summary
                    atomic(output/key/f'{mode}-predictions.jsonl.gz',gzip.compress(('\n'.join(canonical(v) for v in preds)+'\n').encode(),mtime=0))
                per['resources']={'allocated_parameters':sum(p.numel() for p in model.parameters()),'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),'optimizer_state_parameters':sum(v['exp_avg'].numel() for v in saved['optimizer']['state'].values()),'forward_backward_update_seconds':saved['elapsed'],'peak_cuda_allocated':saved['peak_cuda_allocated'],'limit':'same update/data budget, not equal FLOPs; timing excludes validation/checkpoint'}
                reports[arm][seed]=per;print('EVALUATED',arm,seed,per['primary']['correct'],flush=True)
        comparisons={}
        for a,b in [('chrono_typed','baseline_typed'),('baseline_typed','baseline_legacy'),('chrono_legacy','baseline_legacy'),('baseline_typed','f_no_memory'),('baseline_typed','gru'),('baseline_typed','frozen_write'),('baseline_typed','random_keys'),('baseline_typed','permuted_values')]:
            if a not in predictions or b not in predictions:continue
            comparisons[a+':'+b]={'overall':hierarchical([(predictions[a][s],predictions[b][s]) for s in plan['seeds']]),'by_group':{group:hierarchical([([r for r in predictions[a][s] if r['group']==group],[r for r in predictions[b][s] if r['group']==group]) for s in plan['seeds']]) for group in sorted({r['group'] for r in test})},'by_family':{family:hierarchical([([r for r in predictions[a][s] if r['group'].startswith(family+'-')],[r for r in predictions[b][s] if r['group'].startswith(family+'-')]) for s in plan['seeds']]) for family in FAMILIES}}
        atomic(final,canonical({'plan':plan,'selections':pins,'runs':reports,'paired':comparisons,'evaluation_device':'cpu','evaluation_torch':str(torch.__version__),'supervision_limit':'typed versus legacy jointly changes fields and queried-only/all-write coverage; chronology comparisons hold payload protocol fixed','limit':'three seeds; paired test clusters; no pooled independent seed*episode CI; historic TRAIN001 test not used here'}).encode());print('LOCKED_TEST_REPORT',final)

def suite(root,output,receipt,max_seconds=1800):
    plan=load_plan(root);started=time.monotonic()
    with output_lock(output/'active-trainer'):
        for arm in plan['arms']:
            for seed in plan['seeds']:
                remaining=max_seconds-(time.monotonic()-started)
                if remaining<=0:print('SUITE_TIME_STOP; rerun Suite to resume');return
                path=output/f'{arm}__{seed}'
                run(root,output,arm,seed,'cuda',path.exists(),remaining,receipt)
                saved=restore(path/'latest.uno')
                if saved['step']<plan['steps']:print('SUITE_PAUSED',arm,seed);return
    print('ALL_PREDECLARED_RUNS_FINISHED; test remains unopened')

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['train','resume','evaluate','plan','suite']);p.add_argument('root',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--arm',choices=list(ARMS));p.add_argument('--seed',type=int);p.add_argument('--device',choices=['cuda','cpu'],default='cuda');p.add_argument('--max-seconds',type=float,default=1800);p.add_argument('--receipt',type=pathlib.Path);a=p.parse_args()
    if a.command=='plan':print(canonical(load_plan(a.root)))
    elif a.command=='evaluate':
        with output_lock(a.output/'active-trainer'):evaluate(a.root,a.output)
    elif a.command=='suite':suite(a.root,a.output,a.receipt,a.max_seconds)
    else:
        with output_lock(a.output/'active-trainer'):run(a.root,a.output,a.arm,a.seed,a.device,a.command=='resume',a.max_seconds,a.receipt)
if __name__=='__main__':main()
