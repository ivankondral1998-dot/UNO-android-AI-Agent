"""Run disposable CUDA probes, choose measured configuration; no weight publication."""
import argparse,json,subprocess,sys,os,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RECEIPT=ROOT/'cuda-probe-fast03.json'
def select(runs):
 baseline=runs[0];eligible=[baseline]
 for r in runs[1:]:
  if r['receipt']['targets']!=baseline['receipt']['targets']:continue
  if any(r['dev'][k]['targets']!=baseline['dev'][k]['targets'] or abs(r['dev'][k]['nll']-baseline['dev'][k]['nll'])>.03 or r['dev'][k]['accuracy']<baseline['dev'][k]['accuracy']-.03 for k in baseline['dev']):continue
  if r['receipt']['update_targets_s']>=1.10*baseline['receipt']['update_targets_s']:eligible.append(r)
 return max(eligible,key=lambda r:r['receipt']['update_targets_s'])
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path(r'D:\UNO\corpus_prepared_v4'));p.add_argument('--batch',type=int,default=16);p.add_argument('--context',type=int,default=64);p.add_argument('--phase',choices=['language','mixed','dialogue'],default='language');p.add_argument('--steps',type=int,default=18);a=p.parse_args()
 base=['--data',str(a.data),'--batch',str(a.batch),'--context',str(a.context),'--phase',a.phase,'--probe-steps',str(a.steps),'--eval-batches','4'];runs=[]
 for name,flags in [('FP32',[]),('FP32_FUSED',['--fused']),('BF16_FUSED',['--fused','--precision','bf16'])]:
  print('BENCHMARK',name,flush=True);dev=None
  command=[sys.executable,str(ROOT/'train_cuda_fast03.py'),'probe',*base,*flags]
  with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',env={**os.environ,'PYTHONUTF8':'1'}) as proc:
   for line in proc.stdout:
    print(line.rstrip(),flush=True)
    if line.startswith('PROBE_DEV '):dev=ast.literal_eval(line[len('PROBE_DEV '):])
   rc=proc.wait()
  if rc!=0 or dev is None:
   print('BENCHMARK_STOP: failed probe; no configuration selected. Do not train until checked.',flush=True);return 1
  receipt=json.loads(RECEIPT.read_text());assert receipt['status']=='CUDA_MECHANISM_ONLY_NOT_QUALITY';runs.append({'name':name,'flags':flags,'dev':dev,'receipt':receipt})
 best=select(runs);tmp=RECEIPT.with_suffix('.tmp');tmp.write_text(json.dumps(best['receipt'],indent=2));os.replace(tmp,RECEIPT)
 result={'selected':best['name'],'runs':runs,'train_args':base+best['flags']};(ROOT/'benchmark-fast03.json').write_text(json.dumps(result,indent=2));print('SELECTED',best['name'],best['receipt']['update_targets_s'],'target tokens/sec',flush=True);print('TRAIN_ARGS',json.dumps(result['train_args']),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
