"""Recompute 14–16 from exact historical archive and prior pinned CPU replay.
No training, no evaluation model selection, no writes to input files.
"""
import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib
import json
import math
import zipfile
from r54_measurement import (trajectory_keys, value_loss_floor, group_accuracy,
    recover_rounded_count, wilson95, overwrite_info, paired_counts)


def sha(b):return hashlib.sha256(b).hexdigest()


def read_rows(raw):
    rows={}
    for line in raw.decode().splitlines():
        ident,y,record,value,events=line.split('\t');x=[tuple(map(float,s.split(','))) for s in events.split(';')]
        if ident in rows:raise ValueError('DUPLICATE_ID')
        tr,noise=trajectory_keys(x)
        rows[ident]={'label':int(y),'record':int(record),'value':float(value),'events':x,'trajectory':tr,'noise':noise}
    return rows


def audit(source,prior):
    with zipfile.ZipFile(source) as z,zipfile.ZipFile(prior) as p:
        def one(suffix):
            names=[n for n in z.namelist() if n.endswith(suffix)]
            if len(names)!=1:raise ValueError(('AMBIGUOUS_SOURCE',suffix,names))
            return z.read(names[0])
        replay=json.loads(p.read('EVIDENCE/PRIOR_08/PRIOR_07/replay.json'))
        cfg=json.loads(one('09_TRAIN001/RESULTS/rtx_run/manifest.json'))
        pin=json.loads(one('09_TRAIN001/RESULTS/rtx_run/test-selected.json'))
        if replay['inputs']!=cfg['input'] or replay['selected']!=pin['selected'] or replay['checkpoint_sha256']!=pin['checkpoint'] or not replay['weights_unchanged']:raise ValueError('REPLAY_PROVENANCE')
        rows={}
        for split in ('train','validation','test','erased','initial'):
            raw=one('/UNO_TRAIN001_RTX_READY_20261115/'+split+'.tsv')
            if sha(raw)!=cfg['input'][split+'.tsv']:raise ValueError('DATA_HASH_MISMATCH')
            if split!='initial':rows[split]=read_rows(raw)
        summaries={s:{'n':len(rr),'lengths':dict(Counter(len(r['events']) for r in rr.values())),
                      'trajectory_count':len({r['trajectory'] for r in rr.values()}),'noise_families':len({r['noise'] for r in rr.values()}),
                      'exact_real_value_loss_floor_mean':sum(value_loss_floor(r['value']) for r in rr.values())/len(rr)} for s,rr in rows.items()}
        overlap={a+'__'+b:{k:len({r[k] for r in rows[a].values()}&{r[k] for r in rows[b].values()}) for k in ('trajectory','noise')} for a,b in combinations(('train','validation','test'),2)}
        training=json.loads(one('09_TRAIN001/RESULTS/rtx_run/training.json'))
        val_lengths=set(summaries['validation']['lengths']);train_lengths=set(summaries['train']['lengths']);test_lengths=set(summaries['test']['lengths'])
        stats={};predictions={}
        for mode,pp in replay['predictions'].items():
            rr=rows['erased' if mode=='erased' else 'test'];got={}
            for pred in pp:
                ident=pred['id'];r=rr[ident]
                if ident in got or pred['label']!=r['label'] or pred['target_seq']!=r['record']:raise ValueError('PREDICTION_ALIGNMENT')
                got[ident]=int(pred['presence'] and pred['prediction']==r['label'])
            if got.keys()!=rr.keys():raise ValueError('PREDICTION_COVERAGE')
            stats[mode]=group_accuracy((rr[i]['noise'],ok) for i,ok in got.items());predictions[mode]=got
            if stats[mode]['correct']!=replay['metrics'][mode]['correct']:raise ValueError('METRIC_MISMATCH')
        overwrite=[]
        for ident,r in rows['test'].items():
            if '-r4_overwrite-' not in ident:continue
            info=overwrite_info(r['events'])
            if info['last']!=r['label']:raise ValueError('TEACHER_MISMATCH')
            overwrite.append((ident,predictions['full'][ident],int(info['first']==r['label']),info['hard']))
        archived007=json.loads(one('11_S4_WM_007/UNO_S4_WM_007/CPU_VERIFIED/RESULTS_SUMMARY.json'))
        corrected007=[]
        for row in archived007['runs']:
            corrected007.append({'rung':row['rung'],'mode':row['mode'],'trainable_count':row['parameters_updated'],
                'changed_count':None,'history':[{'step':h['step'],'total_loss':h['train_bce'],'answer_bce':h['train_bce'] if row['mode']=='no_memory' else None,'route_ce':None} for h in row['history']],
                'eval':{L:wilson95(recover_rounded_count(v['acc'],v['n']),v['n']) for L,v in row['eval'].items()}})
        corrected005={};identical=0
        for name in z.namelist():
            if '/uno_ladder_005b_gpu/' not in name or not name.endswith('.json') or name.count('.')!=1:continue
            b=json.loads(z.read(name));a=json.loads(z.read(name.replace('uno_ladder_005b_gpu/','uno_ladder_005_gpu/')))
            same=all(a[k]==b[k] for k in ('final','erased_control'));identical+=same
            corrected005[Path(name).stem]={'same_005_005b':same,**{k:{L:wilson95(recover_rounded_count(v['acc'],v['n']),v['n']) for L,v in b[k].items()} for k in ('final','erased_control')}}
        return {'status':'ARCHIVED_EVIDENCE_REANALYSIS_NOT_NEW_TRAINING_OR_HOLDOUT','source_sha256':sha(source.read_bytes()),'prior_sha256':sha(prior.read_bytes()),
         '14':{'selected':training['selected'],'splits':summaries,'overlap':overlap,'unseen_in_training':sorted(test_lengths-train_lengths),
               'also_used_in_validation':sorted((test_lengths-train_lengths)&val_lengths),'order_value_floor':value_loss_floor(1.),'grouped_prior_replay':stats},
         '15':{'runs':corrected007,'attribution':'joint memory, goal, trainable parameters and route loss intervention; individual effects not identified'},
         '16':{'005_005B_identical_cells':identical,'cells':corrected005,'train001_full_vs_first_write':paired_counts(overwrite),
               'perfect_2048':wilson95(2048,2048),'first_write_theoretical_accuracy':5/6,
               'unit':'one generated episode conditional on a fixed model/seed; not independent training repeats'}}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('prior',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    result=audit(a.source,a.prior)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({'14':result['14'],'15_runs':len(result['15']['runs']),'16':{k:v for k,v in result['16'].items() if k!='cells'}},indent=2))
