#!/usr/bin/env python3
"""Local, conservative corpus gate. No training; no automatic legal approval."""
import argparse, collections, csv, hashlib, heapq, json, os, re, shutil, sys, tempfile, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone

VERSION = '1.0.0'
REPO = 'PleIAs/Russian-PD'
EXPECTED = {'russian_pd_1.parquet': 'e58e4d472ae72980286f3794d881e52384690d8a6899424b3b8cf462cd482500', 'russian_pd_2.parquet': '703ec2ae3ebdc5b90c7e06b108e8fd03ed360fd426c6d04f85d60e3f7dc9667d', 'russian_pd_3.parquet': 'cb97a987a0dbc6fe370f8ee311b0c761cf237b1460c130d02673425c789e4f6b', 'russian_pd_4.parquet': 'fab8349cb576ca8c3ef9283b224d6eac52c996a1fe047364e8a5e658e97d4878', 'russian_pd_5.parquet': 'f47186aaed6d633eee462c5c3684c10e3ed70966bca50848d40e8674066b08fa', 'russian_pd_6.parquet': '6e292addbdb155c18fc524ef7029b5f7c9331f1c5cfd397e7d1a894468010255', 'russian_pd_7.parquet': '093ebf68304695594049074f27328857434a919ce5954620614459f5cf9e34bf', 'russian_pd_8.parquet': '8e4c37cf73de0ea7de9545c14ae5c2d9a8c719da4b131c8e23e56d5789327c0f', 'russian_pd_9.parquet': '695fe8aea5423589192961f1c597aadc1059e4ccc8c445264386153c7530ed91'}
COLS = ['identifier','creator','title','publication_date','word_count','text']
WORD = re.compile(r'[^\W\d_]+', re.UNICODE)
CYR = re.compile(r'[а-яёѣіѳѵ]', re.I)
ID = re.compile(r'[A-Za-z0-9_.-]{1,200}\Z')
PII = {'email': re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}\b'), 'phone': re.compile(r'(?<!\w)(?:\+7|8)[\s()-]*\d{3}[\s()-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)'), 'url': re.compile(r'https?://\S+', re.I), 'identifier_context': re.compile(r'\b(?:паспорт|снилс|инн)\b[^\n]{0,24}\d{6,}', re.I)}
REVIEW = ['record_id','identifier','creator','title','publication_date','source_url','flags','decision','reviewer','rights_evidence','markets','rights_basis','privacy_checked','quality_checked','work_key']
K=128
MASK=(1<<64)-1

def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def js(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def put(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def lines(p):
    with p.open(encoding='utf-8') as f:
        for l in f: yield json.loads(l)
def utc(): return datetime.now(timezone.utc).isoformat()
def normal(s): return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def safe_cell(s):
    s=str(s or ''); return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s

def quality(s):
    n=len(s); alpha=sum(c.isalpha() for c in s); cyr=sum(1 for _ in CYR.finditer(s)); bad=sum(c=='\ufffd' or (unicodedata.category(c)=='Cc' and c not in '\r\n\t') for c in s)
    # Detect OCR fragments, not semantic correctness. No modernization of spelling.
    nw=single=0
    for m in WORD.finditer(s):
        nw+=1; single+=len(m.group())==1
    metrics={'chars':n,'words':nw,'cyrillic_share':round(cyr/max(alpha,1),5),'letters_share':round(alpha/max(n,1),5),'bad_share':round(bad/max(n,1),6),'single_word_share':round(single/max(nw,1),5)}
    reject=[]; flags=[]
    if n<500 or nw<80: reject.append('too_short')
    if cyr/max(alpha,1)<.85: reject.append('not_predominantly_russian')
    if alpha/max(n,1)<.55 or bad/max(n,1)>.002 or single/max(nw,1)>.27: reject.append('ocr_or_noise')
    for name,pat in PII.items():
        if pat.search(s): flags.append('privacy_review:'+name)
    if re.search(r'digitized by google|google books|internet archive|оцифровано',s,re.I): flags.append('scan_boilerplate')
    return metrics,reject,flags

def sketch(s):
    # Bottom-k distinct hashes of 5-word shingles. Bounded memory, approximate similarity.
    q=collections.deque(maxlen=5); chosen=set(); heap=[]
    for m in WORD.finditer(s):
        q.append(m.group().casefold())
        if len(q)<5: continue
        h=int.from_bytes(hashlib.blake2b(' '.join(q).encode(),digest_size=8).digest(),'big')
        if h in chosen: continue
        if len(heap)<K: heapq.heappush(heap,-h); chosen.add(h)
        elif h < -heap[0]: chosen.remove(-heapq.heapreplace(heap,-h)); chosen.add(h)
    return sorted(chosen)

def near(a,b):
    union=sorted(set(a)|set(b))[:K]
    return len(set(union)&set(a)&set(b))/max(len(union),1)>=.65 and len(union)>=16

def groups(records):
    parent=list(range(len(records))); first={}; inverted=collections.defaultdict(list)
    def root(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def join(a,b):
        a,b=root(a),root(b)
        if a!=b: parent[max(a,b)]=min(a,b)
    for i,r in enumerate(records):
        for field,key in [('id',r['identifier']),('title',normal(r['title'])),('hash',r['normalized_sha256'])]:
            if not key: continue
            k=(field,key)
            if k in first: join(i,first[k])
            else: first[k]=i
        a=r['sketch']; counts=collections.Counter(j for h in a for j in inverted[h])
        for j,c in counts.items():
            if c>=12 and near(a,records[j]['sketch']): join(i,j)
        for h in a: inverted[h].append(i)
    return {r['record_id']:records[root(i)]['record_id'] for i,r in enumerate(records)}

def parquet_rows(p):
    import pyarrow.parquet as pq
    pf=pq.ParquetFile(p, memory_map=False, pre_buffer=False)
    missing=set(COLS)-set(pf.schema_arrow.names)
    if missing: raise ValueError(f'{p.name}: missing columns {sorted(missing)}')
    # Refuse especially large row groups on low-RAM machines; this is not a hard RSS cap.
    for i in range(pf.metadata.num_row_groups):
        if pf.metadata.row_group(i).total_byte_size>2*1024**3: raise ValueError(f"{p.name}: row group {i} exceeds 2 GiB safety threshold; do not load on Acer")
    for batch in pf.iter_batches(batch_size=1,columns=COLS,use_threads=False):
        yield batch.to_pylist()[0]

def atomic_dir(dest):
    if dest.exists(): raise FileExistsError(f'Output exists: {dest}; choose a new name, never overwrite')
    dest.parent.mkdir(parents=True,exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=dest.name+'.partial-',dir=dest.parent))

def scan(files,dest,expected,rows=parquet_rows):
    tmp=atomic_dir(dest); (tmp/'texts').mkdir(); stats=collections.Counter(); sources=[]; eligible=[]
    try:
        with (tmp/'records.jsonl').open('w',encoding='utf-8',newline='\n') as out:
            for p in files:
                digest=fsha(p); trusted=expected.get(p.name)==digest
                if p.name in expected and not trusted: raise ValueError(f'SHA256 mismatch: {p.name}')
                src={'name':p.name,'sha256':digest,'bytes':p.stat().st_size,'verified_expected_sha256':trusted,'repo':REPO,'url':f'https://huggingface.co/datasets/{REPO}/blob/main/{urllib.parse.quote(p.name)}'}; sources.append(src)
                for i,row in enumerate(rows(p)):
                    stats['rows']+=1
                    rid=str(row.get('identifier') or ''); title=str(row.get('title') or ''); author=str(row.get('creator') or ''); year=row.get('publication_date'); text=row.get('text'); valid=isinstance(text,str); text=text if valid else ''
                    rawhash=sha(text.encode('utf-8')); recid=sha(js([digest,i,rid,title,author,str(year),rawhash]).encode()); metrics,reject,flags=quality(text)
                    if not valid: reject.append('invalid_text')
                    if not trusted: reject.append('source_hash_not_verified')
                    if not ID.fullmatch(rid) or rid in ('.','..') or not title.strip(): reject.append('missing_source_identity')
                    if not isinstance(year,int) or isinstance(year,bool) or not 1000<=year<1884: reject.append('publication_date_outside_policy')
                    if not author.strip(): flags.append('author_unknown')
                    flags.append('manual_rights_review_required')
                    if isinstance(row.get('word_count'),int) and abs(row['word_count']-metrics['words'])>max(100,metrics['words']*.35): flags.append('word_count_discrepancy')
                    rec={'record_id':recid,'identifier':rid,'title':title,'creator':author,'publication_date':year,'source_file':p.name,'source_sha256':digest,'row':i,'source_url':'https://archive.org/details/'+urllib.parse.quote(rid,safe='') if ID.fullmatch(rid) else '', 'raw_text_sha256':rawhash,'metrics':metrics,'reject':reject,'flags':flags,'status':'REJECTED' if reject else 'PENDING_REVIEW'}
                    if not reject:
                        rec['normalized_sha256']=sha(normal(text).encode()); rec['sketch']=sketch(text); (tmp/'texts'/f'{recid}.txt').write_bytes(text.encode()); eligible.append(rec)
                    stats[rec['status']]+=1; stats.update('reject:'+v for v in reject); out.write(js(rec)+'\n')
                    if stats['rows']%25==0: print('ROWS',stats['rows'],'REVIEW',stats['PENDING_REVIEW'],flush=True)
                if fsha(p)!=digest: raise ValueError(f'Input changed during scan: {p.name}')
        g=groups(eligible); put(tmp/'groups.json',g)
        with (tmp/'review.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=REVIEW,delimiter=';'); w.writeheader()
            for r in eligible:
                w.writerow({**{k:safe_cell(r[k]) for k in ('record_id','identifier','creator','title','publication_date','source_url')},'flags':','.join(r['flags'])})
        manifest={'version':VERSION,'created_utc':utc(),'sources':sources,'counts':dict(stats),'records_sha256':fsha(tmp/'records.jsonl'),'groups_sha256':fsha(tmp/'groups.json'),'automatic_legal_approval':False,'status':'SCAN_COMPLETE_PENDING_REVIEW'}; put(tmp/'scan.json',manifest)
        tmp.rename(dest); print(js(manifest),flush=True)
    except BaseException:
        print('INCOMPLETE, not usable:',tmp,file=sys.stderr); raise

def load_scan(base):
    m=json.loads((base/'scan.json').read_text(encoding='utf-8'))
    if m['version']!=VERSION or m['status']!='SCAN_COMPLETE_PENDING_REVIEW' or fsha(base/'records.jsonl')!=m['records_sha256'] or fsha(base/'groups.json')!=m['groups_sha256']: raise ValueError('Scan integrity failed')
    return m,list(lines(base/'records.jsonl')),json.loads((base/'groups.json').read_text(encoding='utf-8'))

def evidence(base,limit):
    _,rr,_=load_scan(base); target=base/'source_metadata'; target.mkdir(exist_ok=True); done=0
    for r in rr:
        if r['status']!='PENDING_REVIEW': continue
        p=target/(r['record_id']+'.json')
        if p.exists(): continue
        if done>=limit: break
        url='https://archive.org/metadata/'+urllib.parse.quote(r['identifier'],safe='')
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'UNO-corpus-review/1.0'})
            with urllib.request.urlopen(req,timeout=20) as f: raw=f.read(8*1024*1024+1)
            if len(raw)>8*1024*1024: raise ValueError('metadata exceeds limit')
            item=json.loads(raw); md=item.get('metadata',{}); result={'fetched_utc':utc(),'url':url,'response_sha256':sha(raw),'metadata':{k:md.get(k) for k in ('identifier','title','creator','date','year','rights','licenseurl','publisher','language','possible-copyright-status')},'not_legal_approval':True}
            put(p,result); (target/(r['record_id']+'.raw.json')).write_bytes(raw); done+=1
        except Exception as e: print('METADATA_UNAVAILABLE',r['identifier'],str(e),file=sys.stderr); done+=1
    print('Metadata attempts:',done)

def export(base,review,dest):
    m,rr,g=load_scan(base); records={r['record_id']:r for r in rr}; approved=[]; seen=set()
    with review.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter=';')
        if not set(REVIEW)<=set(reader.fieldnames or []): raise ValueError('Invalid review header; keep semicolon delimiter')
        for a in reader:
            rid=a['record_id']; decision=a['decision'].strip().upper()
            if rid in seen or rid not in records: raise ValueError('Duplicate or unknown review ID')
            seen.add(rid)
            if decision in ('','REJECT','HOLD'): continue
            if decision!='APPROVE': raise ValueError('Unknown review decision')
            r=records[rid]
            if r['status']!='PENDING_REVIEW' or rid not in g: raise ValueError('Rejected record cannot be approved')
            if not all(a[k].strip() for k in ('reviewer','rights_evidence','markets','rights_basis','work_key')) or any(a[k].strip().upper()!='YES' for k in ('privacy_checked','quality_checked')): raise ValueError('Incomplete manual review: '+rid)
            approved.append((r,a))
    # Unite reviewed bibliographic work IDs with similarity groups, including transitive links.
    parents={v:v for v in g.values()}; work={}
    def root(x):
        while parents[x]!=x: x=parents[x]
        return x
    for r,a in approved:
        k=normal(a['work_key']); v=g[r['record_id']]
        if k in work: parents[root(v)]=root(work[k])
        else: work[k]=v
    unique={}
    for r,a in sorted(approved,key=lambda t:(-t[0]['metrics']['chars'],t[0]['record_id'])): unique.setdefault(root(g[r['record_id']]),(r,a))
    ordered=sorted(unique,key=lambda k:sha(('UNO-split-v1:'+k).encode()))
    if len(ordered)<3: raise ValueError('Need at least 3 independently reviewed work groups; nothing exported')
    n=len(ordered); ntest=max(1,n//10); ndev=max(1,n//10); splits={k:('test' if i<ntest else 'dev' if i<ntest+ndev else 'train') for i,k in enumerate(ordered)}
    tmp=atomic_dir(dest); counts=collections.Counter(); words=collections.Counter()
    try:
        import contextlib
        with contextlib.ExitStack() as st:
            outs={s:st.enter_context((tmp/(s+'.jsonl')).open('w',encoding='utf-8',newline='\n')) for s in ('train','dev','test')}
            for k in ordered:
                r,a=unique[k]; raw=(base/'texts'/(r['record_id']+'.txt')).read_bytes()
                if sha(raw)!=r['raw_text_sha256']: raise ValueError('Text integrity failed')
                s=splits[k]; out={'record_id':r['record_id'],'work_group':k,'identifier':r['identifier'],'title':r['title'],'creator':r['creator'],'publication_date':r['publication_date'],'source_url':r['source_url'],'source_sha256':r['source_sha256'],'row':r['row'],'text_sha256':r['raw_text_sha256'],'review':{f:a[f] for f in ('reviewer','rights_evidence','markets','rights_basis','privacy_checked','quality_checked','work_key')},'text':raw.decode('utf-8')}; outs[s].write(js(out)+'\n'); counts[s]+=1; words[s]+=r['metrics']['words']
        put(tmp/'manifest.json',{'version':VERSION,'created_utc':utc(),'scan_sha256':fsha(base/'scan.json'),'review_sha256':fsha(review),'sources':m['sources'],'approved_rows':len(approved),'selected_groups':n,'counts':dict(counts),'words':dict(words),'files':{s+'.jsonl':fsha(tmp/(s+'.jsonl')) for s in ('train','dev','test')},'legal_guarantee':False,'split_policy':'whole work groups; one representative; approximate dedup; stable for frozen scan/review'})
        tmp.rename(dest); print('EXPORTED',dict(counts))
    except BaseException: print('INCOMPLETE:',tmp,file=sys.stderr); raise

def report(base):
    import zipfile
    load_scan(base)
    dest=base.parent/('REVIEW_REPORT_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')+'.zip')
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in ('scan.json','records.jsonl','groups.json','review.csv'):
            z.write(base/name,name)
        for p in sorted((base/'source_metadata').glob('*.json')):
            if not p.name.endswith('.raw.json'): z.write(p,'source_metadata/'+p.name)
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None: raise ValueError('Report ZIP integrity failed')
    print('REPORT:',dest)

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('scan'); s.add_argument('--input',type=Path,default=Path('input')); s.add_argument('--out',type=Path,default=Path('scan_result')); s.add_argument('--expected',type=Path)
    e=sub.add_parser('evidence'); e.add_argument('--scan',type=Path,default=Path('scan_result')); e.add_argument('--limit',type=int,default=20)
    x=sub.add_parser('export'); x.add_argument('--scan',type=Path,default=Path('scan_result')); x.add_argument('--review',type=Path,default=Path('scan_result/review.csv')); x.add_argument('--out',type=Path,default=Path('corpus'))
    q=sub.add_parser('report'); q.add_argument('--scan',type=Path,default=Path('scan_result'))
    a=p.parse_args()
    if a.cmd=='scan':
        fs=sorted(a.input.glob('*.parquet')); expected=EXPECTED.copy()
        if a.expected:
            extra=json.loads(a.expected.read_text(encoding='utf-8'))
            for k,v in extra.items():
                if not re.fullmatch('[0-9a-f]{64}',v) or (k in expected and expected[k]!=v): raise ValueError('Invalid expected hash: '+k)
            expected.update(extra)
        if not fs: p.error('No .parquet in input folder')
        scan(fs,a.out,expected)
    elif a.cmd=='evidence': evidence(a.scan,max(0,a.limit))
    elif a.cmd=='report': report(a.scan)
    else: export(a.scan,a.review,a.out)
if __name__=='__main__':
    try: main()
    except (Exception,KeyboardInterrupt) as e: print('ERROR:',e,file=sys.stderr); sys.exit(1)
