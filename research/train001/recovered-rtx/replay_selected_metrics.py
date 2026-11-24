"""Read-only, pinned TRAIN001 evaluation under current CPU runtime.
Does NOT resume training, select another checkpoint, or replace the locked original.
Arguments: original results ZIP, original TSV directory, original backend file, new report.
"""
import argparse,hashlib,json,math,tempfile,zipfile
from pathlib import Path
import torch
from torch_backend import TorchF,dataset,restore,scores,file_sha,require

def replay(results,data,original_backend):
    with zipfile.ZipFile(results) as z:
        def entry(name):
            matches=[n for n in z.namelist() if n.replace('\\','/')=='rtx_run/'+name]
            require(len(matches)==1,'ARCHIVE_ENTRY_MISSING_OR_DUPLICATE')
            return z.read(matches[0])
        cfg=json.loads(entry('manifest.json'));pin=json.loads(entry('test-selected.json'))
        old=json.loads(entry('test.json'));checkpoint=entry('latest.uno')
    require(hashlib.sha256(checkpoint).hexdigest()==pin['checkpoint'],'LOCKED_CHECKPOINT_MISMATCH')
    require(file_sha(original_backend)==cfg['source'],'ORIGINAL_BACKEND_MISMATCH')
    require({p.name:file_sha(p) for p in data.glob('*.tsv')}==cfg['input'],'INPUT_MANIFEST_MISMATCH')
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'pinned.uno';p.write_bytes(checkpoint);state=restore(p)
    require(state['config']==cfg and state['step']==cfg['steps'] and state['selected']==pin['selected']==old['selected'],'LOCKED_SELECTION_MISMATCH')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    dtype={'double':torch.float64,'float32':torch.float32}[cfg['precision']]
    model=TorchF(data/'initial.tsv',dtype,'cpu');model.load_state_dict(state['best'],strict=True);model.validate();model.eval()
    for p in model.parameters():p.requires_grad_(False)
    before={k:v.detach().clone() for k,v in model.state_dict().items()}
    class Capture:
        def __init__(self,rows):self.rows=iter(rows);self.predictions=[]
        def episode(self,x,mode):
            row=next(self.rows);require(x is row['x'],'CAPTURE_ROW_MISMATCH')
            h,q,bank=model.episode(x,mode)
            top=None
            if bank and mode!='memory_off':
                logits=torch.stack([k for _,k,_ in bank])@q/math.sqrt(q.numel())
                top=bank[int(logits.argmax())][0]
            self.predictions.append({'id':row['id'],'label':row['label'],'target_seq':row['record'],
                'state0':float(h[0]),'prediction':int(float(h[0])>=0),'presence':any(seq==row['record'] for seq,_,_ in bank),
                'top1_seq':top,'bank_size':len(bank)})
            return h,q,bank
    test=dataset(data/'test.tsv',dtype,'cpu');erased=dataset(data/'erased.tsv',dtype,'cpu')
    report={'status':'FROZEN_CPU_REPLAY_DIFFERENT_RUNTIME_NOT_NEW_HOLDOUT','selected':pin['selected'],
        'checkpoint_sha256':pin['checkpoint'],'original_backend_sha256':cfg['source'],
        'original_runtime':cfg['torch'],'current_runtime':str(torch.__version__),
        'metric_schema':2,'inputs':cfg['input'],'metrics':{},'predictions':{},'comparison':{}}
    for name,rows,mode in [('full',test,'full'),('erased',erased,'full'),('memory_off',test,'memory_off'),('zero_values',test,'zero_values')]:
        capture=Capture(rows);r=scores(capture,rows,mode);report['metrics'][name]=r;report['predictions'][name]=capture.predictions
        report['comparison'][name]={'archive_correct':old[name]['correct'],'replay_correct':r['correct'],
            'archive_mse':old[name]['mse'],'replay_mse':r['mse'],
            'max_group_mse_abs_delta':max(abs(g['mse']-old[name]['groups'][k]['mse']/old[name]['groups'][k]['n']) for k,g in r['groups'].items())}
    require(all(torch.equal(v,model.state_dict()[k]) for k,v in before.items()),'WEIGHTS_CHANGED')
    report['weights_unchanged']=True
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('data',type=Path);p.add_argument('original_backend',type=Path);p.add_argument('report',type=Path);a=p.parse_args()
    require(not a.report.exists(),'REFUSE_OVERWRITE_REPORT')
    report=replay(a.results,a.data,a.original_backend)
    with a.report.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({'selected':report['selected'],'comparison':report['comparison'],'weights_unchanged':report['weights_unchanged'],'top1':{k:(v['retrieval_top1_correct'],v['retrieval_top1_n']) for k,v in report['metrics'].items()}},indent=2))
