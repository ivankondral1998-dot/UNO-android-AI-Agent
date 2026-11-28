"""Deterministic byte BPE trained only on training works. Tiny research vocab.
Byte ids 0..255, BOS/EOS 256/257; unused 258..511 reserved, merges >=512.
All 32768 embedding slots allocated. Invalid/unbuilt ids excluded from language softmax.
"""
import collections,json,pathlib,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
FILES={'train':['good.txt','ram.txt'],'dev':['questions.txt'],'reserved':['storm.txt']}
REFS={'good.txt':'48052742e5512238dd0e13b0a834f35b9ca8e760','ram.txt':'c46e30a0d43a8468c0eff530ed9a4dfe8fa485aa','questions.txt':'8ffe642c553b434daede9208a57cab6dfaf0fc82','storm.txt':'ad5c9cccc8b7f5b5d711979349960eb558b8aa0d'}
PATHS={'good.txt':'prose/Chekhov/Добрый знакомый.txt','ram.txt':'prose/Chekhov/Баран и барышня.txt','questions.txt':'prose/Chekhov/Дополнительные вопросы.txt','storm.txt':'prose/Gorky/Песня о Буревестнике.txt'}
def sha(b):return hashlib.sha256(b).hexdigest()
def replace(seq,a,b,new):
 out=[];i=0
 while i<len(seq):
  if i+1<len(seq) and seq[i]==a and seq[i+1]==b:out.append(new);i+=2
  else:out.append(seq[i]);i+=1
 return out

def encode(b,merges):
 seq=list(b)
 for a,c,new in merges:seq=replace(seq,a,c,new)
 return seq

def prepare():
 docs={}
 for n,h in REFS.items():
  b=(ROOT/'corpus'/n).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h,n;b.decode('utf8');docs[n]=b
 # No training or tokenizer selection using reserved texts. Provenance hash only.
 seqs=[list(docs[n]) for n in FILES['train']];tokens={i:bytes([i]) for i in range(256)};merges=[]
 for new in range(512,768):
  c=collections.Counter(p for s in seqs for p in zip(s,s[1:]));
  if not c:break
  (a,b),count=min(c.items(),key=lambda kv:(-kv[1],tokens[kv[0][0]],tokens[kv[0][1]],kv[0]))
  if count<3:break
  tokens[new]=tokens[a]+tokens[b];merges.append((a,b,new));seqs=[replace(s,a,b,new) for s in seqs]
 out={'version':'research_byte_bpe_train_only_v1','allocated_vocab':32768,'bos':256,'eos':257,'merges':merges,'active_ids':list(range(258))+list(range(512,512+len(merges))), 'tokens_hex':{str(k):v.hex() for k,v in tokens.items()}}
 (ROOT/'tokenizer.json').write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2))
 ds={s:[[256]+encode(docs[n],merges)+[257] for n in FILES[s]] for s in ('train','dev')}
 for s,seqs in ds.items():
  for n,seq in zip(FILES[s],seqs):assert b''.join(tokens[i] for i in seq[1:-1])==docs[n]
 (ROOT/'data.json').write_text(json.dumps(ds,separators=(',',':')))
 m={'source':'https://github.com/d0rj/RusLit','tree':'4509680428729da225a73a22008133660f92bb7e','license_claim':'Repository declares original works public domain. Chekhov died 1904, Gorky 1936; exact original text rights still subject to local law and edition review before commercial use. Research only.','groups':FILES,'files':{n:{'path':PATHS[n],'git_blob_sha1':REFS[n],'sha256':sha(b),'bytes':len(b)} for n,b in docs.items()},'tokens':{s:sum(map(len,seqs)) for s,seqs in ds.items()},'reserved':'bytes hashed, never encoded or evaluated in pilot','active_vocab':len(out['active_ids']),'note':'four works only; two train, one dev, one reserved. Not sufficient for Russian language pretraining.'}
 (ROOT/'corpus_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(json.dumps(m,ensure_ascii=False))
if __name__=='__main__':prepare()
