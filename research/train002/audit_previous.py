"""Read-only scientific replay of supplied TRAIN001. Never updates weights or opens a new test."""
import argparse,pathlib,json,hashlib,gzip,collections,math
import torch
from engine import OrganizedF,restore,require,file_sha,canonical,atomic
from study_stats import paired,wilson
sys_path=pathlib.Path(__file__).resolve().parents[1]/'train001'
from torch_backend import dataset,scores

def enrich(rows):
    for r in rows:
        fields=r['id'].split('-');r['group']='-'.join(fields[1:-1]) if fields[0]=='test' else 'unknown'
        # Historic generator reused the same length/index seed across different rungs.
        r['pair']='-'.join(fields[-2:]) if fields[0]=='test' else r['id']
    return rows

def export_row(model,row,mode):
    with torch.no_grad():g=model.replay(row['x'],mode)
    reads=g['reads'];last=reads[-1];catalogue=last['ids'];prob=last['prob'].cpu().tolist()
    chosen=catalogue[max(range(len(prob)),key=prob.__getitem__)] if prob else None
    records=[]
    for r in g['store'].records:
        records.append({'id':r.sequence,'ordinal':r.ordinal,'slot':r.slot,'version':r.version,'previous':r.previous,'next':r.next,'previous_version':r.previous_version,'raw_write':row['x'][r.sequence-1].tolist(),'key':r.key.tolist(),'value':r.value.tolist(),'source_state':g['states'][r.sequence-1].tolist()})
    score=float(g['state'][0]);return {'id':row['id'],'group':row['group'],'pair':row['pair'],'label':row['label'],'prediction':int(score>=0),'correct':(score>=0)==bool(row['label']),'score':score,'target_record':row['record'],'selected_record':chosen,'target_attention':prob[catalogue.index(row['record'])] if row['record'] in catalogue else None,'last_query':last['query'].tolist(),'last_read':last['read'].tolist(),'records':records,'reads':[{'sequence':r['sequence'],'ids':r['ids'],'attention':r['prob'].tolist()} for r in reads]}

def audit_splits(data):
    answer={};seen={}
    for split in ('train','validation','test'):
        rows=dataset(data/f'{split}.tsv',torch.float64,'cpu');groups=collections.defaultdict(list);full=set();prefix=set()
        for r in rows:
            key=canonical(r['x'].tolist());full.add(key);prefix.add(canonical(r['x'][:-1].tolist()))
            group='-'.join(r['id'].split('-')[1:-1]) if split=='test' else 'all'
            groups[group].append(r['label'])
        answer[split]={'n':len(rows),'unique_raw_episodes':len(full),'positive':sum(r['label'] for r in rows),'groups':{g:{'n':len(v),'positive':sum(v)} for g,v in groups.items()}}
        seen[split]=(full,prefix)
    answer['overlaps']={f'{a}:{b}':{'raw':len(seen[a][0]&seen[b][0]),'write_prefix':len(seen[a][1]&seen[b][1])} for a,b in [('train','validation'),('train','test'),('validation','test')]}
    shared=collections.defaultdict(list)
    for r in dataset(data/'test.tsv',torch.float64,'cpu'):shared[canonical(r['x'][:-1].tolist())].append(r)
    answer['within_historic_test']={'shared_write_prefix_groups':sum(len(v)>1 for v in shared.values()),'same_record_incompatible_value_targets':sum(a['record']==b['record'] and a['value']!=b['value'] for v in shared.values() for i,a in enumerate(v) for b in v[i+1:])}
    return answer

def run(root,data,out):
    out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    cfg=json.loads((root/'manifest.json').read_text());state=restore(root/'latest.uno');old=json.loads((root/'test.json').read_text())
    require(cfg['source']==file_sha(sys_path/'torch_backend.py'),'HISTORIC_SOURCE_MISMATCH')
    require(all(file_sha(data/n)==h for n,h in cfg['input'].items()),'HISTORIC_INPUT_MISMATCH')
    require(state['config']==cfg and state['step']==1000 and state['selected']==old['selected'],'HISTORIC_CHECKPOINT_MISMATCH')
    marker=json.loads((root/'test-selected.json').read_text());require(marker=={'checkpoint':file_sha(root/'latest.uno'),'selected':state['selected']},'HISTORIC_SELECTION_MISMATCH')
    model=OrganizedF(data/'initial.tsv',torch.float32,'cpu',payload='legacy');model.load_state_dict(state['best']);model.validate()
    rows=enrich(dataset(data/'test.tsv',torch.float32,'cpu'));erased=enrich(dataset(data/'erased.tsv',torch.float32,'cpu'))
    result={'source_checkpoint':file_sha(root/'latest.uno'),'source':cfg,'selected':state['selected'],'split_audit':audit_splits(data),'conditions':{},'test_status':'HISTORIC_ALREADY_OPEN; no new acceptance claims','uncertainty_limit':'Historic intervals are descriptive resampling of observed seed groups, not confirmatory population coverage; adjacent Java seeds and imbalanced cells violate a simple IID interpretation'};predictions={}
    for name in ('full','memory_off','zero_values','erased','random_keys','permute_values','reverse_pairs'):
        selected=erased if name=='erased' else rows;mode='full' if name=='erased' else name
        predictions[name]=[export_row(model,r,mode) for r in selected]
        compact=[{k:r[k] for k in ('id','group','pair','label','prediction','score','correct')} for r in predictions[name]]
        groups={}
        for group in sorted(set(r['group'] for r in compact)):
            group_rows=[r for r in compact if r['group']==group];correct=sum(r['correct'] for r in group_rows);n=len(group_rows)
            traces=[r for r in predictions[name] if r['group']==group]
            groups[group]={'n':n,'correct':correct,'positive':sum(r['label'] for r in group_rows),'wilson_descriptive_ci95':wilson(correct,n),'key_top1':sum(r['selected_record']==r['target_record'] for r in traces),'mean_target_attention':sum(r['target_attention'] or 0 for r in traces)/n,'sse':sum((r['score']-(.8 if r['label'] else -.8))**2 for r in traces),'mse':sum((r['score']-(.8 if r['label'] else -.8))**2 for r in traces)/n}
        result['conditions'][name]={'n':len(compact),'correct':sum(r['correct'] for r in compact),'groups':groups}
        atomic(out/f'{name}.jsonl.gz',gzip.compress(('\n'.join(canonical(r) for r in predictions[name])+'\n').encode(),mtime=0))
        print('REPLAY',name,result['conditions'][name]['correct'],flush=True)
        if name in old:
            actual=scores(model,selected,mode);require(actual==old[name],f'EXACT_REPLAY_FAILED {name}')
    result['paired']={mode:paired(predictions['full'],predictions[mode]) for mode in ('memory_off','zero_values','erased','random_keys','permute_values')}
    # A paired controlled prefix proves a task-dependent auxiliary target conflict.
    x=torch.zeros(12,3);x[0]=torch.tensor([.5,1.,1.]);x[2]=torch.tensor([.25,-1.,1.]);y=x.clone();x[-1]=torch.tensor([0.,-1.,-1.]);y[-1]=torch.tensor([0.,0.,-2.])
    with torch.no_grad():a=model.replay(x);b=model.replay(y)
    require(torch.equal(a['store'].records[-1].value,b['store'].records[-1].value),'CAUSAL_PREFIX_NOT_EQUAL')
    result['value_target_conflict']={'same_write_prefix':True,'same_written_value_tensor':True,'r2_legacy_v0_target':.25,'r5_legacy_v0_target':-1.,'minimum_sum_of_two_value_mse':(.25+1.)**2/2,'minimum_mean_weighted_value_term':.2*(.25+1.)**2/4,'scope':'irreducible auxiliary-loss conflict for this shared causal prefix; not proof of global r5 cause or inability to store both fields elsewhere'}
    # Train-only linear probes diagnose available content/order without changing F or test-driven tuning.
    probes={}
    def features(split):
        features=[];labels=[]
        for r in enrich(dataset(data/f'{split}.tsv',torch.float32,'cpu')):
            if (r['id'].split('-')[1]!='r5_order' if split=='test' else int(r['id'].split('-')[-1])%5!=4):continue
            with torch.no_grad():g=model.replay(r['x'])
            for rec in g['store'].records:
                features.append({'key':torch.cat((rec.key,torch.ones(1))).double(),'value':torch.cat((rec.value,torch.ones(1))).double(),'key_value':torch.cat((rec.key,rec.value,torch.ones(1))).double(),'source_state':torch.cat((g['states'][rec.sequence-1],torch.ones(1))).double()})
                labels.append([float(rec.slot),float(rec.ordinal-1)])
        return {name:torch.stack([v[name] for v in features]) for name in features[0]},torch.tensor(labels,dtype=torch.float64)
    train_x,train_y=features('train');test_x,test_y=features('test');ridge=1e-3
    probes={'train_records':len(train_y),'historic_test_records':len(test_y),'ridge_fixed':ridge,'representations':{},'limit':'train-only diagnostic decoder, not the UNO answer decoder or a new accepted model'}
    for representation in train_x:
        tx=train_x[representation];vx=test_x[representation]
        coef=torch.linalg.solve(tx.T@tx+ridge*torch.eye(tx.shape[1],dtype=torch.float64),tx.T@train_y);fitted=vx@coef
        probes['representations'][representation]={'slot_sign_accuracy':float(((fitted[:,0]>=0)==(test_y[:,0]>=0)).double().mean()),'second_write_accuracy':float(((fitted[:,1]>=.5)==(test_y[:,1]>=.5)).double().mean())}
    result['probes']=probes;atomic(out/'audit.json',canonical(result).encode());print(canonical({'paired':result['paired'],'conflict':result['value_target_conflict'],'probes':probes}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results',type=pathlib.Path);p.add_argument('data',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args();run(a.results,a.data,a.output)
