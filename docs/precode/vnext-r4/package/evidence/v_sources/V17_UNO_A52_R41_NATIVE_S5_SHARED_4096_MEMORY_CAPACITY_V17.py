#!/usr/bin/env python3
"""UNO R4.1 §11/§12.4 isolated lab: 4096 shared memory slot bound and measured memory.
Synthetic data only. No training, real permissions, OS actions or production files.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import multiprocessing as mp
import os
from pathlib import Path
import queue
import re
import shutil
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_SHARED_4096_MEMORY_CAPACITY_V17'
MIB=1048576
N=4096
M=128
KIND=('MEM','Q','D','L','U')
MODEL_A=hashlib.sha256(b'v17-fixture-model-A').digest()
MODEL_B=hashlib.sha256(b'v17-fixture-model-B').digest()
MODES=(
 'HARD_SHARED_CAP_4096', 'FULL_STREAM_INTEGRITY_4096',
 'EXACT_K1_FULL_SCAN', 'K16_STABLE_PAGING',
 'ALL_PINNED_INSERT_DENIED', 'STALE_GENERATION_REUSED',
 'GENERATION_WRAP_RETIRES_SLOT', 'MODEL_QUARANTINE',
 'MIGRATION_MAX16_PER_TASK', 'CONSENT_REVOKED_NO_ACCESS',
 'CORRUPTED_PAYLOAD_REJECTED', 'CURSOR_INVALID_AFTER_MUTATION',
)

def numfile(p):
    try:return int(Path(p).read_text().strip())
    except (OSError, ValueError):return None

def telemetry():
    try:m=int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])
    except (OSError,StopIteration,ValueError,IndexError):m=None
    return numfile('/sys/class/power_supply/battery/capacity'),numfile('/sys/class/power_supply/battery/temp'),m

def safety(host):
    if host:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100 <= t <= 800:return 'SAFETY_TELEMETRY_UNAVAILABLE'
    if b < 40:return 'SAFETY_BATTERY_BELOW_40_PERCENT'
    if t >= 375:return 'SAFETY_BATTERY_TEMP_GE_37_5C'
    if m < 400000:return 'SAFETY_MEMAVAILABLE_LT_400000_KB'
    return None

def pss_kb(pid=None):
    path=Path(f'/proc/{pid if pid is not None else "self"}/smaps_rollup')
    try:
        data=path.read_text()
        return int(re.search(r'^Pss:\s+(\d+)\s+kB$',data,re.M).group(1))
    except (OSError,AttributeError,ValueError):return None

def rss_hwm_kb():
    try:
        data=Path('/proc/self/status').read_text()
        def v(key):
            m=re.search(r'^'+key+r':\s+(\d+)\s+kB$',data,re.M)
            return int(m[1]) if m else None
        return v('VmRSS'),v('VmHWM')
    except OSError:return None,None

def binary_path():
    p=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_BINARY_MISSING '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=12)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_S5_PRECHECK_FAILED '+r.stdout[-200:])
    return p

def s5_worker(p,stop,ready,out):
    vals=[];errors=[]
    try:
        while not stop.is_set():
            r=subprocess.run([str(p),'rank','full','0.70'],capture_output=True,text=True,timeout=15)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
                raise RuntimeError('BACKGROUND_NATIVE_F_FAILED')
            m=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not m:raise RuntimeError('NATIVE_F_METRIC_MISSING')
            vals.append(float(m[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=5)
    except BaseException as e:errors.append(str(e)[:200])
    try:out.put((os.getpid(),len(vals),statistics.mean(vals) if vals else 0.,min(vals) if vals else 0.,errors),timeout=5)
    except BaseException:pass

def ram_worker(stop,ready):
    try:
        b=bytearray(32*MIB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(True,timeout=5)
        while not stop.wait(.2):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def connect(path):
    c=sqlite3.connect(str(path),isolation_level=None,timeout=8)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    c.execute('PRAGMA busy_timeout=6000')
    c.execute('PRAGMA cache_size=-4096') # cap SQLite page cache for fixture (~4 MiB)
    return c

def header(slot,gen):
    b=bytearray(64)
    struct.pack_into('<QIIQQQIHHQQ',b,0,100000+slot,slot,gen,9999+slot,100000000+slot,200000000+slot,0,1,0,4,slot)
    assert len(b)==64
    return bytes(b)

def bytes_payload(slot):
    return hashlib.blake2s(struct.pack('<I',slot)).digest()*128

def index_hash(head,key,val):
    return hashlib.sha256(head+key+val).digest()

def make_store(path,host,log):
    c=connect(path)
    c.execute('CREATE TABLE meta(k TEXT PRIMARY KEY,v INTEGER NOT NULL)')
    c.execute('INSERT INTO meta VALUES(?,?)',('snapshot',1))
    c.execute('CREATE TABLE records(slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 0 AND 4095),generation INTEGER NOT NULL,kind TEXT NOT NULL,pinned INTEGER NOT NULL,header BLOB NOT NULL,key_fp16 BLOB NOT NULL,value_fp16 BLOB NOT NULL,payload BLOB NOT NULL,payload_sha BLOB NOT NULL,index_sha BLOB NOT NULL,model_digest BLOB NOT NULL,boot INTEGER NOT NULL,consent INTEGER NOT NULL,expiry INTEGER NOT NULL)')
    c.execute("CREATE TRIGGER records_full BEFORE INSERT ON records WHEN (SELECT COUNT(*) FROM records) >= 4096 BEGIN SELECT RAISE(ABORT, 'DENIED_STORAGE'); END")
    c.execute("CREATE TRIGGER pinned_protected BEFORE DELETE ON records WHEN OLD.pinned=1 BEGIN SELECT RAISE(ABORT, 'DENIED_PINNED'); END")
    key=struct.pack('<128e',*([0.125]*M))
    val=struct.pack('<128e',*([0.25]*M))
    baseline=hashlib.sha256()
    started=time.monotonic()
    for base in range(0,N,128):
        if why:=safety(host):raise RuntimeError('SAFETY_ABORT_FILL_'+why)
        c.execute('BEGIN IMMEDIATE')
        try:
            for i in range(base,min(base+128,N)):
                pay=bytes_payload(i);h=header(i,1);sha=hashlib.sha256(pay).digest();idx=index_hash(h,key,val)
                c.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (i,1,KIND[i%len(KIND)],int(i%97==0),h,key,val,pay,sha,idx,MODEL_A,1,1,99999))
                baseline.update(struct.pack('<I',i));baseline.update(sha);baseline.update(idx)
            c.execute('COMMIT')
        except BaseException:
            c.execute('ROLLBACK');raise
    c.execute('PRAGMA wal_checkpoint(TRUNCATE)') # only fixture WAL
    elapsed=(time.monotonic()-started)*1000
    pages=c.execute('PRAGMA page_count').fetchone()[0]
    size=c.execute('PRAGMA page_size').fetchone()[0]
    dbsize=path.stat().st_size
    log(f'STORE_FILLED slots={N} shared_kinds={len(KIND)} payload_bytes_per_slot=4096 model_fp16_key_bytes=256 model_fp16_value_bytes=256 fixed_header_bytes=64 indexed_hash_bytes=64 expected_raw_payload_bytes={N*4096} sqlite_pages={pages} sqlite_page_size={size} sqlite_bytes={dbsize} fill_wall_ms={elapsed:.1f}')
    return c,baseline.digest()

def snapshot(c):return int(c.execute('SELECT v FROM meta WHERE k="snapshot"').fetchone()[0])

def scoped(c):
    """Savepoint protects all 4096 fixture records; changes never escape case."""
    class S:
        def __enter__(self):
            c.execute('SAVEPOINT case_fixture');return c
        def __exit__(self,typ,val,tb):
            c.execute('ROLLBACK TO case_fixture');c.execute('RELEASE case_fixture')
    return S()

def read_ref(c,slot,generation,model=MODEL_A,boot=1,consent=1):
    if consent!=1:return 'DENIED',None
    row=c.execute('SELECT generation,header,key_fp16,value_fp16,payload,payload_sha,index_sha,model_digest,boot,consent,expiry FROM records WHERE slot=?',(slot,)).fetchone()
    if row is None:return 'UNKNOWN',None
    gen,h,key,val,payload,pay_sha,idx_sha,mod,b,co,expiry=row
    if mod!=model or b!=boot or co!=consent or expiry<=100:return 'QUARANTINED',None
    if gen!=generation:return 'STALE',None
    if len(h)!=64 or len(key)!=256 or len(val)!=256 or len(payload)>4096:return 'CORRUPT',None
    if h!=header(slot,generation):return 'CORRUPT',None
    if hashlib.sha256(payload).digest()!=pay_sha or index_hash(h,key,val)!=idx_sha:return 'CORRUPT',None
    return 'COMPLETE',payload

def bounded_full_scan(c,k=1,model=MODEL_A,consent=1):
    if consent!=1:return 'DENIED',[],0,0
    if not (1<=k<=16):return 'INVALID',[],0,0
    scanned=0;matched=0;selected=[]
    for slot,kind,gen,mod,expiry in c.execute('SELECT slot,kind,generation,model_digest,expiry FROM records ORDER BY slot'):
        scanned+=1
        if kind=='MEM' and mod==model and expiry>100:
            matched+=1
            if len(selected)<k:selected.append((slot,gen))
    return ('TRUNCATED' if matched>k else 'COMPLETE'),selected,scanned,matched

def pagination(c,k=16):
    ver=snapshot(c);last=-1;all_seen=[];scanned=0
    while True:
        if snapshot(c)!=ver:raise RuntimeError('STALE_CURSOR')
        batch=c.execute('SELECT slot FROM records WHERE slot>? ORDER BY slot LIMIT ?',(last,k)).fetchall()
        scanned+=len(batch)
        if not batch:break
        slots=[r[0] for r in batch]
        if slots[0]<=last:raise RuntimeError('BAD_PAGE_ORDER')
        all_seen.extend(slots);last=slots[-1]
    return all_seen,scanned

def next_gen(g):
    return None if g>=0xffffffff else g+1

def case(mode,c,expected_digest):
    # Cases use only synthetic DB; no real application data or state.
    if mode=='HARD_SHARED_CAP_4096':
        counts=dict(c.execute('SELECT kind,COUNT(*) FROM records GROUP BY kind').fetchall())
        attempted=False;denied=False
        with scoped(c):
            try:
                c.execute('INSERT INTO records SELECT 4096,generation,kind,pinned,header,key_fp16,value_fp16,payload,payload_sha,index_sha,model_digest,boot,consent,expiry FROM records WHERE slot=0')
                attempted=True
            except sqlite3.IntegrityError as e:denied='DENIED_STORAGE' in str(e)
            same_count=c.execute('SELECT COUNT(*) FROM records').fetchone()[0]==N
        return (not attempted and denied and same_count and sum(counts.values())==N and set(counts)==set(KIND),f'kinds={counts} cap={N} 4097th_insert=DENIED_STORAGE')
    if mode=='FULL_STREAM_INTEGRITY_4096':
        s=hashlib.sha256();scanned=0
        for slot,gen,h,key,val,pay,sha,idx in c.execute('SELECT slot,generation,header,key_fp16,value_fp16,payload,payload_sha,index_sha FROM records ORDER BY slot'):
            if h!=header(slot,gen) or len(pay)!=4096 or hashlib.sha256(pay).digest()!=sha or index_hash(h,key,val)!=idx:return False,'FULL_RECORD_CORRUPT'
            s.update(struct.pack('<I',slot));s.update(sha);s.update(idx);scanned+=1
        return (scanned==N and s.digest()==expected_digest,f'full_integrity=YES scanned={scanned} baseline_digest_match={s.digest()==expected_digest}')
    if mode=='EXACT_K1_FULL_SCAN':
        status,refs,scanned,matched=bounded_full_scan(c,1)
        return (status=='TRUNCATED' and len(refs)==1 and scanned==N and matched==820 and read_ref(c,*refs[0])[0]=='COMPLETE',f'status={status} k=1 matched={matched} scanned={scanned} refs={len(refs)}')
    if mode=='K16_STABLE_PAGING':
        ids,scanned=pagination(c,16)
        return (ids==list(range(N)) and scanned==N,f'pages={len(ids)//16} returned={len(ids)} scanned={scanned} monotonic=YES')
    if mode=='ALL_PINNED_INSERT_DENIED':
        with scoped(c):
            c.execute('UPDATE records SET pinned=1')
            count=c.execute('SELECT COUNT(*) FROM records WHERE pinned=1').fetchone()[0]
            blocked_insert=False;blocked_delete=False
            try:
                c.execute('INSERT INTO records SELECT 4096,generation,kind,pinned,header,key_fp16,value_fp16,payload,payload_sha,index_sha,model_digest,boot,consent,expiry FROM records WHERE slot=0')
            except sqlite3.IntegrityError as e:blocked_insert='DENIED_STORAGE' in str(e)
            try:c.execute('DELETE FROM records WHERE slot=0')
            except sqlite3.IntegrityError as e:blocked_delete='DENIED_PINNED' in str(e)
            return (count==N and blocked_insert and blocked_delete and c.execute('SELECT COUNT(*) FROM records').fetchone()[0]==N,f'all_pinned={count} insertion_denied={blocked_insert} protected_eviction_denied={blocked_delete} shared_slots={N}')
    if mode=='STALE_GENERATION_REUSED':
        with scoped(c):
            slot=5;old_status,_=read_ref(c,slot,1)
            pay=bytes_payload(slot);h=header(slot,2)
            c.execute('UPDATE records SET generation=?,header=?,index_sha=? WHERE slot=?',(2,h,index_hash(h,struct.pack('<128e',*([.125]*128)),struct.pack('<128e',*([.25]*128))),slot))
            stale,_=read_ref(c,slot,1);new,_=read_ref(c,slot,2)
            return (old_status=='COMPLETE' and stale=='STALE' and new=='COMPLETE',f'old_status={old_status} stale_status={stale} current_status={new}')
    if mode=='GENERATION_WRAP_RETIRES_SLOT':
        with scoped(c):
            c.execute('UPDATE records SET generation=? WHERE slot=?',(4294967295,9))
            value=c.execute('SELECT generation FROM records WHERE slot=9').fetchone()[0]
            retired=next_gen(value) is None
            return (retired and read_ref(c,9,1)[0]=='STALE',f'generation={value} retired={retired} next_generation={next_gen(value)}')
    if mode=='MODEL_QUARANTINE':
        s,refs,sc,matched=bounded_full_scan(c,16,model=MODEL_B)
        stat,_=read_ref(c,0,1,model=MODEL_B)
        return (s=='COMPLETE' and not refs and matched==0 and sc==N and stat=='QUARANTINED',f'foreign_model_status={stat} eligible={matched} scanned={sc}')
    if mode=='MIGRATION_MAX16_PER_TASK':
        with scoped(c):
            # Reencode 16 synthetic FP16 key/values from exact payload; not learned F.
            selected=c.execute('SELECT slot,payload,header FROM records ORDER BY slot LIMIT 16').fetchall()
            for slot,pay,h in selected:
                d=hashlib.sha256(pay+MODEL_B).digest()
                key=struct.pack('<128e',*[(d[i%32]-127)/256 for i in range(128)])
                val=struct.pack('<128e',*[(d[(i+7)%32]-127)/256 for i in range(128)])
                c.execute('UPDATE records SET key_fp16=?,value_fp16=?,index_sha=?,model_digest=? WHERE slot=?',
                          (key,val,index_hash(h,key,val),MODEL_B,slot))
            c.execute('UPDATE meta SET v=v+1 WHERE k="snapshot"')
            total=c.execute('SELECT COUNT(*) FROM records WHERE model_digest=?',(MODEL_B,)).fetchone()[0]
            rest=c.execute('SELECT COUNT(*) FROM records WHERE model_digest=?',(MODEL_A,)).fetchone()[0]
            current,_=read_ref(c,0,1,model=MODEL_B)
            remaining,_=read_ref(c,16,1,model=MODEL_B)
            # Model-B record header remains original synthetic ABI; no key compatibility claim.
            return (len(selected)==16 and total==16 and rest==N-16 and current=='COMPLETE' and remaining=='QUARANTINED',f'migrated_this_task={total} excluded_remaining={rest} max_per_task=16')
    if mode=='CONSENT_REVOKED_NO_ACCESS':
        state,refs,sc,matched=bounded_full_scan(c,1,consent=0)
        status,_=read_ref(c,0,1,consent=0)
        return (state=='DENIED' and not refs and sc==0 and status=='DENIED',f'exact_status={state} reference_status={status} data_scanned={sc}')
    if mode=='CORRUPTED_PAYLOAD_REJECTED':
        with scoped(c):
            c.execute('UPDATE records SET payload=? WHERE slot=0',(b'corrupted-same-uid',))
            stat,_=read_ref(c,0,1)
            good,_=read_ref(c,1,1)
            return (stat=='CORRUPT' and good=='COMPLETE',f'corrupted_status={stat} unaffected_slot={good}')
    if mode=='CURSOR_INVALID_AFTER_MUTATION':
        with scoped(c):
            old=snapshot(c)
            first=c.execute('SELECT slot FROM records WHERE slot>-1 ORDER BY slot LIMIT 16').fetchall()
            c.execute("UPDATE records SET kind='MEM' WHERE slot=1")
            c.execute('UPDATE meta SET v=v+1 WHERE k="snapshot"')
            rejected=snapshot(c)!=old
            return (len(first)==16 and rejected,f'page_count={len(first)} old_snapshot={old} current_snapshot={snapshot(c)} old_cursor=STALE')
    raise RuntimeError('UNKNOWN_MODE_'+mode)

def stage(log,ctx,bg,root,nworkers,host,inject):
    tag=f'S5x{nworkers}_RAM32';expected=len(MODES)*(1 if host else 2)
    stop=ctx.Event();wr=ctx.Queue();wo=ctx.Queue();rr=ctx.Queue();workers=[];holder=None
    completed=0;failures=0;worker_ok=0;reason=None;durations=[];conn=None
    stage_start=time.monotonic()
    ps_before=pss_kb();rss_before,hwm_before=rss_hwm_kb()
    try:
        holder=ctx.Process(target=ram_worker,args=(stop,rr));holder.start()
        if rr.get(timeout=15) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(nworkers):
            w=ctx.Process(target=s5_worker,args=(bg,stop,wr,wo));w.start();workers.append(w)
        if len({wr.get(timeout=28) for _ in workers})!=nworkers:raise RuntimeError('S5_NOT_ALL_ACTIVE')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={tag} workers={nworkers}')
        log(f'STAGE_BEGIN stage={tag} expected={expected} slots={N} kinds={len(KIND)} RAM_MiB=32')
        stage_path=root/tag;stage_path.mkdir()
        conn,baseline=make_store(stage_path/'shared_store.sqlite3',host,log)
        log(f'ACTUAL_MEMORY stage={tag} phase=after_fill own_PSS_kB={pss_kb()} own_RSS_kB={rss_hwm_kb()[0]} own_HWM_kB={rss_hwm_kb()[1]} NOTE=not_Android_app_peak')
        for rep in range(1,2 if host else 3):
            for mode in MODES:
                if why:=safety(host):reason=why;break
                if inject and completed>=3:reason='INJECTED_HOST_SAFETY_ABORT';break
                t=time.monotonic()
                ok,detail=case(mode,conn,baseline)
                ms=(time.monotonic()-t)*1000;durations.append(ms);completed+=1
                if not ok:failures+=1
                log(f'CASE stage={tag} rep={rep} mode={mode} status={"PASS" if ok else "FAIL"} {detail} elapsed_ms={ms:.3f}')
            if reason:break
        if conn:
            integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity!='ok':failures+=1
            log(f'STORAGE_CHECK stage={tag} sqlite_integrity={integrity} count={conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]}')
        floor=2 if host else (24 if nworkers==2 else 30)
        while not reason and time.monotonic()-stage_start<floor:
            if why:=safety(host):reason=why;break
            time.sleep(.15)
    except BaseException as exc:
        failures+=1
        if str(exc).startswith('SAFETY_ABORT_FILL_'):reason=str(exc)
        else:log(f'STAGE_ERROR stage={tag} error={type(exc).__name__} detail={str(exc)[:200]}')
    finally:
        if conn:conn.close()
        stop.set()
        for p in workers:
            p.join(5)
            if p.is_alive():p.kill();p.join(3)
        if holder:
            holder.join(4)
            if holder.is_alive():holder.kill();holder.join(3)
        for _ in workers:
            try:
                pid,runs,mean,minval,errors=wo.get(timeout=3)
                log(f'S5_WORKER stage={tag} pid={pid} native_runs={runs} mean_GMAC_s={mean:.6f} min_GMAC_s={minval:.6f} errors={errors}')
                if runs>0 and not errors:worker_ok+=1
                else:failures+=1
            except queue.Empty:failures+=1;log(f'S5_WORKER stage={tag} REPORT_MISSING')
        for q in (wr,wo,rr):q.cancel_join_thread();q.close()
    ps_after=pss_kb();rss,hwm=rss_hwm_kb()
    label='SAFETY_ABORT' if reason else ('COMPLETE' if completed==expected and failures==0 and worker_ok==nworkers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={tag} status={label} cases={completed}/{expected} failures={failures} workers_ok={worker_ok}/{nworkers} max_case_ms={max(durations) if durations else None} safety_reason={reason or "-"}')
    log(f'MEMORY_MEASURE stage={tag} own_PSS_before_kB={ps_before} own_PSS_after_kB={ps_after} own_RSS_before_kB={rss_before} own_RSS_after_kB={rss} own_HWM_after_kB={hwm} NOTE=single_python_process_not_total_peak')
    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={tag} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return label,completed

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='developer-only local Linux smoke')
    ap.add_argument('--inject-host-abort',action='store_true',help='developer-only simulation')
    args=ap.parse_args()
    if args.inject_host_abort and not args.host_smoke:raise SystemExit('HOST_ONLY_INJECTION')
    home=Path.home();out=home/'storage'/'downloads'
    if not out.is_dir() or not os.access(out,os.W_OK):out=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=out/f'UNO_A52_R41_SHARED_4096_MEMORY_CAPACITY_V17_{stamp}.txt'
    with report.open('x',encoding='utf-8') as fp:
        def log(x):print(x,flush=True);fp.write(x+'\n');fp.flush()
        try:
            log('UNO / UNOVYRA -- SHARED 4096-SLOT MEMORY CAPACITY / REAL SQLITE + PSS UNDER NATIVE S5 LOAD '+VERSION)
            log('R4.1 §11, §12.4: 4096 shared slots across MEM/Q/D/L/U, FP16 m128 key/value, 64B header, max 4096B payload, 64B indexed hashes; synthetic fixture.')
            log('4096 records are materialized in SQLite WAL FULL. Real process PSS is measured where /proc/self/smaps_rollup permits; not total Android peak.')
            log('Two/four continuously computing native C256R32 S5 background workers plus 32MiB held RAM. No idle stage.')
            log('NO neural model training, P updates, Android permission/STOP/OS dispatch, secure provenance, personal data, power loss, or production code.')
            log('SAFETY battery>=40%, battery temperature<37.5C, MemAvailable>=400000kB. SAFETY_ABORT is never COMPLETE.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if why:=safety(args.host_smoke):log('RESULT SAFETY_SKIP '+why);return 3
            base=home/'uno_a52_r41_shared_capacity_v17'
            base.mkdir(exist_ok=True)
            if not args.host_smoke and shutil.disk_usage(base).free<128*MIB:
                log('RESULT SAFETY_SKIP STORAGE_FREE_BELOW_128_MiB');return 3
            native=binary_path();log('VERIFIED_BACKGROUND_NATIVE_S5 '+str(native))
            root=base/stamp;root.mkdir(parents=True,exist_ok=False)
            ctx=mp.get_context('fork')
            a=stage(log,ctx,native,root,1 if args.host_smoke else 2,args.host_smoke,args.inject_host_abort)
            if a[0]!='COMPLETE':log(f'RESULT {a[0]} cases={a[1]}');return 3
            b=stage(log,ctx,native,root,2 if args.host_smoke else 4,args.host_smoke,False)
            if b[0]!='COMPLETE':log(f'RESULT {b[0]} cases={b[1]}');return 3
            log(f'RESULT COMPLETE_SHARED_4096_MEMORY_CAPACITY_LAB stages=2/2 cases={a[1]+b[1]} slots_per_stage=4096')
            log('LIMIT: fixture key/value are synthetic; SSD durability, protected provenance, semantic quality, actual full Android app peak PSS, real migration and energy are untested.')
            return 0
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:250]}')
            log('TRACE '+traceback.format_exc()[-1400:]);return 2
        finally:log('REPORT '+str(report))
if __name__=='__main__':sys.exit(main())
