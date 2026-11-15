"""Fresh balanced paired corpus. Pair namespaces hashed independently; no consecutive-seed LCG issue.
Raw observations/requests are identical for all arms. Labels/record targets never enter F inputs.
"""
import pathlib,json,hashlib,random
import torch
from engine import require,canonical,atomic,file_sha

FAMILIES=['r1_single','r2_two','r3_three','r4_overwrite','r5_order','r6_previous','r7_next','r8_last_value','r9_previous_version']
LENGTHS=[12,24,48,96]

def digest_seed(namespace):return int.from_bytes(hashlib.sha256(namespace.encode()).digest()[:8],'little')
def oracle(x,family):
    writes=[(i+1,f) for i,f in enumerate(x[:-1]) if f[2]==1.]
    require(bool(writes),'NO_WRITES');query=x[-1]
    if family=='r5_order':record,value=writes[-1][0],writes[-1][1][1]
    elif family in ('r1_single','r2_two','r3_three','r4_overwrite'):
        record,f=next((seq,f) for seq,f in reversed(writes) if f[1]==query[1]);value=f[0]
    elif family=='r8_last_value':record,f=writes[-1];value=f[0]
    else:
        anchor=round(query[0]*96);ix=next(i for i,(seq,_) in enumerate(writes) if seq==anchor)
        if family=='r6_previous':require(ix>0,'NO_PREVIOUS');record,f=writes[ix-1]
        elif family=='r7_next':require(ix+1<len(writes),'NO_NEXT');record,f=writes[ix+1]
        else:
            candidates=[(seq,f) for seq,f in writes[:ix] if f[1]==writes[ix][1][1]]
            require(bool(candidates),'NO_PREVIOUS_VERSION');record,f=candidates[-1]
        value=f[0]
    return record,value,int(value>0)

def pair(split,family,length,index,seed):
    namespace=f'TRAIN002/V1/{seed}/{split}/{family}/{length}/{index}';rng=random.Random(digest_seed(namespace))
    x=[[rng.uniform(-1,1),rng.uniform(-1,1),0.] for _ in range(length)]
    n={'r1_single':1,'r2_two':2,'r3_three':3,'r4_overwrite':4,'r5_order':2,'r6_previous':3,'r7_next':3,'r8_last_value':3,'r9_previous_version':4}[family]
    k=min(n,3);codes=[0.] if k==1 else ([-1.,1.] if k==2 else [-1.,0.,1.])
    slots=list(codes);rng.shuffle(slots)
    if n==4:slots.append(rng.choice(codes))
    if family=='r9_previous_version':
        first=[-1.,1.];rng.shuffle(first);slots=first+first
    stamps=sorted(rng.sample(range(min(length-2,max(5,(length+1)//2))),n))
    for position,slot in zip(stamps,slots):
        value=rng.uniform(-1,1)
        if abs(value)<1e-5:value=.1
        x[position]=[value,slot,1.]
    if family in FAMILIES[:4]:x[-1]=[0.,rng.choice(codes),-1.]
    elif family=='r5_order':x[-1]=[0.,0.,-2.]
    elif family=='r8_last_value':x[-1]=[0.,0.,-.75]
    else:
        anchor=rng.randrange(1,n) if family=='r6_previous' else (rng.randrange(0,n-1) if family=='r7_next' else rng.choice([2,3]))
        opcode={'r6_previous':-.25,'r7_next':-.5,'r9_previous_version':-1.5}[family]
        x[-1]=[(stamps[anchor]+1)/96.,slots[anchor],opcode]
    output=[]
    for complement in (0,1):
        raw=[v.copy() for v in x]
        if complement:
            for f in raw[:-1]:
                if f[2]==1.:f[1 if family=='r5_order' else 0]*=-1
        record,value,label=oracle(raw,family)
        output.append({'id':namespace+f'/{complement}','pair':namespace,'group':f'{family}-{length}','family':family,'length':length,'x':raw,'record':record,'value':value,'label':label,'state':.8 if label else -.8})
    require(output[0]['label']!=output[1]['label'],'BALANCE_ERROR');return output

def erase(row):
    out={**row,'x':row['x'].clone() if isinstance(row['x'],torch.Tensor) else [f.copy() for f in row['x']]}
    if row['family']=='r5_order':
        for f in out['x'][:-1]:
            if f[2]==1.:f[1]=0.
    else:
        # Destroy all answer content, retain observable ops/addresses/times and original labels.
        for f in out['x'][:-1]:
            if f[2]==1.:f[0]=0.
    return out

def generate(root,seed=2026111502,train_pairs=16,val_pairs=4,test_pairs=16):
    root.mkdir(parents=True,exist_ok=False);manifest={'format':'TRAIN002/PAIRED/V1','seed':seed,'pairs_per_cell':{'train':train_pairs,'validation':val_pairs,'test':test_pairs},'test_policy':'LOCKED before any training; test labels never loaded by train','files':{},'balanced':{},'overlaps':{}}
    fingerprints={};prefixes={}
    for split,pairs in [('train',train_pairs),('validation',val_pairs),('test',test_pairs)]:
        rows=[row for family in FAMILIES for length in ([12,24,32] if split=='train' else LENGTHS) for i in range(pairs) for row in pair(split,family,length,i,seed)]
        # Fixed shuffle mixes task groups; pairs remain in one split, not consecutive minibatch targets.
        random.Random(digest_seed(f'sampler/{seed}/{split}')).shuffle(rows)
        body='\n'.join(canonical(row) for row in rows)+'\n';atomic(root/f'{split}.jsonl',body.encode());manifest['files'][split]=file_sha(root/f'{split}.jsonl')
        fingerprints[split]={canonical(r['x']) for r in rows};prefixes[split]={canonical(r['x'][:-1]) for r in rows}
        groups={}
        for row in rows:
            g=groups.setdefault(row['group'],{'n':0,'positive':0});g['n']+=1;g['positive']+=row['label']
        require(all(g['positive']*2==g['n'] for g in groups.values()),'UNBALANCED_GROUP');manifest['balanced'][split]=groups
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        overlap={'raw':len(fingerprints[a]&fingerprints[b]),'prefix':len(prefixes[a]&prefixes[b])};require(not any(overlap.values()),'SPLIT_OVERLAP');manifest['overlaps'][f'{a}:{b}']=overlap
    atomic(root/'manifest.json',canonical(manifest).encode());return manifest

def load(path,dtype,device):
    rows=[]
    for line in path.read_text().splitlines():
        r=json.loads(line);require(r['family'] in FAMILIES and 10<=r['length']<=96 and len(r['x'])==r['length'],'DATA_SHAPE')
        require(r['label'] in (0,1) and r['state']==(.8 if r['label'] else -.8),'LABEL_STATE')
        seq,value,label=oracle(r['x'],r['family']);require((seq,value,label)==(r['record'],r['value'],r['label']),'ORACLE_MISMATCH')
        r['x']=torch.tensor(r['x'],dtype=dtype,device=device);require(bool(torch.isfinite(r['x']).all()),'NONFINITE_DATA');rows.append(r)
    require(rows and len({r['id'] for r in rows})==len(rows),'DUPLICATE_IDS');return rows
