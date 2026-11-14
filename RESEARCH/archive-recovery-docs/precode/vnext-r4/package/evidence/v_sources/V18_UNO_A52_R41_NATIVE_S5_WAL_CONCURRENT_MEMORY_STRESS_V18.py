#!/usr/bin/env python3
"""UNO R4.1 isolated V18: 4096 slot WAL concurrent readers/writer stress on A52.
Not a secure Android boundary, trained model, physical power-cut or production code.
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
import signal
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_WAL_CONCURRENT_MEMORY_STRESS_V18'
N=4096
MIB=1048576
KINDS=('MEM','Q','D','L','U')
MODES=('READER_PINNED_OLD_SNAPSHOT','WAL_CHECKPOINT_PINNED_THEN_RELEASED',
       'PAGING_CURSOR_STALE_AFTER_WRITER','CONCURRENT_READERS_SINGLE_WRITER',
       'WRITER_CRASH_BEFORE_COMMIT','SQLITE_BUSY_NO_IMPLICIT_RETRY',
       'CONSENT_FRESH_READ_DENIED','CONSENT_TOCTOU_NEGATIVE',
       'FULL_4096_INTEGRITY_AFTER_CHURN')

def readnum(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:mem=int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])
    except (OSError,StopIteration,ValueError,IndexError):mem=None
    return dict(battery=readnum('/sys/class/power_supply/battery/capacity'),
                temp_deciC=readnum('/sys/class/power_supply/battery/temp'),
                MemAvailable_kB=mem,
                charge_status=(Path('/sys/class/power_supply/battery/status').read_text().strip() if Path('/sys/class/power_supply/battery/status').exists() else 'UNAVAILABLE'))

def guard(host):
    if host:return None
    x=telemetry();b=x['battery'];t=x['temp_deciC'];m=x['MemAvailable_kB']
    if None in (b,t,m) or not (100<=t<=800):return 'SAFETY_TELEMETRY_UNAVAILABLE'
    if b<40:return 'SAFETY_BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'SAFETY_BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'SAFETY_MEMAVAILABLE_LT_400000_KB'
    return None

def smaps(pid=None):
    p=Path(f'/proc/{pid if pid is not None else "self"}/smaps_rollup')
    try:
        d=p.read_text();q=re.search(r'^Pss:\s+(\d+)\s+kB$',d,re.M)
        return int(q[1]) if q else None
    except OSError:return None

def proc_rss():
    try:
        d=Path('/proc/self/status').read_text();m=re.search(r'^VmRSS:\s+(\d+)\s+kB$',d,re.M)
        return int(m[1]) if m else None
    except OSError:return None

def native_binary(host,override=None):
    p=Path(override) if host and override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_BINARY_MISSING '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=12)
    if r.returncode!=0 or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_OPERATOR_CONTRACT_FAIL '+r.stdout[-220:])
    return p

def s5worker(binary,stop,ready,out):
    vals=[];errors=[]
    try:
        while not stop.is_set():
            r=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=15)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
                raise RuntimeError('NATIVE_S5_CONTRACT_FAIL')
            m=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not m:raise RuntimeError('NATIVE_S5_THROUGHPUT_MISSING')
            vals.append(float(m[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=5)
    except BaseException as e:errors.append(str(e)[:160])
    try:out.put((os.getpid(),len(vals),statistics.mean(vals) if vals else 0.,min(vals) if vals else 0.,errors),timeout=4)
    except BaseException:pass

def ramholder(stop,ready):
    try:
        b=bytearray(32*MIB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(True,timeout=5)
        while not stop.wait(.15):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def dbconnect(path,busy=1200):
    c=sqlite3.connect(str(path),timeout=busy/1000,isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    c.execute(f'PRAGMA busy_timeout={busy}')
    c.execute('PRAGMA cache_size=-4096')
    return c

def pay(slot,gen):
    h=hashlib.blake2s(struct.pack('<II',slot,gen)).digest()
    return h*128

def sha(b):return hashlib.sha256(b).digest()

def setup(path,host,log):
    c=dbconnect(path)
    c.execute('CREATE TABLE meta(k TEXT PRIMARY KEY,v INTEGER NOT NULL)')
    c.executemany('INSERT INTO meta VALUES(?,?)', [('version',0),('consent',1),('consent_epoch',1)])
    c.execute('CREATE TABLE records(slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 0 AND 4095),kind TEXT NOT NULL,generation INTEGER NOT NULL CHECK(generation>=1),payload BLOB NOT NULL,payload_sha BLOB NOT NULL,pinned INTEGER NOT NULL DEFAULT 0)')
    c.execute('CREATE TABLE audit(version INTEGER PRIMARY KEY,slot INTEGER NOT NULL,generation INTEGER NOT NULL,payload_sha BLOB NOT NULL)')
    c.execute('CREATE TRIGGER cap BEFORE INSERT ON records WHEN (SELECT COUNT(*) FROM records)>=4096 BEGIN SELECT RAISE(ABORT, "DENIED_STORAGE"); END')
    begin=time.monotonic()
    for start in range(0,N,128):
        if reason:=guard(host):raise RuntimeError('SAFETY_ABORT_FILL_'+reason)
        c.execute('BEGIN IMMEDIATE')
        try:
            c.executemany('INSERT INTO records(slot,kind,generation,payload,payload_sha,pinned) VALUES(?,?,?,?,?,?)',
                          [(s,KINDS[s%5],1,pay(s,1),sha(pay(s,1)),int(s%97==0)) for s in range(start,start+128)])
            c.execute('COMMIT')
        except BaseException:c.execute('ROLLBACK');raise
    c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    size=path.stat().st_size
    log(f'STORE_FILLED slots={N} sqlite_bytes={size} fill_wall_ms={(time.monotonic()-begin)*1000:.1f} own_PSS_kB={smaps()}')
    return c

def meta(c,k):return int(c.execute('SELECT v FROM meta WHERE k=?',(k,)).fetchone()[0])

def checked_payload(c,slot=0):
    row=c.execute('SELECT generation,payload,payload_sha FROM records WHERE slot=?',(slot,)).fetchone()
    if row is None:raise AssertionError('MISSING_SLOT')
    gen,b,d=row
    if len(b)!=4096 or sha(b)!=d or b!=pay(slot,gen):raise AssertionError('BAD_PAYLOAD')
    return gen,b

def commit_update(c,slot=0):
    c.execute('BEGIN IMMEDIATE')
    try:
        old=meta(c,'version');gen=int(c.execute('SELECT generation FROM records WHERE slot=?',(slot,)).fetchone()[0])+1
        payload=pay(slot,gen);digest=sha(payload)
        c.execute('UPDATE records SET generation=?,payload=?,payload_sha=? WHERE slot=?',(gen,payload,digest,slot))
        c.execute('UPDATE meta SET v=? WHERE k="version"',(old+1,))
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(old+1,slot,gen,digest))
        c.execute('COMMIT')
        return old+1,gen
    except BaseException:
        c.execute('ROLLBACK');raise

def update_child(path,n,out):
    try:
        c=dbconnect(path)
        for j in range(n):commit_update(c)
        c.close();out.put(('OK',n),timeout=3)
    except BaseException as e:
        try:out.put(('FAIL',str(e)[:180]),timeout=3)
        except BaseException:pass

def crash_child(path,ready):
    try:
        c=dbconnect(path)
        c.execute('BEGIN IMMEDIATE')
        old=meta(c,'version');gen=checked_payload(c)[0]+1
        b=pay(0,gen)
        c.execute('UPDATE records SET generation=?,payload=?,payload_sha=? WHERE slot=0',(gen,b,sha(b)))
        c.execute('UPDATE meta SET v=? WHERE k="version"',(old+1,))
        c.execute('INSERT INTO audit VALUES(?,?,?,?)',(old+1,0,gen,sha(b)))
        ready.put(('OPEN_UNCOMMITTED',old),timeout=4)
        time.sleep(25)
    except BaseException as e:
        try:ready.put(('ERROR',str(e)[:180]),timeout=2)
        except BaseException:pass

def busy_child(path,out):
    c=None
    try:
        c=dbconnect(path,busy=150)
        try:
            c.execute('BEGIN IMMEDIATE')
            c.execute('ROLLBACK');out.put('UNEXPECTED_ACQUIRED',timeout=3)
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():out.put('SQLITE_BUSY',timeout=3)
            else:out.put('OTHER_'+str(e)[:100],timeout=3)
    except BaseException as e:
        try:out.put('ERROR_'+str(e)[:100],timeout=3)
        except BaseException:pass
    finally:
        if c:c.close()

def scan_reader(path,stop,ready,out):
    c=None;count=0;errors=[];last=-1
    try:
        c=dbconnect(path)
        ready.put(True,timeout=4)
        while not stop.is_set():
            c.execute('BEGIN')
            try:
                v=meta(c,'version');gen,_=checked_payload(c,0)
                n=c.execute('SELECT COUNT(*) FROM records').fetchone()[0]
                a=int(c.execute('SELECT COUNT(*) FROM audit').fetchone()[0])
                if gen!=v+1 or a!=v or n!=N:raise AssertionError(f'TORN_SNAPSHOT v={v} gen={gen} audit={a} n={n}')
                count+=1;last=v
                c.execute('COMMIT')
            except BaseException:
                c.execute('ROLLBACK');raise
            if count%8==0:time.sleep(.001)
    except BaseException as e:errors.append(str(e)[:180])
    finally:
        if c:c.close()
        try:out.put((count,last,errors),timeout=4)
        except BaseException:pass

def child_wait(proc,host,limit=12):
    end=time.monotonic()+limit
    while proc.is_alive() and time.monotonic()<end:
        if why:=guard(host):raise RuntimeError(why)
        proc.join(.07)
    if proc.is_alive():raise RuntimeError('CHILD_TIMEOUT')
    if proc.exitcode!=0:raise RuntimeError('CHILD_EXIT_'+str(proc.exitcode))

def query_page(c,cursor=None,k=16):
    # Illustrates cooperative *fresh* permission check, NOT linearizable OS authority.
    if meta(c,'consent')!=1:return 'DENIED',[],None,0
    v=meta(c,'version');e=meta(c,'consent_epoch')
    if cursor and cursor[:2]!=(v,e):return 'STALE_CURSOR',[],None,0
    last=-1 if cursor is None else cursor[2]
    rows=[r[0] for r in c.execute('SELECT slot FROM records WHERE slot>? ORDER BY slot LIMIT ?',(last,k)).fetchall()]
    next_cursor=(v,e,rows[-1]) if rows else None
    return 'COMPLETE',rows,next_cursor,len(rows)

def mode_case(mode,c,path,ctx,host,log):
    if mode in ('READER_PINNED_OLD_SNAPSHOT','WAL_CHECKPOINT_PINNED_THEN_RELEASED'):
        reader=dbconnect(path)
        try:
            reader.execute('BEGIN')
            v0=meta(reader,'version');g0,_=checked_payload(reader)
            out=ctx.Queue();w=ctx.Process(target=update_child,args=(path,8 if host else 24,out));w.start()
            try:
                child_wait(w,host,16)
                report=out.get(timeout=3)
                assert report[0]=='OK',report
            finally:
                if w.is_alive():w.kill();w.join(3)
                out.cancel_join_thread();out.close()
            v_old=meta(reader,'version');g_old,_=checked_payload(reader)
            v_new=meta(c,'version');g_new,_=checked_payload(c)
            wal=Path(str(path)+'-wal')
            wal_before=wal.stat().st_size if wal.exists() else 0
            if mode=='WAL_CHECKPOINT_PINNED_THEN_RELEASED':
                # PASSIVE checkpoint is nonblocking. Reader has an old snapshot, thus cannot advance to tip.
                busy,logframes,checkpointed=tuple(c.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone())
                incomplete=logframes>checkpointed
                reader.execute('COMMIT');reader.close();reader=None
                done=tuple(c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
                wal_after=wal.stat().st_size if wal.exists() else 0
                ok=(v_old==v0 and g_old==g0 and v_new>v0 and g_new>g0 and incomplete and done[0]==0 and wal_after==0)
                return ok,f'old_version={v_old} new_version={v_new} pinned_WAL_bytes={wal_before} passive_frames={logframes} passive_checkpointed={checkpointed} full_checkpoint={done} WAL_after_bytes={wal_after}'
            ok=(v_old==v0 and g_old==g0 and v_new==v0+(8 if host else 24) and g_new==g0+(8 if host else 24))
            return ok,f'pinned_old={v_old}/{g_old} fresh={v_new}/{g_new} snapshot_consistent={ok} wal_bytes={wal_before}'
        finally:
            if reader:
                try:reader.execute('COMMIT')
                except sqlite3.Error:pass
                reader.close()
    if mode=='PAGING_CURSOR_STALE_AFTER_WRITER':
        first,rows,cur,sc=query_page(c,k=16)
        commit_update(c)
        stale,after,_,sc_after=query_page(c,cur,k=16)
        fresh,fr,_,sc_fr=query_page(c,k=16)
        ok=(first=='COMPLETE' and len(rows)==16 and stale=='STALE_CURSOR' and not after and sc_after==0 and fresh=='COMPLETE' and len(fr)==16)
        return ok,f'old_cursor={stale} old_cursor_data_scan={sc_after} fresh_count={len(fr)}'
    if mode=='CONCURRENT_READERS_SINGLE_WRITER':
        stop=ctx.Event();ready=ctx.Queue();out=ctx.Queue();wo=ctx.Queue();readers=[];writer=None
        try:
            for _ in range(2):
                p=ctx.Process(target=scan_reader,args=(path,stop,ready,out));p.start();readers.append(p)
            for _ in readers:
                assert ready.get(timeout=6) is True
            base=meta(c,'version')
            n=24 if host else 64
            writer=ctx.Process(target=update_child,args=(path,n,wo));writer.start()
            child_wait(writer,host,24)
            wreport=wo.get(timeout=4)
            assert wreport==('OK',n),wreport
            # Keep readers active until they observe the committed endpoint.
            end=time.monotonic()+(.1 if host else .25)
            while time.monotonic()<end:
                if why:=guard(host):raise RuntimeError(why)
                time.sleep(.04)
            stop.set()
            for p in readers:child_wait(p,host,5)
            infos=[out.get(timeout=3) for _ in readers]
            v=meta(c,'version');g,_=checked_payload(c)
            ok=(v==base+n and g==v+1 and all(i[0]>2 and not i[2] for i in infos))
            return ok,f'commits={n} version={v} readers_checks={[i[0] for i in infos]} reader_errors={[i[2] for i in infos]} snapshot_atomic={ok}'
        finally:
            stop.set()
            if writer and writer.is_alive():writer.kill();writer.join(3)
            for p in readers:
                if p.is_alive():p.kill();p.join(3)
            for q in (ready,out,wo):q.cancel_join_thread();q.close()
    if mode=='WRITER_CRASH_BEFORE_COMMIT':
        before=meta(c,'version');g0,_=checked_payload(c)
        ready=ctx.Queue();p=ctx.Process(target=crash_child,args=(path,ready));p.start()
        try:
            received=ready.get(timeout=8)
            if received!=('OPEN_UNCOMMITTED',before):raise RuntimeError('WRITER_NOT_PREPARED_'+str(received))
            os.kill(p.pid,signal.SIGKILL);p.join(5)
            if p.is_alive():raise RuntimeError('KILLED_CHILD_STILL_ALIVE')
        finally:
            if p.is_alive():p.kill();p.join(3)
            ready.cancel_join_thread();ready.close()
        check=dbconnect(path)
        try:
            after=meta(check,'version');g1,_=checked_payload(check)
            audit_count=check.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
            integrity=check.execute('PRAGMA integrity_check').fetchone()[0]
        finally:check.close()
        ok=(after==before and g1==g0 and audit_count==after and integrity=='ok')
        return ok,f'killed_uncommitted_writer=YES pre_version={before} post_version={after} pre_gen={g0} post_gen={g1} audit={audit_count} integrity={integrity}'
    if mode=='SQLITE_BUSY_NO_IMPLICIT_RETRY':
        v0=meta(c,'version');q=ctx.Queue();p=None
        c.execute('BEGIN IMMEDIATE')
        try:
            p=ctx.Process(target=busy_child,args=(path,q));p.start()
            child_wait(p,host,5)
            result=q.get(timeout=3)
        finally:
            c.execute('ROLLBACK')
            if p and p.is_alive():p.kill();p.join(3)
            q.cancel_join_thread();q.close()
        no_partial=(meta(c,'version')==v0)
        v1,g1=commit_update(c)
        ok=(result=='SQLITE_BUSY' and no_partial and v1==v0+1)
        return ok,f'contending_writer={result} no_partial={no_partial} next_explicit_commit={v1} generation={g1}'
    if mode=='CONSENT_FRESH_READ_DENIED':
        a=meta(c,'consent');e=meta(c,'consent_epoch')
        first,rows,cur,sc=query_page(c,k=16)
        assert first=='COMPLETE' and len(rows)==16 and cur
        c.execute('BEGIN IMMEDIATE')
        try:
            c.execute('UPDATE meta SET v=0 WHERE k="consent"')
            c.execute('UPDATE meta SET v=v+1 WHERE k="consent_epoch"')
            c.execute('COMMIT')
        except BaseException:c.execute('ROLLBACK');raise
        state,refs,_,scan=query_page(c,cur,k=16)
        check=meta(c,'consent_epoch')
        c.execute('BEGIN IMMEDIATE')
        c.execute('UPDATE meta SET v=1 WHERE k="consent"')
        c.execute('UPDATE meta SET v=v+1 WHERE k="consent_epoch"')
        c.execute('COMMIT')
        # A cursor minted before consent revoke never gets to continue, even after re-grant.
        old,_,_,scanold=query_page(c,cur,k=16)
        ok=(a==1 and check==e+1 and state=='DENIED' and not refs and scan==0 and old=='STALE_CURSOR' and scanold==0)
        return ok,f'fresh_read={state} scanned={scan} regrant_old_cursor={old} regrant_scan={scanold}'
    if mode=='CONSENT_TOCTOU_NEGATIVE':
        # A direct reader that checked consent before revocation can still access raw data.
        pre=meta(c,'consent');assert pre==1
        c.execute('BEGIN IMMEDIATE');c.execute('UPDATE meta SET v=0 WHERE k="consent"');c.execute('UPDATE meta SET v=v+1 WHERE k="consent_epoch"');c.execute('COMMIT')
        raw=c.execute('SELECT payload FROM records WHERE slot=0').fetchone()[0]
        scoped,refs,_,scans=query_page(c,k=16)
        c.execute('BEGIN IMMEDIATE');c.execute('UPDATE meta SET v=1 WHERE k="consent"');c.execute('UPDATE meta SET v=v+1 WHERE k="consent_epoch"');c.execute('COMMIT')
        vulnerable=(len(raw)==4096 and scoped=='DENIED' and not refs and scans==0)
        return vulnerable,f'NEGATIVE_FINDING precheck_was_allowed={pre} revoked_raw_still_accessible={len(raw)==4096} fresh_cooperative_check={scoped} (not_OS_isolation)'
    if mode=='FULL_4096_INTEGRITY_AFTER_CHURN':
        c.execute('BEGIN')
        try:
            n=0
            for s,g,b,d in c.execute('SELECT slot,generation,payload,payload_sha FROM records ORDER BY slot'):
                if len(b)!=4096 or sha(b)!=d or b!=pay(s,g):raise AssertionError(f'BAD_SLOT {s}')
                n+=1
            ver=meta(c,'version');a=c.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
            c.execute('COMMIT')
        except BaseException:c.execute('ROLLBACK');raise
        check=c.execute('PRAGMA quick_check').fetchone()[0]
        ok=(n==N and a==ver and check=='ok')
        return ok,f'full_scan={n} audit_rows={a} version={ver} sqlite_quick_check={check}'
    raise RuntimeError('UNKNOWN_MODE '+mode)

def runstage(log,ctx,binary,root,nworkers,host,inject_abort):
    tag=f'S5x{nworkers}_RAM32';expected=len(MODES)*2
    stage_start=time.monotonic();stop=ctx.Event();ready=ctx.Queue();out=ctx.Queue();ram_ready=ctx.Queue()
    workers=[];ram=None;conn=None;cases=0;failed=0;negative=0;why=None;metrics=[];workers_good=0
    prepss=smaps();pre_rss=proc_rss()
    try:
        ram=ctx.Process(target=ramholder,args=(stop,ram_ready));ram.start()
        if ram_ready.get(timeout=10) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(nworkers):
            p=ctx.Process(target=s5worker,args=(binary,stop,ready,out));p.start();workers.append(p)
        if len(set(ready.get(timeout=25) for _ in workers))!=nworkers:raise RuntimeError('NATIVE_S5_NOT_ALL_ACTIVE')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={tag} workers={nworkers}')
        stage_dir=root/tag;stage_dir.mkdir(parents=True,exist_ok=False);db=stage_dir/'v18_concurrent.sqlite3'
        log(f'STAGE_BEGIN stage={tag} expected={expected} slots={N} background_S5={nworkers} held_RAM_MiB=32')
        conn=setup(db,host,log)
        for rep in range(1,3):
            for mode in MODES:
                if reason:=guard(host):why=reason;break
                if inject_abort and cases>=3:why='INJECTED_HOST_SAFETY_ABORT';break
                start=time.monotonic()
                try:
                    ok,detail=mode_case(mode,conn,db,ctx,host,log)
                except BaseException as e:
                    if str(e).startswith('SAFETY_'):why=str(e);break
                    ok=False;detail=f'{type(e).__name__} {str(e)[:240]}'
                ms=(time.monotonic()-start)*1000;metrics.append(ms);cases+=1
                if not ok:failed+=1
                if mode=='CONSENT_TOCTOU_NEGATIVE' and ok:negative+=1
                status=('PASS_EXPECTED_NEGATIVE' if mode=='CONSENT_TOCTOU_NEGATIVE' and ok else 'PASS' if ok else 'FAIL')
                log(f'CASE stage={tag} rep={rep} mode={mode} status={status} {detail} elapsed_ms={ms:.3f}')
            if why:break
        if conn:
            integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity!='ok':failed+=1
            log(f'STORAGE_CHECK stage={tag} integrity={integrity} rows={conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]} audit={conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]}')
            wal=Path(str(db)+'-wal');walsize=wal.stat().st_size if wal.exists() else 0
            log(f'WAL_MEASURE stage={tag} before_final_checkpoint_bytes={walsize} sqlite_db_bytes={db.stat().st_size} own_PSS_kB={smaps()} own_RSS_kB={proc_rss()}')
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            log(f'WAL_CHECKPOINT_END stage={tag} after_bytes={wal.stat().st_size if wal.exists() else 0}')
        floor=1.2 if host else 24 if nworkers==2 else 30
        while not why and time.monotonic()-stage_start<floor:
            if reason:=guard(host):why=reason;break
            time.sleep(.15)
    except BaseException as e:
        if str(e).startswith('SAFETY_'):why=str(e)
        else:
            failed+=1;log(f'STAGE_ERROR stage={tag} error={type(e).__name__} detail={str(e)[:260]}')
    finally:
        if conn:conn.close()
        stop.set()
        for p in workers:
            p.join(4)
            if p.is_alive():p.kill();p.join(3)
        if ram:
            ram.join(4)
            if ram.is_alive():ram.kill();ram.join(3)
        for _ in workers:
            try:
                pid,runs,mean,minval,errors=out.get(timeout=3)
                log(f'S5_WORKER stage={tag} pid={pid} native_runs={runs} mean_GMAC_s={mean:.5f} min_GMAC_s={minval:.5f} errors={errors}')
                if runs>0 and not errors:workers_good+=1
                else:failed+=1
            except queue.Empty:failed+=1;log(f'S5_WORKER stage={tag} RESULT_MISSING')
        for q in (ready,out,ram_ready):q.cancel_join_thread();q.close()
    state='SAFETY_ABORT' if why else 'COMPLETE' if cases==expected and failed==0 and workers_good==nworkers and negative==2 else 'INCOMPLETE_OR_FAIL'
    log(f'STAGE_SUMMARY stage={tag} status={state} cases={cases}/{expected} failures={failed} expected_negative_findings={negative} workers_ok={workers_good}/{nworkers} max_case_ms={max(metrics) if metrics else None} safety_reason={why or "-"}')
    log(f'PROCESS_MEMORY stage={tag} own_PSS_before_kB={prepss} own_PSS_after_kB={smaps()} own_RSS_before_kB={pre_rss} own_RSS_after_kB={proc_rss()} NOTE=single_process_not_total_app_peak')
    log(f'STAGE_TELEMETRY stage={tag} {telemetry()}')
    return state,cases,negative

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--host-smoke',action='store_true',help='developer Linux-only smoke')
    p.add_argument('--native-binary',help='developer smoke only; not allowed on phone')
    p.add_argument('--inject-host-abort',action='store_true',help='developer smoke only')
    a=p.parse_args()
    if (a.native_binary or a.inject_host_abort) and not a.host_smoke:raise SystemExit('HOST_ONLY_OPTIONS')
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_WAL_CONCURRENT_MEMORY_V18_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- CONCURRENT 4096-SLOT SQLITE WAL / CURSOR / REVOCATION LAB UNDER NATIVE S5 LOAD '+VERSION)
            log('One cooperative SQLite writer, concurrent snapshot readers, 4096 actual 4096B records. WAL FULL, real PSS and WAL size measurement. No real private data.')
            log('Charging supported WITH unchanged hardware guards; battery status is observed, not proof of charger thermal safety.')
            log('NEGATIVE consent check-before-read race is NOT fixed by cooperative SQLite; Android trust boundary and physical STOP remain untested.')
            log('No weight training, P updates, production code, Binder, OS dispatch, real microphone, readback or power cut.')
            log('SAFETY battery>=40% temp<37.5C MemAvailable>=400000kB. SAFETY_ABORT != COMPLETE.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            log(f'PRECHECK {telemetry()}')
            if reason:=guard(a.host_smoke):log('RESULT SAFETY_SKIP '+reason);return 3
            root_parent=home/'uno_a52_r41_wal_concurrent_v18'
            root_parent.mkdir(parents=True,exist_ok=True)
            if not a.host_smoke and shutil.disk_usage(root_parent).free<192*MIB:
                log('RESULT SAFETY_SKIP DISK_FREE_BELOW_192_MiB');return 3
            binary=native_binary(a.host_smoke,a.native_binary);log('VERIFIED_BACKGROUND_NATIVE_S5 '+str(binary))
            root=root_parent/stamp;root.mkdir(parents=True,exist_ok=False)
            ctx=mp.get_context('fork')
            one=runstage(log,ctx,binary,root,1 if a.host_smoke else 2,a.host_smoke,a.inject_host_abort)
            if one[0]!='COMPLETE':log(f'RESULT {one[0]} completed={one[1]}');return 3
            two=runstage(log,ctx,binary,root,2 if a.host_smoke else 4,a.host_smoke,False)
            if two[0]!='COMPLETE':log(f'RESULT {two[0]} completed={one[1]+two[1]}');return 3
            log(f'RESULT COMPLETE_CONCURRENT_WAL_LAB stages=2/2 cases={one[1]+two[1]} expected_negative_findings={one[2]+two[2]}')
            log('LIMIT: local SQLite snapshot guarantees != Android permission isolation or atomic permission/read operation; no hard real-time deadline, energy, power cut or full Android RSS proof.')
            return 0
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:260]}')
            log('TRACE '+traceback.format_exc()[-1500:]);return 2
        finally:log('REPORT '+str(report))
if __name__=='__main__':sys.exit(main())
