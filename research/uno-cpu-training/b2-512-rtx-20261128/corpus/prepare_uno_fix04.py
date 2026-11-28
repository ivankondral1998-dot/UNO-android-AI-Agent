#!/usr/bin/env python3
"""UNO corpus preparation FIX04; no model training, no changes to input files."""
import argparse, bz2, collections, gzip, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, time, unicodedata, zipfile
import pd_gate
from pathlib import Path

SPLITS=('train','validation','calibration','test')
LEGACY_SHA='1c622409b42d96d339505d15d69da66d7176788f358e828672970c3ee637474f'
HERE=Path(__file__).resolve().parent
BASE_SHA='4553129512603de3aa4bd18d764a0bb310bb9cc68b83b0ea3943b6116c8e42b5'
HOLDOUT_SHA='5fc75454a13925d7d0ef6f95d8c833f1a76dbf95af3438186382ca34dea89d10'
INTENT_PREFIXES=('alarm_', 'audio_', 'datetime_', 'lists_', 'play_', 'music_', 'general_', 'iot_')
INTENT_EXCLUDED={'iot_cleaning','iot_coffee','iot_hue_lightchange','iot_hue_lightdim','iot_hue_lightoff','iot_hue_lighton','iot_hue_lightup','iot_wemo_off','iot_wemo_on','play_game','general_joke','general_quirky'}
SENSITIVE_SLOTS={'person','email_address','email_folder','place_name','house_place','business_name','business_type','media_type'}
SLOT=re.compile(r'\[([a-z_]+)\s*:\s*([^\[\]]+?)\s*\]')
EVERYDAY='kukunechka/russian-everyday-dialogues'
SPECIAL=['<pad>','<unk>','<bos>','<eos>','<user>','<assistant>','<event>','<end>']
SOURCES={
 'oasst2': ['https://huggingface.co/datasets/OpenAssistant/oasst2','Apache-2.0'],
 'aya': ['https://huggingface.co/datasets/CohereLabs/aya_dataset','Apache-2.0'],
 'massive': ['https://huggingface.co/datasets/AmazonScience/massive','CC-BY-4.0'],
 'russian_pd': ['https://huggingface.co/datasets/PleIAs/Russian-PD','public-domain claimed; work-level rights pending'],
 'tatoeba': ['https://tatoeba.org/en/downloads','CC-BY-2.0-FR'],
 'taskmaster': ['https://github.com/google-research-datasets/Taskmaster','CC-BY-4.0; translation pending']}
PII=re.compile(r'(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b|(?<!\d)(?:\+7|8)[\s().-]*\d{3}[\s().-]*\d{3}[\s().-]*\d{2}[\s().-]*\d{2}(?!\d)|\b(?:sk-[A-Za-z0-9_-]{15,}|ghp_[A-Za-z0-9]{15,})\b')
CYR=re.compile('[А-Яа-яЁё]')

def say(s): print(s,flush=True)
def dump(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha(p):
 with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def norm(s): return ' '.join(unicodedata.normalize('NFKC',s).casefold().replace('ё','е').split())
def prompt_key(s): return 'prompt:'+h(' '.join(re.findall(r'\w+',norm(s))))
def clean(s):
 if not isinstance(s,str): return ''
 s=unicodedata.normalize('NFC',s).replace('\r\n','\n').replace('\r','\n').strip()
 s=''.join(c for c in s if c in '\n\t' or unicodedata.category(c)!='Cc')
 if '\ufffd' in s or any(unicodedata.category(c) in ('Cf','Cs') for c in s) or PII.search(s) or re.search(r'(?i)\b(?:паспорт|снилс|инн)\b[^\n]{0,24}\d{6,}|\b[\w.+-]+@[\w.-]+\.[a-zа-яё]{2,}\b',s) or any(x in s.casefold() for x in SPECIAL): return ''
 return s

def ru(s):
 letters=sum(c.isalpha() for c in s)
 return bool(letters and len(CYR.findall(s))>=max(1,letters*.35))
def split(key):
 n=int(h('UNO-split-v1:'+key)[:8],16)%100
 return 'test' if n<3 else 'validation' if n<6 else 'train'
def rows(f):
 for i,line in enumerate(f,1):
  if line.strip():
   try: yield json.loads(line)
   except Exception as e: raise ValueError(f'invalid JSONL line {i}: {e}') from e

def chunks(s,limit=4096):
 while len(s)>limit:
  i=max(s.rfind('\n',limit//2,limit),s.rfind(' ',limit//2,limit))
  if i<1:i=limit
  yield s[:i].strip(); s=s[i:].lstrip()
 if s:yield s

def find_input(root):
 a=sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()))
 return {'oasst_raw':[p for p in a if 'oasst2' in p.name.lower() and p.name.endswith('.trees.jsonl.gz')],
 'oasst_ru':[p for p in a if 'oasst2_ru_main_branch' in p.name.lower() and p.suffix=='.jsonl'],
 'aya':[p for p in a if p.suffix=='.parquet' and ('aya' in str(p.relative_to(root)).lower() or re.match(r'train-00000-of-00001(?: \(\d+\))?\.parquet$',p.name)) and 'massive' not in p.name],
 'massive':[p for p in a if p.suffix=='.parquet' and 'massive' in p.name.lower()],
 'russian_pd':[p for p in a if re.match(r'russian_pd_\d+(?: \(\d+\))?\.parquet$',p.name.lower())],
 'tatoeba':[p for p in a if 'rus_sentences_detailed' in p.name.lower() and p.suffix in ('.bz2','.tsv')],
 'taskmaster':[p for p in a if ('taskmaster' in p.name.lower() or p.name.lower()=='master.zip') and p.suffix=='.zip']}

def ensure_deps(root, parquet, tokenizer):
 deps=HERE/'deps'; sys.path.insert(0,str(deps))
 if not deps.resolve().is_relative_to(root):raise ValueError('Dependency folder outside UNO')
 import importlib.util
 needed=[x for x,on in [('pyarrow',parquet),('tokenizers',tokenizer)] if on and importlib.util.find_spec(x) is None]
 if not needed:return
 uv=root/'uv'/'uv.exe'
 if not uv.is_file():raise RuntimeError('Missing '+', '.join(needed)+'; expected '+str(uv))
 deps.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy(); temp=root/'tmp'; temp.mkdir(exist_ok=True)
 env.update(TEMP=str(temp),TMP=str(temp),UV_CACHE_DIR=str(root/'cache'),PYTHONNOUSERSITE='1',PYTHONUTF8='1',XDG_CACHE_HOME=str(root/'cache'))
 say('Installing isolated data dependencies: '+', '.join(needed))
 subprocess.run([str(uv),'pip','install','--python',sys.executable,'--target',str(deps),'--only-binary',':all:',*needed],env=env,check=True)
 importlib.invalidate_caches()

PARQUET_GROUP_EVENTS=[]
GIB=1024**3

def available_ram():
 # OS-level available physical RAM, no additional package and no system changes.
 if os.name=='nt':
  import ctypes
  class MemoryStatus(ctypes.Structure):
   _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended')]
  m=MemoryStatus();m.length=ctypes.sizeof(m)
  if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):return int(m.avail_phys)
 elif sys.platform.startswith('linux'):
  with open('/proc/meminfo',encoding='ascii') as f:
   for line in f:
    if line.startswith('MemAvailable:'):return int(line.split()[1])*1024
 return None

def parquet_rows(p,required,optional=()):
 import pyarrow.parquet as pq
 pf=pq.ParquetFile(p,memory_map=False,pre_buffer=False); cols=set(pf.schema_arrow.names)
 if not set(required)<=cols:raise ValueError(f'{p.name}: missing columns {set(required)-cols}; found {sorted(cols)}')
 selected=list(required)+[c for c in optional if c in cols]; is_pd=bool(re.fullmatch(r'russian_pd_\d+(?: \(\d+\))?\.parquet',p.name.lower())) and 'text' in required
 hf=json.loads((pf.schema_arrow.metadata or {}).get(b'huggingface',b'{}')).get('info',{}).get('features',{})
 physical_row=0
 for i in range(pf.metadata.num_row_groups):
  rg=pf.metadata.row_group(i); size=rg.total_byte_size
  if size>2*GIB:
   if not is_pd:raise ValueError(f'{p.name}: row group too large (>2 GiB)')
   # Caller verifies pinned official file SHA before entering the reader.
   # A group is not one Python batch. Admit only when physical headroom is
   # sufficient for the full uncompressed group plus other allocations.
   avail=available_ram()
   if avail is None or avail<max(2*GIB,size*2):
    event={'file':p.name,'row_group':i,'bytes':size,'available_ram':avail,'status':'SKIPPED_LOW_RAM'};PARQUET_GROUP_EVENTS.append(event);say(dump(event));physical_row+=rg.num_rows;continue
   event={'file':p.name,'row_group':i,'bytes':size,'available_ram':avail,'status':'STREAMING_BATCH_ONE'};PARQUET_GROUP_EVENTS.append(event);say(dump(event))
  for j,batch in enumerate(pf.iter_batches(batch_size=1 if 'text' in required else 256,row_groups=[i],columns=selected,use_threads=False)):
   if is_pd and j%32==0:
    avail=available_ram()
    if avail is not None and avail<GIB:
     event={'file':p.name,'row_group':i,'status':'STOPPED_LOW_RAM','available_ram':avail};PARQUET_GROUP_EVENTS.append(event);say(dump(event));break
   for k,row in enumerate(batch.to_pylist()):
    if is_pd:row['_physical_row']=physical_row+j+k
    for key in ('intent','scenario'):
     names=hf.get(key,{}).get('names',[]); value=row.get(key)
     if isinstance(value,int) and isinstance(names,list) and 0<=value<len(names):row[key]=names[value]
    yield row
  physical_row+=rg.num_rows


class Store:
 def __init__(self,out):
  self.db=sqlite3.connect(out/'index.sqlite'); self.count=collections.Counter(); self.i=0
  self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
 CREATE TABLE records(id INTEGER PRIMARY KEY, kind TEXT, split TEXT, source TEXT, fingerprint TEXT, payload TEXT, priority INTEGER);
 CREATE TABLE keys(key TEXT,rid INTEGER); CREATE INDEX keys_k ON keys(key); CREATE INDEX keys_r ON keys(rid);
 CREATE TABLE locked(key TEXT PRIMARY KEY);
 CREATE TABLE protected_train(key TEXT PRIMARY KEY);
 CREATE TABLE intent_labels(rid INTEGER PRIMARY KEY, label TEXT NOT NULL);''')
 def lock(self,key):self.db.execute('INSERT OR IGNORE INTO locked VALUES(?)',(key,))
 def add(self,kind,part,source,payload,keys=(),priority=0):
  if part not in SPLITS:raise ValueError(part)
  if kind=='language': texts=[payload['text']]
  elif kind=='dialogue':texts=[m['text'] for m in payload['messages']]
  else:texts=[payload['text']]
  f=h(kind+'\n'+'\n'.join(norm(t) for t in texts)); ks=set(keys)|{'exact:'+f}
  rid=self.db.execute('INSERT INTO records(kind,split,source,fingerprint,payload,priority) VALUES(?,?,?,?,?,?)',(kind,part,source,f,dump(payload),priority)).lastrowid
  self.db.executemany('INSERT INTO keys VALUES(?,?)',[(k,rid) for k in sorted(ks)]); self.i+=1
  if source.startswith('r54:') and part=='train':
   self.db.executemany('INSERT OR IGNORE INTO protected_train VALUES(?)',[(k,) for k in sorted(ks)])
  if kind=='intent':
   label=dump([payload['intent'],sorted((x['name'],norm(x['value'])) for x in payload['slots'])]);self.db.execute('INSERT INTO intent_labels VALUES(?,?)',(rid,label))
  if self.i%5000==0:self.db.commit();say(f'  {self.i:,} candidate records')
 def lang(self,s,part,source,meta):
  s=clean(s)
  if not s or not ru(s):self.count[source+':filtered']+=1;return False
  keys=['text:'+h(norm(s)),prompt_key(s)]
  if meta.get('work_key'):keys.append('work:'+meta['work_key'])
  self.add('language',part,source,{'text':s,'source':source,'meta':meta},keys);return True
 def chat(self,turns,part,source,meta,priority=0):
  m=[]
  for role,s in turns:
   s=clean(s)
   if not s or len(s)>48000 or role not in ('user','assistant'):self.count[source+':filtered']+=1;return
   if m and m[-1]['role']==role:
    self.count[source+':nonalternating']+=1;return
   else:m.append({'role':role,'text':s})
  if m and m[-1]['role']=='user':m.pop()
  if len(m)<2 or m[0]['role']!='user' or not all(ru(x['text']) or not any(c.isalpha() for c in x['text']) for x in m):self.count[source+':filtered']+=1;return
  keys=[prompt_key(x['text']) for x in m if x['role']=='user']
  keys.extend('text:'+h(norm(x['text'])) for x in m if len(x['text'].split())>=6)
  self.add('dialogue',part,source,{'messages':m,'source':source,'meta':meta},keys,priority)
 def intent(self,s,part,source,meta,intent,slots):
  s=clean(s)
  if not s or not ru(s):self.count[source+':filtered']+=1;return
  self.add('intent',part,source,{'text':s,'intent':intent,'slots':slots,'source':source,'meta':meta},[prompt_key(s),'text:'+h(norm(s))])
 def finish(self,out):
  self.db.commit();say('Removing exact duplicates and train/holdout collisions...')
  self.db.executescript('''CREATE INDEX rec_f ON records(fingerprint); CREATE INDEX rec_s ON records(split);
 CREATE TABLE excluded(id INTEGER PRIMARY KEY);
 -- Do not turn previously used base training records into a new evaluation set.
 INSERT OR IGNORE INTO excluded SELECT DISTINCT rid FROM keys JOIN protected_train USING(key) JOIN records ON records.id=rid WHERE split!='train' AND source NOT LIKE 'r54:%';
 -- Exclude conflicting external intent annotations rather than arbitrarily choosing one.
 INSERT OR IGNORE INTO excluded SELECT DISTINCT k.rid FROM keys k JOIN intent_labels i ON i.rid=k.rid JOIN (SELECT key FROM keys JOIN intent_labels ON keys.rid=intent_labels.rid WHERE key LIKE 'prompt:%' GROUP BY key HAVING COUNT(DISTINCT label)>1) bad USING(key);
 INSERT OR IGNORE INTO locked SELECT DISTINCT key FROM keys JOIN records ON rid=records.id WHERE split!='train' AND rid NOT IN (SELECT id FROM excluded);
 INSERT OR IGNORE INTO excluded SELECT DISTINCT rid FROM keys JOIN locked USING(key) JOIN records ON records.id=rid WHERE split='train';
 -- Prevent shared keys in different new evaluation splits, highest priority wins.
 CREATE TABLE holdout_priority AS SELECT key,MIN(CASE split WHEN 'test' THEN 0 WHEN 'calibration' THEN 1 ELSE 2 END) AS p FROM keys JOIN records ON rid=records.id WHERE split!='train' AND rid NOT IN (SELECT id FROM excluded) GROUP BY key;
 CREATE INDEX holdout_key ON holdout_priority(key);
 INSERT OR IGNORE INTO excluded SELECT DISTINCT rid FROM keys JOIN records ON records.id=rid JOIN holdout_priority USING(key) WHERE split!='train' AND CASE split WHEN 'test' THEN 0 WHEN 'calibration' THEN 1 ELSE 2 END > p;
 INSERT OR IGNORE INTO excluded SELECT id FROM (SELECT id,ROW_NUMBER() OVER(PARTITION BY fingerprint ORDER BY CASE split WHEN 'test' THEN 0 WHEN 'calibration' THEN 1 WHEN 'validation' THEN 2 ELSE 3 END,priority DESC,id) AS n FROM records WHERE id NOT IN (SELECT id FROM excluded)) WHERE n>1;''')
  self.db.commit();counts=collections.Counter(); handles={}
  try:
   for kind,part,source,payload in self.db.execute('SELECT kind,split,source,payload FROM records WHERE id NOT IN (SELECT id FROM excluded) ORDER BY id'):
    key=(kind,part)
    if key not in handles:
     p=out/kind/(part+'.jsonl');p.parent.mkdir(exist_ok=True);handles[key]=p.open('w',encoding='utf-8',newline='\n')
    handles[key].write(payload+'\n');counts[f'{kind}/{part}/{source}']+=1
  finally:
   for f in handles.values():f.close()
  n=self.db.execute('SELECT COUNT(*) FROM excluded').fetchone()[0]
  return dict(counts),n

def base_import(st,base,out):
 if sha(base)!=BASE_SHA:raise ValueError('Base archive differs from pinned original')
 with zipfile.ZipFile(base) as z:
  names=z.namelist(); mf=next(n for n in names if n.endswith('/SHA256SUMS.txt')); prefix=mf[:-len('SHA256SUMS.txt')]
  listed=set()
  for line in z.read(mf).decode('utf-8').splitlines():
   digest,name=line.split(maxsplit=1); name=name.lstrip('*'); full=prefix+name
   if full in listed or Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name or ':' in name:raise ValueError('Invalid base manifest path')
   listed.add(full); data=z.read(full)
   if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Base hash mismatch: '+name)
  if len(names)!=len(set(names)) or listed!={n for n in names if not n.endswith('/') and n!=mf}:raise ValueError('Base manifest coverage mismatch')
  say('Original R5.4 archive manifest verified')
  # Preserve the aligned original model-visible, teacher and trace files separately.
  for n in names:
   if not n.startswith(prefix):continue
   rel=n[len(prefix):]; p=Path(rel)
   if not rel or n.endswith('/'):continue
   if p.is_absolute() or '..' in p.parts or '\\' in rel or ':' in rel:raise ValueError('Unsafe archive path')
   if rel.startswith(('episodes/','licenses/','literature/','language/','tools/','evidence/','extension_source/')) or rel in ('SOURCES_RU.md','manifest.json','README_RU.md','SHA256SUMS.txt'):
    dest=out/'r54_original'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
  for part in SPLITS:
   n=prefix+'language/'+part+'.jsonl'
   if n in names:
    for r in rows(z.open(n)):
     t=r.get('turns',[])
     if part!='train':
      for prompt in t[::2]:st.lock(prompt_key(prompt))
     meta={k:v for k,v in r.items() if k!='turns'}
     if r.get('source')==EVERYDAY:
      # Human-human dialogue is language material, not assistant instruction supervision.
      st.lang('\n'.join(t),part,'r54:'+EVERYDAY,dict(meta,genre='human_dialogue'))
     else:st.chat([('user' if i%2==0 else 'assistant',s) for i,s in enumerate(t)],part,'r54:'+r.get('source','unknown'),meta,10)
   n=prefix+'episodes/model_visible/'+part+'.jsonl'
   if part!='train' and n in names:
    for r in rows(z.open(n)):
     for e in r.get('events',[]):
      if e.get('kind')=='owner_text' and e.get('text'):st.lock(prompt_key(e['text']))
  n=prefix+'language/pretrain.train.jsonl'
  if n in names:
   for r in rows(z.open(n)):st.lang(r.get('text'),'train','r54:pretrain',{k:v for k,v in r.items() if k!='text'})
  # Literature is language modeling, not assistant supervision; preserve existing heldouts.
  for part in ('train','validation','test'):
   for kind in ('language','dialogues'):
    n=prefix+f'literature/{kind}/{part}.jsonl'
    if n not in names:continue
    for r in rows(z.open(n)):
     t=r.get('text')
     if not isinstance(t,str):
      if kind!='dialogues' or not isinstance(r.get('turns'),list):raise ValueError('Unexpected literature schema')
      t='\n'.join(x['speaker']+': '+x['text'] for x in r['turns'])
     meta={k:v for k,v in r.items() if k not in ('text','turns')}
     meta['work_key']='legacy:'+r['work_id'];meta['genre']=kind
     st.lang(t,part,'r54:literature',meta)

def oasst(st,p,raw):
 def good(n):
  if n.get('lang','ru')!='ru' or n.get('deleted') or n.get('review_result') is False or n.get('synthetic') is True:return False
  lab=n.get('labels') or {}
  if isinstance(lab,list):lab={x.get('name'):x.get('value') for x in lab if isinstance(x,dict)}
  elif isinstance(lab,dict) and isinstance(lab.get('name'),list):lab=dict(zip(lab['name'],lab.get('value',[])))
  if isinstance(lab,dict):
   for k in ('pii','spam','lang_mismatch'):
    v=lab.get(k) or {}; v=v.get('value',0) if isinstance(v,dict) else v
    if isinstance(v,(int,float)) and v>=.5:return False
  return bool(clean(n.get('text')))
 def best(n,depth=0):
  if depth>=64 or not good(n):return []
  role={'prompter':'user','user':'user','assistant':'assistant'}.get(n.get('role'))
  if not role:return []
  replies=sorted(n.get('replies') or [],key=lambda x:(x.get('rank') is None,x.get('rank') if x.get('rank') is not None else 999,str(x.get('message_id',''))))
  branch=[]
  for c in replies:
   branch=best(c,depth+1)
   if branch:break
  return [(role,n['text'])]+branch
 with (gzip.open(p,'rt',encoding='utf-8') if raw else p.open(encoding='utf-8')) as f:
  for i,r in enumerate(rows(f)):
   if raw:
    n=r.get('prompt')
    if not isinstance(n,dict):raise ValueError('Unexpected OASST tree format')
    t=best(n); uid=r.get('message_tree_id',str(i))
   else:
    m=r.get('messages',r.get('conversation',r.get('dialogue',r.get('conversations',r.get('turns')))))
    if not isinstance(m,list):raise ValueError('Unsupported OASST RU schema; use original trees archive')
    t=[]
    for j,x in enumerate(m):
     if isinstance(x,str):t.append(('user' if j%2==0 else 'assistant',x));continue
     role=x.get('role',x.get('from')); role={'prompter':'user','human':'user','gpt':'assistant','bot':'assistant'}.get(role,role)
     t.append((role,x.get('content',x.get('text',x.get('value')))))
    uid=r.get('id',str(i))
   if t:st.chat(t,split('prompt:'+norm(t[0][1])),'oasst2',{'id':uid,'file':p.name,'license':'Apache-2.0','derived':not raw,'rights_status':'RESEARCH_ONLY_CONTRIBUTOR_RIGHTS_UNRESOLVED'})

def aya(st,p):
 for i,r in enumerate(parquet_rows(p,('inputs','targets','language_code','annotation_type'),('user_id',))):
  if str(r['language_code']).lower() not in ('ru','rus','ru-ru') or str(r['annotation_type']).replace('_','-')!='original-annotations':continue
  a,b=r['inputs'],r['targets'];
  if not isinstance(a,str) or not isinstance(b,str):continue
  group='aya-contributor:'+str(r['user_id']) if r.get('user_id') else 'prompt:'+norm(a)
  st.chat([('user',a),('assistant',b)],split(group),'aya',{'row':i,'file':p.name,'license':'Apache-2.0','annotation_type':r['annotation_type']})

def massive(st,p):
 part='validation' if 'validation' in p.name.lower() or 'dev' in p.name.lower() else 'test' if 'test' in p.name.lower() else 'train' if 'train' in p.name.lower() else None
 if part is None:raise ValueError('MASSIVE split not recognized: '+p.name)
 for r in parquet_rows(p,('id','utt','intent','annot_utt'),('locale','scenario','partition','judgments')):
  if r.get('locale','ru-RU')!='ru-RU':continue
  if not isinstance(r['intent'],str) or not r['intent']:raise ValueError('MASSIVE intent labels unresolved; metadata required')
  declared=r.get('partition'); declared={'dev':'validation','val':'validation'}.get(declared,declared)
  if declared in SPLITS and declared!=part:raise ValueError('MASSIVE filename/partition mismatch: '+p.name)
  if not r['intent'].startswith(INTENT_PREFIXES) or r['intent'] in INTENT_EXCLUDED:
   st.count['massive:out_of_scope']+=1;continue
  judges=r.get('judgments')
  # Arrow represents list-of-struct either as rows or columns, depending on exporter.
  if isinstance(judges,dict):
   fields=('language_identification','intent_score','slots_score','grammar_score','spelling_score')
   if not all(isinstance(judges.get(k),list) for k in fields) or len({len(judges[k]) for k in fields})!=1:judges=[]
   else:judges=[dict(zip(fields,vals)) for vals in zip(*(judges[k] for k in fields))]
  vote=sum(j.get('language_identification')=='target' and j.get('intent_score')==1 and j.get('slots_score')==1 and isinstance(j.get('grammar_score'),(int,float)) and j['grammar_score']>=3 and isinstance(j.get('spelling_score'),(int,float)) and j['spelling_score']>=1 for j in judges if isinstance(j,dict)) if isinstance(judges,list) else 0
  if vote<2:st.count['massive:quality_votes']+=1;continue
  annotated=clean(r['annot_utt']);bare=SLOT.sub(lambda m:m.group(2),annotated)
  slots=[{'name':m.group(1),'value':m.group(2)} for m in SLOT.finditer(annotated)]
  if not annotated or norm(bare)!=norm(clean(r['utt'])) or '[' in bare or ']' in bare or any(x['name'] in SENSITIVE_SLOTS for x in slots):
   st.count['massive:alignment_or_sensitive']+=1;continue
  st.intent(r['utt'],part,'massive',{'id':str(r['id']),'file':p.name,'license':'CC-BY-4.0','scenario':r.get('scenario'),'annotated_utterance':annotated,'quality_votes':vote},r['intent'],slots)

def pd(st,p,cap):
 size=0
 for i,r in enumerate(parquet_rows(p,('text','identifier','creator','title'),('publication_date',))):
  text=r['text'];
  if not isinstance(text,str):continue
  metrics,reject,flags=pd_gate.quality(text)
  if reject or any(x.startswith('privacy_review:') for x in flags) or not isinstance(r.get('publication_date'),int) or not 1000<=r['publication_date']<1884 or not r.get('identifier') or not r.get('title'):
   st.count['russian_pd:quality_or_rights_pending']+=1;continue
  group=norm(str(r['creator'])+' '+str(r['title'])); part=split('work:'+group)
  meta={k:r[k] for k in r if k not in ('text','_physical_row')};meta.update(file=p.name,row=r.get('_physical_row',i),work_key=h(group),rights='public-domain claimed; work-level verification pending',quality=metrics,flags=flags)
  # Limit excerpts per work to avoid domination by a single long book.
  for j,s in enumerate(chunks(text[:131072])):
   if len(s)<80:continue
   if st.lang(s,part,'russian_pd',dict(meta,chunk=j)):size+=len(s.encode('utf-8'))
   if cap and size>=cap:return

def reviewed_pd(st,folder,out):
 manifest=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
 if manifest.get('version')!=pd_gate.VERSION:raise ValueError('Unsupported reviewed PD manifest')
 for f,part in [('train.jsonl','train'),('dev.jsonl','validation'),('test.jsonl','test')]:
  p=folder/f
  if sha(p)!=manifest['files'][f]:raise ValueError('Reviewed PD file checksum mismatch: '+f)
  with p.open(encoding='utf8') as stream:
   for row in rows(stream):
    rev=row['review']; text=row['text']
    if h(text)!=row['text_sha256'] or not all(rev.get(k) for k in ('reviewer','rights_evidence','markets','rights_basis','work_key')) or any(rev.get(k,'').upper()!='YES' for k in ('privacy_checked','quality_checked')):raise ValueError('Incomplete reviewed PD record')
    meta={k:v for k,v in row.items() if k!='text'};meta['work_key']=row['work_group']
    for j,t in enumerate(chunks(text)):
     if len(t)>=80:st.lang(t,part,'russian_pd_reviewed',dict(meta,chunk=j))
 shutil.copyfile(folder/'manifest.json',out/'reviewed_pd_manifest.json')

def tatoeba(st,p):
 with (bz2.open(p,'rt',encoding='utf-8') if p.suffix=='.bz2' else p.open(encoding='utf-8')) as f:
  for line in f:
   r=line.rstrip('\r\n').split('\t')
   if len(r)<6:raise ValueError('Unexpected Tatoeba detailed TSV format')
   if r[1]!='rus':continue
   st.lang(r[2],split('sentence:'+norm(r[2])),'tatoeba',{'id':r[0],'attribution':r[3],'url':'https://tatoeba.org/en/sentences/show/'+r[0],'license':'CC-BY-2.0-FR'})

def legacy_tokenizer(out):
 raw=(HERE/'legacy_tokenizer.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=LEGACY_SHA:raise ValueError('Legacy B2 tokenizer changed')
 spec=json.loads(raw); active=spec['active_ids']; known={i:bytes([i]) for i in range(256)}
 for a,b,c in spec['merges']:
  if c in known or a not in known or b not in known:raise ValueError('Invalid merge')
  known[c]=known[a]+known[b]
 if len(active)!=514 or set(active)!=set(known)|{spec['bos'],spec['eos']} or any(bytes.fromhex(spec['tokens_hex'][str(i)])!=v for i,v in known.items()):raise ValueError('Legacy tokenizer mapping mismatch')
 (out/'tokenizer.json').write_bytes(raw)
 return {'format':'UNO B2 original','active_vocab':len(active),'sha256':LEGACY_SHA,'compatible_token_ids_with_old_weights':True,'checkpoint_resume':False,'note':'Old F 514 dense IDs; RTX GRU 517 with role IDs 514..516 added by trainer. New corpus requires trainer input adaptation and new lineage.'}

def tokenize(out,vocab):
 from tokenizers import Tokenizer,models,trainers,pre_tokenizers,decoders
 t=Tokenizer(models.BPE(unk_token='<unk>')); t.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False);t.decoder=decoders.ByteLevel()
 def it():
  for kind in ('language','dialogue','intent'):
   p=out/kind/'train.jsonl'
   if not p.exists():continue
   for r in rows(p.open(encoding='utf-8')):
    if kind=='dialogue':
     for m in r['messages']:yield m['text']
    else:yield r['text']
 trainer=trainers.BpeTrainer(vocab_size=vocab,min_frequency=2,special_tokens=SPECIAL,initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),show_progress=True)
 t.train_from_iterator(it(),trainer=trainer);t.save(str(out/'tokenizer.json'))
 for s in ('Привет, мир!','Ёжик, 42 °C','Не выключай Wi-Fi.','Строка\nс пробелами'):
  if t.decode(t.encode(s).ids)!=s:raise ValueError('Tokenizer roundtrip failed')
 return {'vocab':t.get_vocab_size(),'special_ids':{s:t.token_to_id(s) for s in SPECIAL},'sha256':sha(out/'tokenizer.json'),'training_split':'train only','compatible_with_old_weights':False}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(r'D:\UNO'));ap.add_argument('--input',type=Path);ap.add_argument('--base',type=Path,default=Path(__file__).with_name('UNO_R54_RU_DATA_EXPANDED_20261128.zip'));ap.add_argument('--output',type=Path);ap.add_argument('--language-mib',type=int,default=128,help='Russian-PD total cap; 0 = all works, capped per work');ap.add_argument('--vocab',type=int,default=8192);ap.add_argument('--new-tokenizer',action='store_true',help='Explicit incompatible new tokenizer, from scratch only');ap.add_argument('--research-pd',action='store_true',help='Include hash-checked but rights-pending PD excerpts for research only');ap.add_argument('--reviewed-pd',type=Path,help='Existing UNO Russian-PD Preparer EXPORT directory');ap.add_argument('--skip-tokenizer',action='store_true');ap.add_argument('--no-install',action='store_true');a=ap.parse_args()
 root=a.root.resolve();inp=(a.input or root/'datasets').resolve();out=(a.output or root/'corpus_prepared_v4').resolve()
 if a.language_mib<0 or not 512<=a.vocab<=32768:raise ValueError('Bad cap or vocab')
 for p in (inp,out,a.base.resolve()):
  if not p.is_relative_to(root):raise ValueError('All inputs and output must be inside UNO root: '+str(p))
 if not inp.is_dir():raise FileNotFoundError(inp)
 if out.is_relative_to(inp) or inp.is_relative_to(out):raise ValueError('Input and output directories must be separate')
 if out.exists():raise FileExistsError(str(out)+' already exists; use --output with a new path')
 stage=out.with_name(out.name+'.building')
 if stage.exists():raise FileExistsError(str(stage)+' exists after previous attempt; preserve it and use a new --output')
 files=find_input(inp);say(dump({k:[str(p.relative_to(root)) for p in v] for k,v in files.items()}))
 if not any(files[k] for k in files if k!='taskmaster') and not a.reviewed_pd:raise ValueError('No supported downloaded Russian data found in '+str(inp))
 if a.skip_tokenizer and a.new_tokenizer:raise ValueError('Conflicting tokenizer flags')
 if not a.no_install:ensure_deps(root,bool(files['aya'] or files['massive'] or (a.research_pd and files['russian_pd'])),a.new_tokenizer)
 else:
  sys.path.insert(0,str(HERE/'deps'))
  if files['aya'] or files['massive'] or (a.research_pd and files['russian_pd']):
   import pyarrow.parquet
  if a.new_tokenizer:import tokenizers
 if a.reviewed_pd and not a.reviewed_pd.resolve().is_relative_to(root):raise ValueError('Reviewed PD export must be inside UNO')
 stage.mkdir(parents=True);start=time.time();st=Store(stage);base_import(st,a.base,stage)
 holdout_path=HERE/'legacy_holdout_prompts.json'
 if sha(holdout_path)!=HOLDOUT_SHA:raise ValueError('Historical holdout list hash mismatch')
 holdouts=json.loads(holdout_path.read_text(encoding='utf8'))
 if len(holdouts)!=555 or not all(isinstance(x,str) for x in holdouts):raise ValueError('Historical holdout list invalid')
 for prompt in holdouts:st.lock(prompt_key(prompt))
 report={'schema':'UNO-CORPUS-PREP/4','status':'RESEARCH_CORPUS_NOT_COMMERCIAL_APPROVAL','sources':SOURCES,'base_sha256':sha(a.base),'legacy_locked_prompts':555,'pd_research_unreviewed':a.research_pd,'input_files':[],'missing':[],'not_imported':[],'warnings':['PII filtering is heuristic, not anonymization proof','Exact normalized duplicates/prompt overlaps only; semantic leakage not ruled out','Russian-PD individual works require rights review','Original R5.4 episode files preserved separately; do not feed teacher/future events as model inputs','Legacy tokenizer retained by default; explicit new tokenizer requires new weights or migration','OASST2 contributor commercial rights unresolved; research only, even with Apache-2.0 label','Previously used training data are not new independent evaluation examples','Not yet integrated into F/GRU trainer','MASSIVE source ontology mapping is required before training action heads']}
 def run(key,fn,paths):
  if not paths:report['missing'].append(key);return
  seen=set()
  for p in paths:
   say('Reading '+p.name);d=sha(p)
   if d in seen:continue
   seen.add(d);before=st.i
   if key=='russian_pd':
    name=re.sub(r' \(\d+\)(?=\.parquet$)','',p.name.lower())
    if pd_gate.EXPECTED.get(name)!=d:raise ValueError('Russian-PD official hash mismatch: '+p.name)
   fn(p)
   if st.i==before:say('WARNING: no accepted records from '+p.name)
   report['input_files'].append({'source':key,'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':d,'candidates':st.i-before})
 run('oasst2',lambda p:oasst(st,p,bool(files['oasst_raw'])),files['oasst_raw'] or files['oasst_ru'])
 if files['oasst_raw'] and files['oasst_ru']:report['not_imported'].append('OASST derived subset skipped because original used')
 run('aya',lambda p:aya(st,p),files['aya']);run('massive',lambda p:massive(st,p),files['massive'])
 cap=0 if not a.language_mib else max(1,a.language_mib*1024*1024//max(1,len(files['russian_pd'])))
 if a.research_pd:
  run('russian_pd',lambda p:pd(st,p,cap),files['russian_pd'])
 else:
  report['not_imported'].extend({'source':'russian_pd','file':p.name,'reason':'Pending rights review; existing PD Preparer gate retained'} for p in files['russian_pd'])
 if a.reviewed_pd: reviewed_pd(st,a.reviewed_pd,stage)
 run('tatoeba',lambda p:tatoeba(st,p),files['tatoeba'])
 for p in files['taskmaster']:
  with zipfile.ZipFile(p) as z: n=len(z.namelist())
  report['not_imported'].append({'source':'taskmaster','file':p.name,'sha256':sha(p),'zip_entries':n,'reason':'English; translation and rights review required'})
 report['counts'],report['excluded_exact_or_holdout']=st.finish(stage); report['filtered']=dict(st.count)
 report['external_train_rows']=sum(n for k,n in report['counts'].items() if '/train/' in k and not k.split('/',2)[2].startswith('r54:'))
 if not report['external_train_rows']:raise ValueError('No new external training rows accepted; inspect .building directory, do not use as expanded corpus')
 # Original aligned episode train records additionally screened against all known holdout prompts.
 base=stage/'r54_original'/'episodes'; dst=stage/'r54_episode_train';dst.mkdir()
 allowed=set(); removed=0
 everyday_ids={r['id'] for r in rows((stage/'r54_original'/'language'/'train.jsonl').open(encoding='utf-8')) if r.get('source')==EVERYDAY}
 with (base/'model_visible'/'train.jsonl').open(encoding='utf-8') as f:
  for r in rows(f):
   if r['episode_id'] in everyday_ids:continue
   keys=[prompt_key(e['text']) for e in r.get('events',[]) if e.get('kind')=='owner_text' and isinstance(e.get('text'),str)]
   if any(st.db.execute('SELECT 1 FROM locked WHERE key=?',(k,)).fetchone() for k in keys):removed+=1;continue
   allowed.add(r['episode_id'])
 filtered_ids={}
 for kind in ('model_visible','teacher','simulator_trace'):
  kept=set()
  with (base/kind/'train.jsonl').open(encoding='utf-8') as f,(dst/(kind+'.jsonl')).open('w',encoding='utf-8',newline='\n') as g:
   for r in rows(f):
    if r['episode_id'] in allowed:
     if r['episode_id'] in kept:raise ValueError('Duplicate episode ID in '+kind)
     kept.add(r['episode_id']);g.write(dump(r)+'\n')
  filtered_ids[kind]=kept
 if filtered_ids['model_visible']!=allowed or filtered_ids['teacher']!=allowed or not filtered_ids['simulator_trace']<=allowed:raise ValueError('Filtered episode alignment failed')
 # Independently check the DB result before dropping its temporary index.
 cross=st.db.execute('''SELECT k.key FROM keys k JOIN records r ON r.id=k.rid WHERE r.id NOT IN (SELECT id FROM excluded) GROUP BY k.key HAVING COUNT(DISTINCT r.split)>1 LIMIT 1''').fetchone()
 if cross:raise ValueError('Retained cross-split key collision: '+cross[0])
 report['retained_cross_split_keys']=0
 report['r54_train_episodes']={'kept':len(allowed),'simulator_trace':len(filtered_ids['simulator_trace']),'excluded_holdout_prompt':removed,'excluded_human_dialogue_not_assistant':len(everyday_ids)};st.db.close()
 for name in ('index.sqlite','index.sqlite-wal','index.sqlite-shm'):
  p=stage/name
  if p.exists():p.unlink()
 if a.new_tokenizer:
  say('Training explicitly requested incompatible byte BPE tokenizer...');report['tokenizer']=tokenize(stage,a.vocab)
 elif not a.skip_tokenizer:report['tokenizer']=legacy_tokenizer(stage)
 else:report['tokenizer']='SKIPPED'
 report['parquet_group_events']=PARQUET_GROUP_EVENTS;report['seconds']=round(time.time()-start,1);report['russian_pd_cap_mib']=a.language_mib
 (stage/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 (stage/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in sorted(stage.rglob('*')) if p.is_file()),encoding='utf-8')
 stage.rename(out);say('DONE: '+str(out));say(dump(report['counts']));say('See report.json; original files unchanged.')
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback;traceback.print_exc();sys.exit(1)
