#!/usr/bin/env python3
"""UNO R4.1 precode isolated exact-memory integrity laboratory, not production.
Real A52 native S5 background computation; synthetic bytes only; no P training.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import re
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_EXACT_MEMORY_INTEGRITY_V14'
MIB=1048576
MAX_SLOTS=4  # fixture limit; normative full-store upper bound is 4096
MAX_PAYLOAD=4096
MAX_QUERY_BYTES=4096
MAX_CONDITIONS=16
MODEL_A=hashlib.sha256(b'fixture-model-a').digest()
MODEL_B=hashlib.sha256(b'fixture-model-b').digest()
MODES=(
 'EXACT_BYTE_MATCH','NEAR_TEXT_NOT_EXACT','CORRUPT_PAYLOAD_UNAVAILABLE',
 'CORRUPT_HEADER_UNAVAILABLE','MODEL_VERSION_QUARANTINE','BOOT_EPOCH_QUARANTINE','STALE_SLOT_GENERATION',
 'STABLE_PAGE_WALK','CURSOR_INVALID_AFTER_MUTATION','CURSOR_INVALID_AFTER_CONSENT',
 'CURSOR_INVALID_AFTER_QUERY_CHANGE','CURSOR_INVALID_AFTER_MODEL_CHANGE',
 'CURSOR_EXPIRED_DEADLINE',
 'TRUNCATED_REQUIRES_FULL_SCAN','ALL_PINNED_DENIED_STORAGE','CRASH_BEFORE_COMMIT',
 'INVALID_QUERY_REJECTED','REVOKED_CONSENT_DENIES')

def get_number(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:mem=int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])
    except (OSError,StopIteration,ValueError,IndexError):mem=None
    return get_number('/sys/class/power_supply/battery/capacity'),get_number('/sys/class/power_supply/battery/temp'),mem

def safety(smoke):
    if smoke:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100<=t<=800:return 'TELEMETRY_UNAVAILABLE'
    if b<40:return 'BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'MEMAVAILABLE_BELOW_400000_KB'
    return None

def native_binary():
    p=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('MISSING_NATIVE_S5_BINARY '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=10)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_S5_PRECHECK_FAILED '+r.stdout[-220:])
    return p

def s5_worker(binary,stop,ready,out):
    vals=[];errs=[]
    try:
        while not stop.is_set():
            r=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=10)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
                raise RuntimeError('NATIVE_S5_COMPUTE_FAILED')
            found=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not found:raise RuntimeError('NATIVE_S5_METRIC_MISSING')
            vals.append(float(found[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=3)
    except BaseException as e:errs.append(str(e)[:150])
    try:out.put((os.getpid(),len(vals),statistics.mean(vals) if vals else 0.0,min(vals) if vals else 0.0,errs),timeout=3)
    except BaseException:pass

def ram_holder(stop,ready,mib=32):
    try:
        b=bytearray(mib*MIB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(True,timeout=5)
        while not stop.wait(.15):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def connect(path):
    c=sqlite3.connect(str(path),timeout=7,isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    c.execute('PRAGMA busy_timeout=5000')
    return c

def init_store(path):
    c=connect(path)
    c.execute('CREATE TABLE meta (name TEXT PRIMARY KEY, val TEXT NOT NULL)')
    c.execute('CREATE TABLE records (slot INTEGER PRIMARY KEY, generation INTEGER NOT NULL, record_id INTEGER NOT NULL UNIQUE, '
              'payload BLOB NOT NULL, payload_sha BLOB NOT NULL, header BLOB NOT NULL, model_digest BLOB NOT NULL, '
              'kind INTEGER NOT NULL, source_id INTEGER NOT NULL, schema_id INTEGER NOT NULL, source_sequence INTEGER NOT NULL, '
              'time_scope TEXT NOT NULL, pinned INTEGER NOT NULL, boot_epoch INTEGER NOT NULL, consent_epoch INTEGER NOT NULL)')
    for key,val in [('snapshot','1'),('boot','1'),('consent','1'),('consent_granted','1'),('model',MODEL_A.hex())]:
        c.execute('INSERT INTO meta VALUES (?,?)',(key,val))
    return c

def meta(c,key):return c.execute('SELECT val FROM meta WHERE name=?',(key,)).fetchone()[0]
def bump(c,key):
    v=int(meta(c,key))+1
    c.execute('UPDATE meta SET val=? WHERE name=?',(str(v),key))
    return v

def header_bytes(slot,gen,rid,seq):
    buf=bytearray(64)
    struct.pack_into('<Q',buf,0,rid)
    struct.pack_into('<I',buf,8,slot)
    struct.pack_into('<I',buf,12,gen)
    struct.pack_into('<Q',buf,16,80+rid)  # synthetic provenance id, NOT authenticated
    struct.pack_into('<Q',buf,24,1000000000+rid)
    struct.pack_into('<Q',buf,32,2000000000+rid)
    struct.pack_into('<I',buf,40,0)  # manifest model-table index
    struct.pack_into('<H',buf,44,1)  # kind
    struct.pack_into('<H',buf,46,0)
    struct.pack_into('<Q',buf,48,1)
    struct.pack_into('<Q',buf,56,seq)
    return bytes(buf)

def add(c,slot,rid,payload,gen=1,pinned=False,seq=1):
    if not isinstance(payload,bytes) or len(payload)>MAX_PAYLOAD:return 'INVALID_PAYLOAD'
    if not 0<=slot<MAX_SLOTS or gen<1 or gen>=2**32:return 'INVALID_SLOT'
    if c.execute('SELECT COUNT(*) FROM records').fetchone()[0]>=MAX_SLOTS:return 'DENIED_STORAGE'
    c.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
        slot,gen,rid,payload,hashlib.sha256(payload).digest(),header_bytes(slot,gen,rid,seq),
        bytes.fromhex(meta(c,'model')),1,3,7,seq,'lab_scope',int(pinned),int(meta(c,'boot')),int(meta(c,'consent'))))
    bump(c,'snapshot')
    return 'INSERTED'

def validate_record(r):
    slot,gen,rid,payload,sha,head,model,kind,source,schema,seq,scope,pinned,boot,consent=r
    if len(head)!=64 or len(payload)>MAX_PAYLOAD or len(sha)!=32 or len(model)!=32:return False
    if hashlib.sha256(payload).digest()!=sha:return False
    if struct.unpack_from('<Q',head,0)[0]!=rid or struct.unpack_from('<I',head,8)[0]!=slot:return False
    if struct.unpack_from('<I',head,12)[0]!=gen or struct.unpack_from('<Q',head,56)[0]!=seq:return False
    if struct.unpack_from('<H',head,44)[0]!=kind:return False
    if struct.unpack_from('<Q',head,16)[0]!=80+rid:return False
    if struct.unpack_from('<Q',head,24)[0]!=1000000000+rid:return False
    if struct.unpack_from('<Q',head,32)[0]!=2000000000+rid:return False
    if struct.unpack_from('<I',head,40)[0]!=0:return False
    if struct.unpack_from('<H',head,46)[0]!=0:return False
    if struct.unpack_from('<Q',head,48)[0]!=1:return False
    return True

ALLOWED={'record_id','kind','source_id','schema_id','source_sequence','time_scope','raw_literal'}
def validate_query(conditions):
    try:blob=json.dumps(conditions,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    except (ValueError,TypeError):return False
    if not isinstance(conditions,list) or len(conditions)>MAX_CONDITIONS or len(blob)>MAX_QUERY_BYTES:return False
    for d in conditions:
        if not isinstance(d,dict) or set(d)!={'field','op','value'} or d['field'] not in ALLOWED:return False
        fld,op,val=d['field'],d['op'],d['value']
        if fld=='raw_literal':
            if op!='contains' or not isinstance(val,str) or len(val.encode())>256:return False
        elif op=='eq':
            if not isinstance(val,(str,int)) or isinstance(val,bool):return False
        elif op=='in':
            if not isinstance(val,list) or not val or len(val)>64 or any(not isinstance(v,(str,int)) or isinstance(v,bool) for v in val):return False
        elif op=='range':
            if not isinstance(val,list) or len(val)!=2 or any(not isinstance(v,int) or isinstance(v,bool) for v in val):return False
            if val[0]>val[1]:return False
        else:return False
    return True

def cond(fld,op,val):return {'field':fld,'op':op,'value':val}
def row_matches(r,query):
    keys={'record_id':2,'kind':7,'source_id':8,'schema_id':9,'source_sequence':10,'time_scope':11}
    for item in query:
        fld,op,wanted=item['field'],item['op'],item['value']
        if fld=='raw_literal':
            if wanted.encode('utf8') not in r[3]:return False
        else:
            actual=r[keys[fld]]
            if op=='eq' and actual!=wanted:return False
            if op=='in' and actual not in wanted:return False
            if op=='range' and not wanted[0]<=actual<=wanted[1]:return False
    return True

def cursor_stamp(c,q):
    encoded=json.dumps(q,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return {'query':hashlib.sha256(encoded).hexdigest(),'snapshot':meta(c,'snapshot'),
            'boot':meta(c,'boot'),'consent':meta(c,'consent'),'scope':'lab_scope','model':meta(c,'model')}

def search_exact(c,q,k=MAX_SLOTS,cursor=None):
    if not validate_query(q) or not isinstance(k,int) or k<1 or k>MAX_SLOTS:
        return {'status':'INVALID_QUERY','matches':0,'scanned':0,'items':[],'cursor':None}
    mark=cursor_stamp(c,q)
    if cursor is not None:
        if (not isinstance(cursor,dict) or any(cursor.get(a)!=b for a,b in mark.items())
                or not isinstance(cursor.get('next_slot'),int)
                or not isinstance(cursor.get('deadline_ns'),int)
                or time.monotonic_ns()>cursor['deadline_ns']):
            return {'status':'INVALID_CURSOR','matches':0,'scanned':0,'items':[],'cursor':None}
    if meta(c,'consent_granted')!='1':
        return {'status':'DENIED_CONSENT','matches':0,'scanned':0,'items':[],'cursor':None}
    start_slot=cursor['next_slot'] if cursor else 0
    rows=c.execute('SELECT * FROM records WHERE slot>=? ORDER BY slot,generation',(start_slot,)).fetchall()
    matches=[];in_quarantine=False
    for r in rows:
        if not validate_record(r):
            return {'status':'INTEGRITY_ERROR','matches':0,'scanned':len(rows),'items':[],'cursor':None}
        if not row_matches(r,q):continue
        if r[6]!=bytes.fromhex(meta(c,'model')) or r[13]!=int(meta(c,'boot')) or r[14]!=int(meta(c,'consent')):
            in_quarantine=True;continue
        matches.append({'slot':r[0],'generation':r[1],'record_id':r[2],'payload':r[3]})
    if in_quarantine:
        return {'status':'QUARANTINE','matches':0,'scanned':len(rows),'items':[],'cursor':None}
    ret=matches[:k]
    clipped=len(matches)>k
    nextc={**mark,'next_slot':ret[-1]['slot']+1,
           'deadline_ns':cursor['deadline_ns'] if cursor else time.monotonic_ns()+5_000_000_000} if clipped else None
    return {'status':'TRUNCATED' if clipped else 'COMPLETE','matches':len(matches),'scanned':len(rows),'items':ret,'cursor':nextc}

def read_ref(c,slot,gen):
    r=c.execute('SELECT * FROM records WHERE slot=?',(slot,)).fetchone()
    if not r:return 'NOT_FOUND'
    if r[1]!=gen:return 'STALE_GENERATION'
    if not validate_record(r):return 'INTEGRITY_ERROR'
    if r[6]!=bytes.fromhex(meta(c,'model')) or r[13]!=int(meta(c,'boot')):return 'QUARANTINE'
    if meta(c,'consent_granted')!='1' or r[14]!=int(meta(c,'consent')):return 'DENIED_CONSENT'
    return 'EXACT_BYTES'

def crash_writer(path,ready):
    c=None
    try:
        c=connect(path);c.execute('BEGIN IMMEDIATE')
        result=add(c,0,991,b'uncommitted synthetic payload')
        ready.put(result,timeout=4)
        time.sleep(25)
    finally:
        if c:c.close()

def do_case(mode,case_dir,ctx):
    case_dir.mkdir(parents=True,exist_ok=False)
    db=case_dir/'exact_store.sqlite3';c=init_store(db)
    q=[cond('schema_id','eq',7)]
    metric='none'
    try:
        if mode=='EXACT_BYTE_MATCH':
            assert add(c,0,100,b'synthetic bolt=17; state=TRUE')=='INSERTED'
            assert add(c,1,101,b'synthetic bolt=18; state=FALSE')=='INSERTED'
            a=search_exact(c,[cond('schema_id','eq',7),cond('raw_literal','contains','bolt=17')])
            ok=a['status']=='COMPLETE' and a['matches']==1 and a['items'][0]['payload']==b'synthetic bolt=17; state=TRUE'
            metric='exact_payload_sha=YES' if ok else 'bad'
        elif mode=='NEAR_TEXT_NOT_EXACT':
            add(c,0,100,b'valve 123 CLOSED')
            a=search_exact(c,[cond('raw_literal','contains','valve 124')]);ok=a['status']=='COMPLETE' and a['matches']==0
            metric='similar_text_did_not_match=YES' if ok else 'bad'
        elif mode=='CORRUPT_PAYLOAD_UNAVAILABLE':
            add(c,0,100,b'authentic synthetic bytes')
            c.execute('UPDATE records SET payload=? WHERE slot=0',(b'corrupt synthetic bytes',))
            a=search_exact(c,q);ok=a['status']=='INTEGRITY_ERROR' and read_ref(c,0,1)=='INTEGRITY_ERROR'
            metric='corrupt_sha_rejected=YES' if ok else 'bad'
        elif mode=='CORRUPT_HEADER_UNAVAILABLE':
            add(c,0,100,b'header checksum still good')
            row=c.execute('SELECT header FROM records WHERE slot=0').fetchone()[0]
            changed=bytearray(row);changed[12]^=1
            c.execute('UPDATE records SET header=? WHERE slot=0',(bytes(changed),))
            a=search_exact(c,q);ok=a['status']=='INTEGRITY_ERROR' and read_ref(c,0,1)=='INTEGRITY_ERROR'
            metric='corrupt_header_rejected=YES' if ok else 'bad'
        elif mode=='MODEL_VERSION_QUARANTINE':
            add(c,0,100,b'model A memory')
            c.execute('UPDATE meta SET val=? WHERE name=?',(MODEL_B.hex(),'model'))
            a=search_exact(c,q);ok=a['status']=='QUARANTINE' and read_ref(c,0,1)=='QUARANTINE'
            metric='old_model_quarantined=YES' if ok else 'bad'
        elif mode=='BOOT_EPOCH_QUARANTINE':
            add(c,0,100,b'boot one timestamp')
            bump(c,'boot')
            a=search_exact(c,q);ok=a['status']=='QUARANTINE' and read_ref(c,0,1)=='QUARANTINE'
            metric='cross_boot_time_not_compared=YES' if ok else 'bad'
        elif mode=='STALE_SLOT_GENERATION':
            add(c,0,100,b'generation one',gen=1)
            c.execute('DELETE FROM records WHERE slot=0');bump(c,'snapshot')
            add(c,0,101,b'generation two',gen=2)
            ok=read_ref(c,0,1)=='STALE_GENERATION' and read_ref(c,0,2)=='EXACT_BYTES'
            metric='stale_ref_denied=YES' if ok else 'bad'
        elif mode=='STABLE_PAGE_WALK':
            for i in range(4):add(c,i,100+i,f'payload-{i}'.encode())
            seen=[];cur=None;steps=0;scanned_total=0
            while True:
                a=search_exact(c,q,k=1,cursor=cur);steps+=1;scanned_total+=a['scanned']
                assert a['status'] in ('COMPLETE','TRUNCATED')
                seen.extend((it['slot'],it['generation']) for it in a['items'])
                cur=a['cursor']
                if cur is None:break
                if steps>5:raise AssertionError('PAGINATION_LOOP')
            ok=seen==[(i,1) for i in range(4)] and steps==4
            metric=f'pages={steps} refs={len(seen)} scanned_total={scanned_total}'
        elif mode=='CURSOR_INVALID_AFTER_MUTATION':
            for i in range(2):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1);add(c,2,102,b'mutated snapshot')
            b=search_exact(c,q,k=1,cursor=a['cursor'])
            ok=a['status']=='TRUNCATED' and b['status']=='INVALID_CURSOR'
            metric='snapshot_mutation_invalidated_cursor=YES' if ok else 'bad'
        elif mode=='CURSOR_INVALID_AFTER_CONSENT':
            for i in range(2):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1);bump(c,'consent')
            b=search_exact(c,q,k=1,cursor=a['cursor'])
            ok=a['status']=='TRUNCATED' and b['status']=='INVALID_CURSOR'
            metric='consent_epoch_invalidated_cursor=YES' if ok else 'bad'
        elif mode=='CURSOR_INVALID_AFTER_QUERY_CHANGE':
            for i in range(2):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1)
            b=search_exact(c,[cond('kind','eq',1)],k=1,cursor=a['cursor'])
            ok=a['status']=='TRUNCATED' and b['status']=='INVALID_CURSOR'
            metric='changed_query_invalidated_cursor=YES' if ok else 'bad'
        elif mode=='CURSOR_INVALID_AFTER_MODEL_CHANGE':
            for i in range(2):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1)
            c.execute('UPDATE meta SET val=? WHERE name=?',(MODEL_B.hex(),'model'))
            b=search_exact(c,q,k=1,cursor=a['cursor'])
            ok=a['status']=='TRUNCATED' and b['status']=='INVALID_CURSOR'
            metric='model_digest_invalidated_cursor=YES' if ok else 'bad'
        elif mode=='CURSOR_EXPIRED_DEADLINE':
            for i in range(2):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1);expired=dict(a['cursor']);expired['deadline_ns']=time.monotonic_ns()-1
            b=search_exact(c,q,k=1,cursor=expired)
            ok=a['status']=='TRUNCATED' and b['status']=='INVALID_CURSOR'
            metric='expired_cursor_denied=YES' if ok else 'bad'
        elif mode=='TRUNCATED_REQUIRES_FULL_SCAN':
            for i in range(4):add(c,i,100+i,f'payload-{i}'.encode())
            a=search_exact(c,q,k=1)
            ok=a['status']=='TRUNCATED' and a['matches']==4 and a['scanned']==4 and len(a['items'])==1
            metric=f'k=1 total_matched_lower_bound={a["matches"]} scanned={a["scanned"]}'
        elif mode=='ALL_PINNED_DENIED_STORAGE':
            for i in range(4):assert add(c,i,100+i,f'pinned-{i}'.encode(),pinned=True)=='INSERTED'
            before=int(meta(c,'snapshot'))
            verdict=add(c,0,999,b'eviction forbidden')
            ok=verdict=='DENIED_STORAGE' and int(meta(c,'snapshot'))==before and c.execute('SELECT COUNT(*) FROM records').fetchone()[0]==4
            metric='all_pinned_fifth_insert=DENIED_STORAGE'
        elif mode=='CRASH_BEFORE_COMMIT':
            c.close();ready=ctx.Queue();p=ctx.Process(target=crash_writer,args=(str(db),ready));p.start()
            try:
                status=ready.get(timeout=8)
                if status!='INSERTED':raise RuntimeError('CHILD_NOT_STAGED')
                p.kill();p.join(timeout=5)
                if p.is_alive():raise RuntimeError('CHILD_NOT_KILLED')
            finally:
                if p.is_alive():p.kill();p.join(timeout=2)
                ready.cancel_join_thread();ready.close()
            c=connect(db)
            absent=c.execute('SELECT COUNT(*) FROM records').fetchone()[0]==0
            c.execute('BEGIN IMMEDIATE');ins=add(c,0,992,b'committed synthetic payload');c.execute('COMMIT')
            visible=c.execute('SELECT COUNT(*) FROM records').fetchone()[0]==1
            ok=absent and ins=='INSERTED' and visible and read_ref(c,0,1)=='EXACT_BYTES'
            metric='precommit_crash_rolled_back=YES committed_visible=YES' if ok else 'bad'
        elif mode=='INVALID_QUERY_REJECTED':
            add(c,0,100,b'benign')
            forms=[q*17,[cond('raw_literal','contains','x'*257)],
                   [cond('not_in_schema','eq',1)],[cond('raw_literal','contains','x'*255),cond('raw_literal','contains','y'*255)]*8]
            ok=all(search_exact(c,x)['status']=='INVALID_QUERY' for x in forms)
            metric='invalid_query_variants=4' if ok else 'bad'
        elif mode=='REVOKED_CONSENT_DENIES':
            add(c,0,100,b'private synthetic string')
            c.execute('UPDATE meta SET val=? WHERE name=?',('0','consent_granted'))
            a=search_exact(c,q);ok=a['status']=='DENIED_CONSENT' and read_ref(c,0,1)=='DENIED_CONSENT'
            metric='post_revoke_access=DENIED' if ok else 'bad'
        else:raise RuntimeError('UNKNOWN_MODE')
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity!='ok':ok=False
        return bool(ok),metric,integrity
    finally:c.close()

def stage(log,ctx,binary,root,workers,smoke,inject=False):
    tag=f'S5x{workers}_RAM32';cancel=ctx.Event();ready=ctx.Queue();out=ctx.Queue();rr=ctx.Queue()
    children=[];holder=None;complete=0;errors=0;worker_ok=0;reason=None;elapsed=[]
    repmax=1 if smoke else 2;expected=len(MODES)*repmax
    start=time.monotonic()
    try:
        holder=ctx.Process(target=ram_holder,args=(cancel,rr,32));holder.start()
        if rr.get(timeout=9) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(workers):
            p=ctx.Process(target=s5_worker,args=(binary,cancel,ready,out));p.start();children.append(p)
        if len({ready.get(timeout=30) for _ in children})!=workers:raise RuntimeError('NATIVE_WORKERS_NOT_READY')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={tag} processes={workers}')
        log(f'STAGE_BEGIN stage={tag} modes={len(MODES)} repeats={repmax} cases={expected} touched_RAM_MiB=32')
        for rep in range(repmax):
            for j,mode in enumerate(MODES):
                if why:=safety(smoke):reason=why;break
                if inject and complete>=3:reason='INJECTED_HOST_ONLY';break
                t0=time.monotonic()
                ok,detail,integrity=do_case(mode,root/tag/f'{rep+1:02d}_{j+1:02d}_{mode}',ctx)
                ms=(time.monotonic()-t0)*1000;elapsed.append(ms);complete+=1
                if not ok:errors+=1
                log(f'CASE stage={tag} rep={rep+1} mode={mode} status={"PASS" if ok else "FAIL"} '
                    f'fixture={detail} sqlite_integrity={integrity} elapsed_ms={ms:.3f}')
            if reason:break
        floor=2 if smoke else (24 if workers==2 else 30)
        while not reason and time.monotonic()-start<floor:
            if why:=safety(smoke):reason=why;break
            time.sleep(.15)
    except BaseException as e:
        errors+=1;log(f'STAGE_ERROR stage={tag} {type(e).__name__}: {str(e)[:280]}')
    finally:
        cancel.set()
        for p in children:
            p.join(timeout=4)
            if p.is_alive():p.kill();p.join(timeout=3)
        if holder:
            holder.join(timeout=3)
            if holder.is_alive():holder.kill();holder.join(timeout=3)
        for _ in children:
            try:
                pid,runs,mean,minimum,errs=out.get(timeout=2)
                log(f'S5_WORKER stage={tag} pid={pid} native_runs={runs} mean_GMAC_s={mean:.5f} '
                    f'min_GMAC_s={minimum:.5f} errors={errs}')
                if runs>0 and not errs:worker_ok+=1
                else:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={tag} REPORT_MISSING')
        for item in (ready,out,rr):
            item.cancel_join_thread();item.close()
    status='SAFETY_ABORT' if reason else ('COMPLETE' if complete==expected and errors==0 and worker_ok==workers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={tag} status={status} cases={complete}/{expected} failures={errors} '
        f'workers_ok={worker_ok}/{workers} case_max_ms={max(elapsed) if elapsed else None} safety_reason={reason or "-"}')
    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={tag} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return status,complete

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='Linux only; bypass A52 telemetry checks')
    ap.add_argument('--inject-host-abort',action='store_true',help='Use only with --host-smoke')
    opts=ap.parse_args()
    if opts.inject_host_abort and not opts.host_smoke:raise SystemExit('INJECT_HOST_ABORT_ONLY_WITH_HOST_SMOKE')
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_EXACT_MEMORY_INTEGRITY_V14_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(msg):print(msg,flush=True);f.write(msg+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- EXACT-BYTE MEMORY, GENERATION, QUARANTINE, PAGING AND CRASH LAB '+VERSION)
            log('Synthetic SQLite WAL FULL memory; fixed 64-byte header, SHA-256 payload, model digest, boot and consent epochs.')
            log('Exact query restricted subset; k limits returned refs, not full scan. 4 slots fixture, normative full store up to 4096.')
            log('Native S5 continuous background CPU load: 2/4 real C256R32 workers + 32MiB RAM; no idle stage.')
            log('LIMIT: SHA-256 detects accidental corruption, NOT malicious same-UID forgery. Cursor and consent are synthetic, not cryptographic authentication.')
            log('LIMIT: no real owner private data, actual model memory, embeddings, P training, Android authority, system actions or power-loss test.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if why:=safety(opts.host_smoke):log(f'RESULT SAFETY_SKIP {why}');return 3
            binary=native_binary();log('VERIFIED_BACKGROUND_S5 '+str(binary))
            root=home/'uno_a52_r41_exact_memory_v14'/stamp
            root.mkdir(parents=True,exist_ok=False)
            ctx=mp.get_context('fork')
            # Tiny self-test before long-running stages; no external data.
            c=init_store(root/'selftest.sqlite3')
            assert add(c,0,777,b'self-test bytes')=='INSERTED'
            assert search_exact(c,[cond('raw_literal','contains','self-test')])['matches']==1
            c.close();log('SELFTEST_PASS header=64 payload_sha=YES exact_query=YES')
            a=stage(log,ctx,binary,root,2 if not opts.host_smoke else 1,opts.host_smoke,opts.inject_host_abort)
            if a[0]!='COMPLETE':log(f'RESULT {a[0]} first_stage_cases={a[1]}');return 3
            b=stage(log,ctx,binary,root,4 if not opts.host_smoke else 2,opts.host_smoke)
            if b[0]!='COMPLETE':log(f'RESULT {b[0]} second_stage_cases={b[1]}');return 3
            log(f'RESULT COMPLETE_EXACT_MEMORY_INTEGRITY_LAB cases={a[1]+b[1]} stages=2/2')
            log('LIMIT: scoped exact-byte fixture and cooperative SQLite are not a secure Android memory authority or semantic recall proof.')
            return 0
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:400]}')
            log('TRACE '+traceback.format_exc()[-1000:]);return 2
        finally:log('REPORT '+str(report))

if __name__=='__main__':sys.exit(main())
