#!/usr/bin/env python3
"""UNO R4.1 experimental (not production): durable STOP vs receipt commit ordering.
Runs under 2/4 *native* FP32 C256R32 S5 workers on A52 in Termux.
No Android capabilities, actual owner STOP, external dispatch, neural learning, or release claim.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse
import datetime as datetime
import multiprocessing as mp
import os
import queue
import re
import signal
import sqlite3
import subprocess
import sys
import time
import traceback
from pathlib import Path

VERSION='UNO_R41_A52_S5_DURABLE_STOP_ORDER_STRESS_V3'
MIB=1024*1024

def read_int(path):
    try: return int(Path(path).read_text().strip())
    except (ValueError, OSError): return None

def mem_avail():
    try:
        for s in Path('/proc/meminfo').read_text().splitlines():
            if s.startswith('MemAvailable:'): return int(s.split()[1])
    except (OSError, ValueError, IndexError): pass
    return None

def metrics():
    return read_int('/sys/class/power_supply/battery/capacity'), read_int('/sys/class/power_supply/battery/temp'), mem_avail()

def safety(quick):
    b,t,m=metrics()
    if quick: return None
    if b is None or t is None or m is None or t<100 or t>800: return 'REQUIRED_SENSOR_UNAVAILABLE'
    if b<40: return 'BATTERY_LT_40'
    if t>=375: return 'BATTERY_GE_37_5_C'
    if m<400000: return 'MEMAVAILABLE_LT_400000_KB'
    return None

def connect(path):
    db=sqlite3.connect(str(path), timeout=10.0, isolation_level=None)
    db.execute('PRAGMA busy_timeout=10000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    return db

def initialize(path):
    c=connect(path)
    try:
        c.execute('CREATE TABLE gate (id INTEGER PRIMARY KEY CHECK (id=1), epoch INTEGER NOT NULL, stopped INTEGER NOT NULL, stop_ns INTEGER)')
        c.execute('INSERT INTO gate VALUES (1,1,0,NULL)')
        for name in ('receipts','memory','plasticity'):
            c.execute('CREATE TABLE '+name+'(ticket TEXT PRIMARY KEY, epoch INTEGER NOT NULL)')
    finally: c.close()

def inspect(path):
    c=connect(path)
    try:
        state=tuple(c.execute('SELECT epoch,stopped FROM gate WHERE id=1').fetchone())
        records=[set(c.execute('SELECT ticket,epoch FROM '+name).fetchall()) for name in ('receipts','memory','plasticity')]
        return {'state':state, 'rows':len(records[0]), 'atomic':records[0]==records[1]==records[2],
                'integrity':c.execute('PRAGMA integrity_check').fetchone()[0]}
    finally: c.close()

def commit_once(path,ticket='T1',epoch=1):
    c=connect(path)
    try:
        c.execute('BEGIN IMMEDIATE')
        e,stop=c.execute('SELECT epoch,stopped FROM gate WHERE id=1').fetchone()
        if stop or epoch!=e:
            c.execute('ROLLBACK');return 'STOPPED_OR_STALE', None
        if c.execute('SELECT 1 FROM receipts WHERE ticket=?',(ticket,)).fetchone():
            c.execute('ROLLBACK');return 'DUPLICATE',None
        for tab in ('receipts','memory','plasticity'):
            c.execute('INSERT INTO '+tab+' VALUES (?,?)',(ticket,epoch))
        c.execute('COMMIT')
        return 'COMMITTED',time.monotonic_ns()
    finally:
        if c.in_transaction: c.execute('ROLLBACK')
        c.close()

def stop_actor(path,channel,mode):
    c=None
    try:
        c=connect(path)
        channel.send(('READY',os.getpid()))
        if not channel.poll(12): raise TimeoutError('STOP_REQUEST_TIMEOUT')
        item=channel.recv()
        if item[0]!='STOP': raise ValueError('UNEXPECTED_STOP_MESSAGE')
        received=time.monotonic_ns()
        channel.send(('RECEIVED',received))
        c.execute('BEGIN IMMEDIATE')
        c.execute('UPDATE gate SET epoch=2,stopped=1,stop_ns=? WHERE id=1',(received,))
        if mode=='HOLD':
            channel.send(('HELD',time.monotonic_ns()))
            if not channel.poll(12): raise TimeoutError('STOP_RELEASE_TIMEOUT')
            if channel.recv()!=('RELEASE',): raise ValueError('STOP_RELEASE_BAD')
        c.execute('COMMIT')
        durable=time.monotonic_ns()
        channel.send(('ACK',durable))
        if mode=='ACK_THEN_WAIT':
            # Parent deliberately kills this still-live process after ACK.
            if not channel.poll(15): raise TimeoutError('PARENT_DID_NOT_CRASH_STOP_ACTOR')
            channel.recv()
    except BaseException as ex:
        try: channel.send(('ERROR',type(ex).__name__,str(ex)[:120]))
        except Exception: pass
    finally:
        if c is not None:
            try:
                if c.in_transaction:c.execute('ROLLBACK')
                c.close()
            except Exception:pass
        channel.close()

def held_commit_actor(path,crash_after_commit,channel):
    c=None
    try:
        c=connect(path)
        c.execute('BEGIN IMMEDIATE')
        e,stop=c.execute('SELECT epoch,stopped FROM gate WHERE id=1').fetchone()
        if e!=1 or stop: raise RuntimeError('EXPECTED_UNSTOPPED')
        for tab in ('receipts','memory','plasticity'):
            c.execute('INSERT INTO '+tab+' VALUES (?,?)',('T1',1))
        channel.send(('HELD',os.getpid()))
        if not channel.poll(12): raise TimeoutError('COMMIT_RELEASE_TIMEOUT')
        if channel.recv()!=('RELEASE',): raise RuntimeError('COMMIT_RELEASE_BAD')
        c.execute('COMMIT')
        committed=time.monotonic_ns()
        if crash_after_commit:
            # Deliberate crash after durable local commit and before any user-level ACK.
            os._exit(42)
        channel.send(('COMMITTED',committed))
    except BaseException as ex:
        try:channel.send(('ERROR',type(ex).__name__,str(ex)[:120]))
        except Exception:pass
    finally:
        if c is not None:
            try:
                if c.in_transaction:c.execute('ROLLBACK')
                c.close()
            except Exception:pass
        channel.close()

def commit_actor(path,channel,ticket='T1'):
    try:
        channel.send(('TRYING',os.getpid()))
        out,ns=commit_once(path,ticket)
        channel.send(('RESULT',out,ns))
    except BaseException as ex:
        try:channel.send(('ERROR',type(ex).__name__,str(ex)[:120]))
        except Exception:pass
    finally:channel.close()

def get(c,expected,timeout=12):
    if not c.poll(timeout):raise TimeoutError('IPC_WAIT_'+expected)
    v=c.recv()
    if v[0]=='ERROR':raise RuntimeError(str(v))
    if v[0]!=expected:raise RuntimeError('EXPECTED_'+expected+'_GOT_'+str(v))
    return v

def make_process(ctx,target,args):
    parent,child=ctx.Pipe(duplex=True)
    p=ctx.Process(target=target,args=(*args,child))
    p.start();child.close()
    return p,parent

def _stop_process(ctx,db,mode):
    parent,child=ctx.Pipe(duplex=True)
    p=ctx.Process(target=stop_actor,args=(str(db),child,mode))
    p.start();child.close()
    get(parent,'READY')
    return p,parent

def join_checked(p,expected_exit=0):
    p.join(4)
    if p.is_alive():raise TimeoutError('CHILD_DID_NOT_EXIT')
    if p.exitcode!=expected_exit:raise RuntimeError('CHILD_EXIT_'+str(p.exitcode))

def release_process(p):
    if p.is_alive():p.kill()
    p.join(2)

def tested_case(ctx,db,mode):
    initialize(db)
    actors=[]
    times={}
    try:
        if mode=='STOP_LATCH_FIRST':
            stop,ch=_stop_process(ctx,db,'DIRECT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1]
            times['latch']=get(ch,'ACK')[1]
            join_checked(stop)
            out,ns=commit_once(db)
            expected=out=='STOPPED_OR_STALE' and ns is None
            label='STOP_BLOCKED_FUTURE_COMMIT'
        elif mode=='COMMIT_FIRST':
            out,times['commit']=commit_once(db)
            stop,ch=_stop_process(ctx,db,'DIRECT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1]
            times['latch']=get(ch,'ACK')[1]
            join_checked(stop)
            expected=out=='COMMITTED' and times['commit']<times['request']
            label='PAST_COMMIT_RETAINED'
        elif mode=='STOP_LOCK_FIRST':
            stop,ch=_stop_process(ctx,db,'HOLD');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1];get(ch,'HELD')
            cp,cc=make_process(ctx,commit_actor,(str(db),));actors.append((cp,cc))
            get(cc,'TRYING')
            time.sleep(.012)  # force competing writer to wait on gate lock
            ch.send(('RELEASE',))
            times['latch']=get(ch,'ACK')[1]
            out=get(cc,'RESULT');times['commit']=out[2]
            join_checked(stop);join_checked(cp)
            expected=out[1]=='STOPPED_OR_STALE' and times['commit'] is None
            label='STOP_TX_WINS_DB_ORDER'
        elif mode=='WRITER_LOCK_FIRST':
            cp,cc=make_process(ctx,held_commit_actor,(str(db),False));actors.append((cp,cc))
            get(cc,'HELD')
            stop,ch=_stop_process(ctx,db,'DIRECT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1]
            time.sleep(.012)  # writer deliberately holds BEGIN IMMEDIATE lock across STOP request
            cc.send(('RELEASE',))
            times['commit']=get(cc,'COMMITTED')[1]
            times['latch']=get(ch,'ACK')[1]
            join_checked(cp);join_checked(stop)
            expected=times['request']<times['commit']<times['latch']
            label='REQUEST_BEFORE_COMMIT_BUT_DB_ORDER_COMMIT_FIRST'
        elif mode=='CRASH_AFTER_STOP_ACK':
            stop,ch=_stop_process(ctx,db,'ACK_THEN_WAIT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1];times['latch']=get(ch,'ACK')[1]
            if not stop.is_alive(): raise RuntimeError('STOP_ACTOR_EXITED_BEFORE_FORCED_CRASH')
            stop.kill();stop.join(3)
            if stop.is_alive():raise RuntimeError('STOP_ACTOR_NOT_KILLED_AFTER_ACK')
            # ACK already durable; a new controller must enforce it without volatile RAM.
            out,ns=commit_once(db)
            expected=out=='STOPPED_OR_STALE'
            label='DURABLE_ACK_SURVIVES_NEW_CONTROLLER'
        elif mode=='CRASH_PRE_STOP_ACK':
            stop,ch=_stop_process(ctx,db,'HOLD');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1];get(ch,'HELD')
            stop.kill();stop.join(3)
            if stop.is_alive():raise RuntimeError('STOP_PROCESS_STUCK')
            prior=inspect(db)
            # This negative control demonstrates the consequence: after process death,
            # a *new* ticket writer can commit because the unacknowledged STOP vanished.
            replay_status,_=commit_once(db,'T_AFTER_UNACKED_CRASH')
            expected=prior['state']==(1,0) and prior['rows']==0 and replay_status=='COMMITTED'
            label='UNACKED_STOP_LOST_AND_RESTART_COMMIT_ALLOWED'
        elif mode=='REPLAY_QUEUE_32':
            stop,ch=_stop_process(ctx,db,'DIRECT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1];times['latch']=get(ch,'ACK')[1]
            join_checked(stop)
            out=[commit_once(db,'T'+str(i))[0] for i in range(32)]
            expected=all(s=='STOPPED_OR_STALE' for s in out)
            label='ALL_32_POST_STOP_DENIED'
        elif mode=='COMMIT_NO_ACK_DEDUP':
            cp,cc=make_process(ctx,held_commit_actor,(str(db),True));actors.append((cp,cc))
            get(cc,'HELD');cc.send(('RELEASE',))
            join_checked(cp,42)
            pre=inspect(db)
            replay,ticket=commit_once(db,'T1')
            stop,ch=_stop_process(ctx,db,'DIRECT');actors.append((stop,ch))
            times['request']=time.monotonic_ns();ch.send(('STOP',))
            times['receive']=get(ch,'RECEIVED')[1];times['latch']=get(ch,'ACK')[1]
            join_checked(stop)
            expected=pre['rows']==1 and replay=='DUPLICATE' and ticket is None
            label='DURABLE_COMMIT_REPLAY_DEDUP'
        else: raise ValueError('UNKNOWN_CASE_'+mode)
        data=inspect(db)
        expected=expected and data['integrity']=='ok' and data['atomic']
        if mode in ('STOP_LATCH_FIRST','STOP_LOCK_FIRST','CRASH_AFTER_STOP_ACK','REPLAY_QUEUE_32'):
            expected=expected and data['rows']==0
        else:
            expected=expected and data['rows']==1
        if mode!='CRASH_PRE_STOP_ACK':expected=expected and data['state']==(2,1)
        return {'case':mode,'status':'PASS' if expected else 'FAIL','label':label,'data':data,
                'request_to_receive_ms':(times['receive']-times['request'])/1e6 if 'receive' in times else None,
                'request_to_latch_ms':(times['latch']-times['request'])/1e6 if 'latch' in times else None,
                'commit_minus_request_ms':(times['commit']-times['request'])/1e6 if times.get('commit') is not None and 'request' in times else None,
                'negative_control':mode in ('WRITER_LOCK_FIRST','CRASH_PRE_STOP_ACK')}
    finally:
        for p,c in actors:
            release_process(p)
            c.close()

def native_worker(binary,event,result):
    values=[];errs=[]
    while not event.is_set():
        try:
            p=subprocess.run([binary,'rank','full','0.75'],capture_output=True,text=True,timeout=4)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):
                errs.append('S5_BAD_EXIT_OR_CONTRACT');break
            m=re.search(r'estimated_F_GMAC_s=([\d.]+)',p.stdout)
            if not m:errs.append('S5_MISSING_RATE');break
            values.append(float(m.group(1)))
        except BaseException as ex:
            errs.append(type(ex).__name__+':'+str(ex)[:90]);break
    try:result.put((os.getpid(),len(values),min(values) if values else None, sum(values)/len(values) if values else None,errs),timeout=2)
    except Exception:pass

def hold_ram(mib,event,ready):
    try:
        block=bytearray(mib*MIB)
        for i in range(0,len(block),4096):block[i]=1
        ready.put(('READY',os.getpid()),timeout=2)
        while not event.wait(.3):
            for i in range(0,len(block),4096*64):block[i]^=1
    except BaseException as ex:
        try:ready.put(('ERROR',str(ex)),timeout=1)
        except Exception:pass

def check_binary():
    path=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not (path.is_file() and os.access(path,os.X_OK)):
        raise RuntimeError('MISSING_NATIVE_S5: run earlier UNO_A52_R41_F_OPERATOR_BENCH.sh')
    p=subprocess.run([str(path),'rank','prefix2','0.3'],capture_output=True,text=True,timeout=5)
    if p.returncode or 'FIXED_MASK_CONTRACT' not in p.stdout or 'status=PASS' not in p.stdout:
        raise RuntimeError('NATIVE_S5_PROBE_FAILED')
    return str(path)

def fmt(x):return '-' if x is None else ('%.3f'%x)

def stage(name,n,ram,duration,repetitions,binary,root,ctx,log,quick):
    event=ctx.Event();workers=[];res=ctx.Queue();ready=ctx.Queue();holder=None
    began=time.monotonic();allresults=[];errs=0
    try:
        holder=ctx.Process(target=hold_ram,args=(ram,event,ready));holder.start()
        msg=ready.get(timeout=5)
        if msg[0]!='READY':raise RuntimeError('RAM_HOLDER_NOT_READY_'+str(msg))
        for _ in range(n):
            p=ctx.Process(target=native_worker,args=(binary,event,res));p.start();workers.append(p)
        log('STAGE_BEGIN name=%s native_S5=%d held_ram_MiB=%d duration_floor_s=%d' %(name,n,ram,duration))
        modes=('STOP_LATCH_FIRST','COMMIT_FIRST','STOP_LOCK_FIRST','WRITER_LOCK_FIRST',
               'CRASH_AFTER_STOP_ACK','CRASH_PRE_STOP_ACK','REPLAY_QUEUE_32','COMMIT_NO_ACK_DEDUP')
        for rep in range(1,repetitions+1):
            for mode in modes:
                issue=safety(quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                db=root/('%s_%02d_%s.sqlite3'%(name,rep,mode))
                out=tested_case(ctx,db,mode)
                allresults.append(out)
                if out['status']!='PASS':errs+=1
                log('CASE stage=%s rep=%d mode=%s status=%s rows=%d stopped=%d atomic=%s request_to_receive_ms=%s request_to_latch_ms=%s commit_minus_request_ms=%s meaning=%s' %(
                    name,rep,mode,out['status'],out['data']['rows'],out['data']['state'][1],out['data']['atomic'],
                    fmt(out['request_to_receive_ms']),fmt(out['request_to_latch_ms']),fmt(out['commit_minus_request_ms']),out['label']))
        while time.monotonic()<began+duration:
            issue=safety(quick)
            if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
            time.sleep(.2)
    finally:
        event.set()
        for p in workers:
            p.join(3)
            if p.is_alive():p.kill();p.join(1)
        if holder is not None:
            holder.join(2)
            if holder.is_alive():holder.kill();holder.join(1)
        for _ in workers:
            try:
                pid,runs,minimum,mean,problems=res.get(timeout=1)
                log('S5_WORKER stage=%s pid=%d native_runs=%d min_GMAC_s=%s mean_GMAC_s=%s errors=%s'%(
                    name,pid,runs,minimum,mean,problems))
                if runs<1 or problems:errs+=1
            except queue.Empty:
                log('S5_WORKER_MISSING_RESULT stage='+name);errs+=1
        res.cancel_join_thread();res.close();ready.cancel_join_thread();ready.close()
    acks=[x['request_to_latch_ms'] for x in allresults if x['request_to_latch_ms'] is not None]
    import statistics
    acks.sort()
    med=statistics.median(acks) if acks else None
    maxack=max(acks) if acks else None
    import math
    p95=acks[math.ceil(.95*len(acks))-1] if acks else None
    finding_request=sum(1 for x in allresults if x['case']=='WRITER_LOCK_FIRST' and x['commit_minus_request_ms'] is not None and x['commit_minus_request_ms']>0)
    finding_crash=sum(1 for x in allresults if x['case']=='CRASH_PRE_STOP_ACK' and x['data']['state']==(1,0))
    log('STAGE_SUMMARY stage=%s cases=%d failures=%d stop_ack_n=%d ack_median_ms=%s ack_p95_nearest_rank_ms=%s ack_max_ms=%s request_precedes_commit_findings=%d pre_ack_crash_loses_stop=%d' %(
        name,len(allresults),errs,len(acks),fmt(med),fmt(p95),fmt(maxack),finding_request,finding_crash))
    return errs==0,finding_request,finding_crash

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument('--quick',action='store_true',help='Developer smoke test, not full A52 measurement')
    opts=arg.parse_args()
    target=Path.home()/'storage'/'downloads'
    if not target.is_dir() or not os.access(target,os.W_OK):target=Path.home()
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=target/('UNO_A52_R41_DURABLE_STOP_ORDER_STRESS_'+stamp+'.txt')
    out=report.open('x',encoding='utf-8')
    def log(s):
        print(s,flush=True);out.write(s+'\n');out.flush()
    try:
        log('UNO / UNOVYRA -- DURABLE STOP / COMMIT SERIALIZATION UNDER NATIVE S5 STRESS '+VERSION)
        log('On A52: native ARM FP32 S5 workers run on phone CPU; Python orchestrates SQLite and IPC; synthetic fixtures.')
        log('No idle stage: 2 workers +32MiB and 4 workers +64MiB. All directed cases run under load.')
        log('SQLite state and T/L/P fixture share ONE WAL FULL database; separate stop registrar and ticket executor contend for BEGIN IMMEDIATE.')
        log('STOP REQUEST, STOP RECEIVED, DURABLE STOP ACK and COMMIT are different instants.')
        log('Negative controls: WRITE_LOCK_FIRST commit after STOP request; CRASH_PRE_STOP_ACK loses unacknowledged STOP.')
        log('No genuine Android dispatch or user authorization, native receiver or trained P; no production guarantee.')
        log('OWNER_APPROVED_PRECODE = FALSE')
        b,t,m=metrics();log('PRECHECK battery=%s temp_deciC=%s MemAvailable_kB=%s'%(b,t,m))
        issue=safety(opts.quick)
        if issue:
            log('RESULT SAFETY_SKIP '+issue);return 3
        binary=check_binary();log('NATIVE_S5 '+binary)
        root=Path.home()/'uno_a52_r41_durable_stop_order_lab'/stamp
        root.mkdir(parents=True,exist_ok=False,mode=0o700)
        ctx=mp.get_context('fork')
        plans=[('S5x2_RAM32',2,32,4,1),('S5x4_RAM64',4,64,5,1)] if opts.quick else [
            ('S5x2_RAM32',2,32,16,2),('S5x4_RAM64',4,64,20,2)]
        overall=True;findings=0;crashes=0
        def stage_watchdog(signum, frame):
            raise TimeoutError('STAGE_WATCHDOG_TIMEOUT')
        old_handler=signal.signal(signal.SIGALRM,stage_watchdog)
        try:
            for name,n,ram,seconds,reps in plans:
                issue=safety(opts.quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                signal.alarm(100 if n==2 else 140)
                try:
                    ok,request_findings,crash_findings=stage(name,n,ram,seconds,reps,binary,root,ctx,log,opts.quick)
                finally:
                    signal.alarm(0)
                overall=overall and ok;findings+=request_findings;crashes+=crash_findings
                b,t,m=metrics();log('STAGE_TELEMETRY name=%s battery=%s temp_deciC=%s MemAvailable_kB=%s'%(name,b,t,m))
                if not ok:break
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM,old_handler)
        log('RESULT '+('PASS_EXPECTED_SQLITE_SERIAL_ORDER_WITH_KNOWN_REQUEST_GAPS' if overall else 'FAIL_INVARIANT')+
            ' stop_requested_before_commit_cases='+str(findings)+' pre_ack_crash_lost_stop_cases='+str(crashes))
        log('UNRESOLVED: strict user-press STOP before all future commits; reliable durable acceptance of STOP before controller crash; real Android capability isolation.')
        log('LIMIT: ordering is for SQLite synthetic transactions only; not external OS actions or hard real-time response; 2 repetitions per stage cannot define SLA.')
        log('REPORT '+str(report))
        return 0 if overall else 2
    except KeyboardInterrupt:
        log('RESULT USER_INTERRUPT');log('REPORT '+str(report));return 130
    except BaseException as ex:
        log('RESULT ERROR '+type(ex).__name__+' '+str(ex)[:250]);log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2
    finally:out.close()

if __name__=='__main__':sys.exit(main())
