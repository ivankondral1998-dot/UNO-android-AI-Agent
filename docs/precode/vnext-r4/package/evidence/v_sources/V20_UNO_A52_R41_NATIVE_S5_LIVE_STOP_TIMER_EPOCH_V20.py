#!/usr/bin/env python3
"""UNO R4.1 V20: live STOP/TIMER vs in-flight native F laboratory.

Isolated Termux fixture. NO Android authority, STOP integration, OS actions,
trained weights, P changes, or production code. This is cooperative same-UID
SQLite and a cross-process event; same-UID interference remains a negative risk.
"""
from __future__ import annotations
import argparse
import datetime as dt
import multiprocessing as mp
import os
from pathlib import Path
import queue
import re
import sqlite3
import statistics
import subprocess
import time
import traceback
import uuid

VERSION='UNO_R41_A52_NATIVE_S5_LIVE_STOP_TIMER_EPOCH_V20'
MIB=1048576
MODES=(
 'STOP_DURING_NATIVE_F','REVOKE_DURING_NATIVE_F','BOOT_DURING_NATIVE_F',
 'DEADLINE_DURING_NATIVE_F','DUE_TIMER_DURING_NATIVE_F',
 'STOP_AND_DUE_TIMER_DURING_NATIVE_F','NEURAL_FINISH_NO_CONTROL',
 'STOP_BEFORE_F_NO_PULSE','STOP_AFTER_COMMIT_HISTORY_PRESERVED',
 'REVOKE_REGRANT_OLD_TOKEN_STALE','KILLED_NATIVE_F_NO_COMMIT',
 'NAIVE_STALE_RESULT_NEGATIVE',
)
LIVE={
 'STOP_DURING_NATIVE_F','REVOKE_DURING_NATIVE_F','BOOT_DURING_NATIVE_F',
 'DEADLINE_DURING_NATIVE_F','DUE_TIMER_DURING_NATIVE_F',
 'STOP_AND_DUE_TIMER_DURING_NATIVE_F','REVOKE_REGRANT_OLD_TOKEN_STALE',
 'KILLED_NATIVE_F_NO_COMMIT','NAIVE_STALE_RESULT_NEGATIVE',
}
NEG={'NAIVE_STALE_RESULT_NEGATIVE'}

def readint(p):
    try:return int(Path(p).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
    except (OSError,StopIteration,ValueError):mem=None
    try:charge=Path('/sys/class/power_supply/battery/status').read_text().strip()
    except OSError:charge='UNKNOWN'
    return {'battery':readint('/sys/class/power_supply/battery/capacity'),
            'temp_deciC':readint('/sys/class/power_supply/battery/temp'),
            'MemAvailable_kB':mem,'charge':charge}

def guard(host):
    if host:return None
    t=telemetry();b=t['battery'];h=t['temp_deciC'];m=t['MemAvailable_kB']
    if None in (b,h,m) or not 100<=h<=800:return 'SAFETY_TELEMETRY_UNAVAILABLE'
    if b<40:return 'SAFETY_BATTERY_BELOW_40_PERCENT'
    if h>=375:return 'SAFETY_BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'SAFETY_MEMAVAILABLE_LT_400000_KB'
    return None

def native_binary(host,override):
    p=Path(override) if host and override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_MISSING '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=15)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_S5_CONTRACT_NOT_PASS '+r.stdout[-200:])
    return p

def s5worker(binary,stop,ready,out):
    vals=[];errors=[]
    try:
        while not stop.is_set():
            r=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=18)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
                raise RuntimeError('BACKGROUND_NATIVE_S5_FAILED')
            match=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not match:raise RuntimeError('BACKGROUND_NATIVE_THROUGHPUT_MISSING')
            vals.append(float(match[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=5)
    except BaseException as e:errors.append(str(e)[:160])
    try:out.put((os.getpid(),len(vals),statistics.mean(vals) if vals else None,
                 min(vals) if vals else None,errors),timeout=3)
    except BaseException:pass

def ramholder(stop,ready):
    try:
        buf=bytearray(32*MIB)
        for i in range(0,len(buf),4096):buf[i]=1
        ready.put(True,timeout=5)
        while not stop.wait(.15):
            for i in range(0,len(buf),262144):buf[i]^=1
    except BaseException:
        try:ready.put(False,timeout=3)
        except BaseException:pass

def connect(path):
    db=sqlite3.connect(str(path),isolation_level=None,timeout=3.0)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    return db

def make_db(path):
    with connect(path) as db:
        db.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL, boot INTEGER NOT NULL, consent INTEGER NOT NULL, stopped INTEGER NOT NULL, dead INTEGER NOT NULL, deadline_ns INTEGER NOT NULL, timer_due INTEGER NOT NULL, timer_used INTEGER NOT NULL, accepted INTEGER NOT NULL, denied INTEGER NOT NULL, last_status TEXT NOT NULL)')
        db.execute('CREATE TABLE journal(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, at_ns INTEGER NOT NULL, epoch INTEGER NOT NULL)')
        deadline=time.monotonic_ns()+60_000_000_000
        db.execute('INSERT INTO state VALUES(1,1,1,1,0,0,?,0,0,0,0,?)',(deadline,'INITIAL'))

def record(db,kind):
    db.execute('INSERT INTO journal(kind,at_ns,epoch) VALUES(?,?,(SELECT epoch FROM state WHERE id=1))',(kind,time.monotonic_ns()))

def event(db,kind):
    """Same-UID cooperative synthetic ingress; serialized transactional writes."""
    db.execute('BEGIN IMMEDIATE')
    try:
        if kind=='STOP':db.execute('UPDATE state SET stopped=1,epoch=epoch+1 WHERE id=1')
        elif kind=='REVOKE':db.execute('UPDATE state SET consent=0,epoch=epoch+1 WHERE id=1')
        elif kind=='REGRANT':db.execute('UPDATE state SET consent=1,epoch=epoch+1 WHERE id=1')
        elif kind=='BOOT':db.execute('UPDATE state SET boot=boot+1,epoch=epoch+1 WHERE id=1')
        elif kind=='DEADLINE':db.execute('UPDATE state SET deadline_ns=?,epoch=epoch+1 WHERE id=1',(time.monotonic_ns(),))
        elif kind=='TIMER':
            # Control already wins the ordering; a due timer cannot resume a STOPped session.
            if state(db)['stopped']:
                record(db,'TIMER_IGNORED_STOPPED');db.execute('COMMIT');return
            db.execute('UPDATE state SET timer_due=timer_due+1,epoch=epoch+1 WHERE id=1')
        elif kind=='DEATH':db.execute('UPDATE state SET dead=1,epoch=epoch+1 WHERE id=1')
        else:raise ValueError('BAD_EVENT')
        record(db,kind);db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK');raise

def state(db):
    row=db.execute('SELECT epoch,boot,consent,stopped,dead,deadline_ns,timer_due,timer_used,accepted,denied,last_status FROM state WHERE id=1').fetchone()
    return dict(zip(('epoch','boot','consent','stopped','dead','deadline','due','used','accepted','denied','status'),row))

def token(db):
    s=state(db);return {'epoch':s['epoch'],'boot':s['boot'],'deadline':s['deadline']}

def commit_result(db,tok,naive=False):
    """Never dispatch an OS action; just count a synthetic accepted result."""
    db.execute('BEGIN IMMEDIATE')
    try:
        s=state(db);now=time.monotonic_ns()
        allowed=(s['epoch']==tok['epoch'] and s['boot']==tok['boot'] and
                 s['consent']==1 and s['stopped']==0 and s['dead']==0 and
                 now<s['deadline'] and s['due']==s['used'])
        if naive:allowed=True  # INTENTIONAL NEGATIVE: no epoch / STOP check
        status='ACCEPTED' if allowed else ('DUE_EVENT_FIRST' if s['due']>s['used'] else 'REJECTED_STALE')
        if allowed:db.execute('UPDATE state SET accepted=accepted+1,last_status=? WHERE id=1',(status,))
        else:db.execute('UPDATE state SET denied=denied+1,last_status=? WHERE id=1',(status,))
        record(db,'NAIVE_RESULT' if naive else 'RESULT_'+status)
        db.execute('COMMIT');return status
    except BaseException:
        db.execute('ROLLBACK');raise

def consume_timer(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        s=state(db)
        if s['due']<=s['used']:raise RuntimeError('NO_TIMER_TO_CONSUME')
        db.execute('UPDATE state SET timer_used=timer_used+1 WHERE id=1')
        record(db,'TIMER_CONSUMED');db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK');raise

def control_actor(path,kinds,go,ready,result):
    """Independent OS process, but SAME Linux UID, not a protected controller."""
    try:
        db=connect(path);ready.put(os.getpid(),timeout=4)
        if not go.wait(8):raise RuntimeError('CONTROL_GO_TIMEOUT')
        start=time.monotonic_ns()
        for kind in kinds:event(db,kind)
        done=time.monotonic_ns();result.put((True,start,done,None),timeout=4)
        db.close()
    except BaseException as e:
        try:result.put((False,0,0,f'{type(e).__name__}:{str(e)[:120]}'),timeout=4)
        except BaseException:pass

def run_native(binary,kill=False):
    proc=subprocess.Popen([str(binary),'rank','prefix2','0.30'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    t0=time.monotonic_ns()
    if kill:
        time.sleep(.035)
        alive=proc.poll() is None
        if alive:proc.terminate()
        try:so,se=proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();so,se=proc.communicate(timeout=3)
        return alive,proc.returncode,t0,time.monotonic_ns(),so
    try:so,se=proc.communicate(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill();proc.communicate(timeout=3);raise RuntimeError('NATIVE_F_TIMEOUT')
    end=time.monotonic_ns()
    if proc.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',so):
        raise RuntimeError('NATIVE_F_CONTRACT_FAIL '+so[-160:]+' '+se[-100:])
    return True,proc.returncode,t0,end,so

def one_case(mode,dbpath,binary,ctx):
    make_db(dbpath)
    db=connect(dbpath);tok=token(db)
    control_kinds={
       'STOP_DURING_NATIVE_F':['STOP'],
       'REVOKE_DURING_NATIVE_F':['REVOKE'],
       'BOOT_DURING_NATIVE_F':['BOOT'],
       'DEADLINE_DURING_NATIVE_F':['DEADLINE'],
       'DUE_TIMER_DURING_NATIVE_F':['TIMER'],
       'STOP_AND_DUE_TIMER_DURING_NATIVE_F':['STOP','TIMER'],
       'REVOKE_REGRANT_OLD_TOKEN_STALE':['REVOKE','REGRANT'],
       'NAIVE_STALE_RESULT_NEGATIVE':['STOP'],
    }
    issue='NONE';during=False;latency_ms=None;native_ms=None;negative=False
    if mode in control_kinds:
        go=ctx.Event();ready=ctx.Queue();out=ctx.Queue()
        actor=ctx.Process(target=control_actor,args=(dbpath,control_kinds[mode],go,ready,out))
        actor.start()
        try:
            ready.get(timeout=8)
            proc=subprocess.Popen([str(binary),'rank','prefix2','0.30'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            launch=time.monotonic_ns()
            time.sleep(.030)
            if proc.poll() is not None:
                proc.communicate(timeout=4);raise RuntimeError('NATIVE_F_TOO_FAST_TO_OBSERVE_RACE')
            go.set()
            ok,ingress_start,ingress_done,err=out.get(timeout=6)
            if not ok:raise RuntimeError('CONTROL_FAILED '+str(err))
            try:so,se=proc.communicate(timeout=12)
            except subprocess.TimeoutExpired:
                proc.kill();proc.communicate(timeout=3);raise RuntimeError('NATIVE_F_TIMEOUT')
            finished=time.monotonic_ns();native_ms=(finished-launch)/1e6
            during=launch<=ingress_start<=ingress_done<finished
            latency_ms=(ingress_done-ingress_start)/1e6
            if proc.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',so):
                raise RuntimeError('NATIVE_F_CONTRACT_FAIL '+so[-180:]+se[-150:])
            if not during:raise RuntimeError('CONTROL_NOT_CONFIRMED_DURING_NATIVE_F')
            issue=commit_result(db,tok,naive=mode=='NAIVE_STALE_RESULT_NEGATIVE')
            actor.join(4)
            if actor.exitcode!=0:raise RuntimeError('CONTROL_ACTOR_NOT_CLEAN')
        finally:
            go.set()
            if actor.is_alive():actor.kill();actor.join(2)
            if 'proc' in locals() and proc.poll() is None:
                proc.kill();proc.communicate(timeout=3)
            for q in (ready,out):q.cancel_join_thread();q.close()
    elif mode=='NEURAL_FINISH_NO_CONTROL':
        ok,code,launch,finished,so=run_native(binary)
        native_ms=(finished-launch)/1e6;issue=commit_result(db,tok)
        assert issue=='ACCEPTED'
    elif mode=='STOP_BEFORE_F_NO_PULSE':
        event(db,'STOP')
        issue=commit_result(db,tok)
        # F must NOT be invoked after STOP; inspect the recorded absence only.
    elif mode=='STOP_AFTER_COMMIT_HISTORY_PRESERVED':
        ok,code,launch,finished,so=run_native(binary)
        native_ms=(finished-launch)/1e6
        first=commit_result(db,tok)
        event(db,'STOP');second=commit_result(db,tok)
        issue=f'{first}/{second}'
    elif mode=='KILLED_NATIVE_F_NO_COMMIT':
        alive,code,launch,finished,so=run_native(binary,kill=True)
        native_ms=(finished-launch)/1e6
        # Native output does not authorize a commit after a killed worker.
        event(db,'DEATH');issue='NO_RESULT_NO_COMMIT'
        if not alive or code==0:raise RuntimeError('KILL_DID_NOT_INTERRUPT_NATIVE_F')
    else:raise ValueError('UNKNOWN_MODE')

    if mode=='DUE_TIMER_DURING_NATIVE_F':
        before=state(db);consume_timer(db);after=state(db)
        ok=(issue=='DUE_EVENT_FIRST' and before['due']==1 and before['used']==0 and after['used']==1)
    elif mode=='STOP_AND_DUE_TIMER_DURING_NATIVE_F':
        s=state(db)
        ignored=db.execute("SELECT COUNT(*) FROM journal WHERE kind='TIMER_IGNORED_STOPPED'").fetchone()[0]
        ok=(issue=='REJECTED_STALE' and s['stopped']==1 and s['due']==0
            and s['accepted']==0 and ignored==1)
    elif mode=='REVOKE_REGRANT_OLD_TOKEN_STALE':
        s=state(db);ok=(issue=='REJECTED_STALE' and s['consent']==1 and s['epoch']==3 and s['accepted']==0)
    elif mode=='STOP_AFTER_COMMIT_HISTORY_PRESERVED':
        s=state(db);ok=(issue=='ACCEPTED/REJECTED_STALE' and s['accepted']==1 and s['stopped']==1)
    elif mode=='STOP_BEFORE_F_NO_PULSE':
        ok=(issue=='REJECTED_STALE' and state(db)['accepted']==0 and native_ms is None)
    elif mode=='KILLED_NATIVE_F_NO_COMMIT':
        ok=(state(db)['accepted']==0 and state(db)['dead']==1)
    elif mode=='NAIVE_STALE_RESULT_NEGATIVE':
        s=state(db);negative=(issue=='ACCEPTED' and s['stopped']==1 and s['accepted']==1)
        ok=negative
    else:
        expected='ACCEPTED' if mode=='NEURAL_FINISH_NO_CONTROL' else 'REJECTED_STALE'
        s=state(db);ok=(issue==expected and s['accepted']==(1 if expected=='ACCEPTED' else 0))
    integ=db.execute('PRAGMA quick_check').fetchone()[0]
    j=db.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
    db.close()
    if integ!='ok':ok=False
    return ok,negative,(f'issue={issue} live_control_during_F={during} control_commit_ms={round(latency_ms,3) if latency_ms is not None else "NA"} '
                        f'native_F_wall_ms={round(native_ms,3) if native_ms is not None else "SKIPPED"} '
                        f'journal_rows={j} sqlite_integrity={integ}')

def stage(log,ctx,binary,n,root,host,inject):
    name=f'S5x{n}_RAM32';expected=len(MODES)*2
    stop=ctx.Event();ready=ctx.Queue();out=ctx.Queue();rready=ctx.Queue()
    processes=[];ram=None;start=time.monotonic()
    cases=0;errors=0;negative=0;live_cases=0;good=0;why=None;max_ms=0.
    try:
        ram=ctx.Process(target=ramholder,args=(stop,rready));ram.start()
        if rready.get(timeout=10)!=True:raise RuntimeError('RAM_HOLDER_NOT_READY')
        for _ in range(n):
            p=ctx.Process(target=s5worker,args=(binary,stop,ready,out));p.start();processes.append(p)
        if len(set(ready.get(timeout=25) for _ in range(n)))!=n:raise RuntimeError('BACKGROUND_S5_NOT_ACTIVE')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={name} workers={n}')
        log(f'STAGE_BEGIN stage={name} scenarios={expected} modes={len(MODES)} RAM_MiB=32')
        for rep in (1,2):
            for mode in MODES:
                if why:=guard(host):break
                if inject and cases>=3:why='INJECTED_HOST_SAFETY_ABORT';break
                at=time.monotonic();ok=False;neg=False;details=''
                try:
                    path=root/f'{name}_r{rep}_{mode}.sqlite3'
                    ok,neg,details=one_case(mode,path,binary,ctx)
                except BaseException as e:
                    details=f'exception={type(e).__name__}:{str(e)[:170]}'
                elapsed=(time.monotonic()-at)*1000;max_ms=max(max_ms,elapsed)
                cases+=1;errors+=int(not ok);negative+=int(neg);live_cases+=int(mode in LIVE)
                status='FAIL' if not ok else 'PASS_EXPECTED_NEGATIVE' if neg else 'PASS'
                log(f'CASE stage={name} rep={rep} mode={mode} status={status} {details} elapsed_ms={elapsed:.3f}')
            if why:break
        floor=0 if host else (24 if n==2 else 30)
        while not why and time.monotonic()-start<floor:
            if why:=guard(host):break
            time.sleep(.15)
    except BaseException as e:
        errors+=1;log(f'STAGE_ERROR stage={name} kind={type(e).__name__} error={str(e)[:240]}')
    finally:
        stop.set()
        for p in processes:
            p.join(5)
            if p.is_alive():p.kill();p.join(2)
        if ram:
            ram.join(4)
            if ram.is_alive():ram.kill();ram.join(2)
        for _ in processes:
            try:
                pid,runs,mean,minimum,err=out.get(timeout=3)
                log(f'S5_WORKER stage={name} pid={pid} runs={runs} mean_GMAC_s={mean} min_GMAC_s={minimum} errors={err}')
                if runs>0 and not err:good+=1
                else:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={name} NO_RESULT')
        for q in (ready,out,rready):q.cancel_join_thread();q.close()
    status='SAFETY_ABORT' if why else 'COMPLETE' if cases==expected and errors==0 and negative==2 and good==n else 'INCOMPLETE_OR_FAIL'
    log(f'STAGE_SUMMARY stage={name} status={status} cases={cases}/{expected} failures={errors} '
        f'negative_findings={negative} live_native_races={live_cases} workers_ok={good}/{n} '
        f'case_max_ms={max_ms:.3f} safety_reason={why or "-"}')
    log(f'STAGE_TELEMETRY stage={name} {telemetry()}')
    return status,cases,negative

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--host-smoke',action='store_true')
    p.add_argument('--native-binary')
    p.add_argument('--inject-host-abort',action='store_true')
    a=p.parse_args()
    if (a.native_binary or a.inject_host_abort) and not a.host_smoke:raise SystemExit('HOST_ONLY_OPTIONS')
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    path=downloads/f'UNO_A52_R41_LIVE_STOP_TIMER_EPOCH_V20_{stamp}.txt'
    with path.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        log(f'UNO / UNOVYRA -- REAL NATIVE F IN-FLIGHT vs STOP / REVOKE / TIMER EPOCH LAB {VERSION}')
        log('R4.1 S2/S3/S23: independent same-UID control PROCESS during native C256R32 F, epoch invalidation and durable SQLite journal; real monotonic times.')
        log('Negative: naive stale result accepted after STOP if epoch check omitted. No OS dispatch, Android protected STOP, real model learning, real permissions or user data.')
        log('2/4 native S5 background workers, 32MiB RAM; no idle load stage. Live native F race is required, not virtual only.')
        log('SAFETY battery>=40%, temp<37.5C, MemAvailable>=400000kB, charger allowed with same thresholds.')
        log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
        log(f'PRECHECK {telemetry()}')
        if why:=guard(a.host_smoke):log('RESULT SAFETY_ABORT reason='+why);return 3
        try:b=native_binary(a.host_smoke,a.native_binary)
        except BaseException as e:log(f'PRECHECK_FAIL {type(e).__name__}: {e}');return 4
        log('VERIFIED_BACKGROUND_NATIVE_S5 '+str(b))
        fixture_root=home/'uno_a52_r41_live_stop_timer_v20'/stamp
        fixture_root.mkdir(parents=True,exist_ok=False)
        log('FIXTURE_ROOT '+str(fixture_root))
        ctx=mp.get_context('fork')
        workers=(1,2) if a.host_smoke else (2,4)
        results=[]
        for n in workers:
            result=stage(log,ctx,b,n,fixture_root,a.host_smoke,a.inject_host_abort)
            results.append(result)
            if result[0]!='COMPLETE':break
        good=all(s=='COMPLETE' for s,c,neg in results)
        log(f'RESULT {"COMPLETE_LIVE_STOP_TIMER_EPOCH_LAB" if good else "SAFETY_ABORT" if any(s=="SAFETY_ABORT" for s,c,neg in results) else "INCOMPLETE_OR_FAIL"} '
            f'stages={sum(s=="COMPLETE" for s,c,neg in results)}/{len(results)} cases={sum(c for s,c,neg in results)} '
            f'expected_naive_negative={sum(neg for s,c,neg in results)}')
        log('LIMIT: same UID can forge SQLite state/control; wall-clock bound and cancellation of OS effect not proven. The latch is cooperative, not trusted Android.')
        log('REPORT '+str(path))
        return 0 if good else 3 if any(s=='SAFETY_ABORT' for s,c,neg in results) else 5

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('INTERRUPTED != COMPLETE',flush=True);raise SystemExit(130)
