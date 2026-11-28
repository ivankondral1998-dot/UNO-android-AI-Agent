"""Train-only byte BPE extension; original IDs and ranks remain unchanged."""
import argparse, collections, heapq, json, random, os
from pathlib import Path
from train_cuda_vocab04 import Codec, identity, sha, require, ROOT, TOK_SHA

def pairs(s): return collections.Counter(zip(s,s[1:]))
def merge(s,a,b,c):
 out=[];i=0
 while i<len(s):
  if i+1<len(s) and s[i]==a and s[i+1]==b:out.append(c);i+=2
  else:out.append(s[i]);i+=1
 return tuple(out)
def extend(base,chunks,target=4096,min_count=3):
 t=json.loads(json.dumps(base));freq=collections.Counter(chunks);seq=list(freq);weights=[freq[s] for s in seq];counts=collections.Counter();owners=collections.defaultdict(set);existing={(a,b) for a,b,c in t['merges']};occupied=set(t['active_ids']);free=iter(i for i in range(512,t['allocated_vocab']) if i not in occupied)
 for i,s in enumerate(seq):
  for p,n in pairs(s).items():counts[p]+=n*weights[i];owners[p].add(i)
 heap=[(-n,p) for p,n in counts.items() if n>=min_count and p not in existing];heapq.heapify(heap)
 while len(t['active_ids'])<target and heap:
  neg,p=heapq.heappop(heap)
  if -neg!=counts[p] or p in existing:continue
  if -neg<min_count:break
  a,b=p;c=next(free);t['merges'].append([a,b,c]);t['active_ids'].append(c);t['tokens_hex'][str(c)]=t['tokens_hex'][str(a)]+t['tokens_hex'][str(b)];existing.add(p);changed=set()
  for i in sorted(owners[p]):
   old=seq[i];new=merge(old,a,b,c);before=pairs(old);after=pairs(new);seq[i]=new
   for q in before.keys()|after.keys():
    delta=(after[q]-before[q])*weights[i]
    if delta:counts[q]+=delta;changed.add(q)
    if not after[q]:owners[q].discard(i)
    else:owners[q].add(i)
  for q in changed:
   if counts[q]>=min_count and q not in existing:heapq.heappush(heap,(-counts[q],q))
 t['active_ids'].sort();return t

def texts(path,kind,count,seed):
 rng=random.Random(seed);sample=[]
 with path.open(encoding='utf8') as f:
  for i,line in enumerate(f):
   if i<count:sample.append(line)
   else:
    j=rng.randrange(i+1)
    if j<count:sample[j]=line
 for line in sample:
  r=json.loads(line)
  if kind=='language':yield r['text']
  else:
   for m in r['messages']:yield m['text']
def validate_extension(t,base,digest):
 require(t['allocated_vocab']==32768 and t['bos']==base['bos'] and t['eos']==base['eos'],'EXT_ABI');require(t['merges'][:len(base['merges'])]==base['merges'],'EXT_RULE_PREFIX');require(t['extension']['parent_sha256']==TOK_SHA and t['extension']['corpus_manifest_sha256']==digest,'EXT_LINEAGE');known={int(k):v for k,v in base['tokens_hex'].items()};ids=set(base['active_ids']);seen={(a,b) for a,b,c in base['merges']}
 for a,b,c in t['merges'][len(base['merges']):]:
  require(a in known and b in known and c not in ids and 512<=c<32768 and (a,b) not in seen,'EXT_RULE');known[c]=known[a]+known[b];ids.add(c);seen.add((a,b))
 require(t['active_ids']==sorted(ids) and t['tokens_hex']=={str(k):v for k,v in known.items()},'EXT_TOKEN_TABLE')
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--target',type=int,default=4096);p.add_argument('--sample-records',type=int,default=3000);a=p.parse_args();require(514<a.target<=32514 and 100<=a.sample_records<=20000,'BOUNDS');require(not a.out.exists(),'OUTPUT_EXISTS');digest=identity(a.data);codec=Codec();base=json.loads((ROOT/'tokenizer.json').read_text());chunks=[];budget=350000
 for kind,n in [('dialogue',max(100,a.sample_records//3)),('language',a.sample_records)]:
  limit=budget//3 if kind=='dialogue' else budget;used=0
  for s in texts(a.data/kind/'train.jsonl',kind,n,243):
   ids=codec.encode(s[:8192]);ids=ids[:max(0,limit-used)];used+=len(ids);chunks.extend(tuple(ids[i:i+48]) for i in range(0,len(ids),48) if len(ids[i:i+48])>=2)
   if used>=limit:break
 t=extend(base,chunks,a.target);t['extension']={'parent_sha256':TOK_SHA,'corpus_manifest_sha256':digest,'algorithm':'incremental weighted byte-pair v04','sample_records':a.sample_records,'sample_chunks':len(chunks),'target':a.target};validate_extension(t,base,digest);a.out.parent.mkdir(parents=True,exist_ok=True);tmp=a.out.with_suffix('.tmp');tmp.write_text(json.dumps(t,ensure_ascii=False,sort_keys=True),encoding='utf8');os.replace(tmp,a.out);print(json.dumps({'active':len(t['active_ids']),'sha256':sha(a.out),'chunks':len(chunks)},ensure_ascii=False))
if __name__=='__main__':main()
