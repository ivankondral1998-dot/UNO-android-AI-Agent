#!/usr/bin/env python3
"""UNO R4.1 V4 PRECODE laboratory: independent durable STOP ingress and synthetic commit guard.
Under native S5 C256R32 CPU load on an ARM Android phone. NOT a production security model.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse, datetime, fcntl, math, multiprocessing as mp, os, queue, re
import signal, sqlite3, statistics, subprocess, sys, time, traceback
from pathlib import Path

VERSION='UNO_R41_A52_S5_STOP_INGRESS_DURABILITY_STRESS_V4'
MiB=1048576

def read_i(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:
        m=next(int(s.split()[1]) for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    except (OSError,StopIteration,ValueError,IndexError):m=None
    return (read_i('/sys/class/power_supply/battery/capacity'),read_i('/sys/class/power_supply/battery/temp'),m)

def safety(quick):
    if quick:return None
    b,t,m=telemetry()
    if b is None or t is None or m is None or not 100<=t<=800:return 'REQUIRED_BATTERY_OR_MEMORY_SENSOR_UNAVAILABLE'
    if b<40:return 'BATTERY_LT_40_PCT'
    if t>=375:return 'BATTERY_GE_37_5_C'
    if m<400000:return 'MEMAVAILABLE_LT_400000_KB'
    return None

def db(path):
    c=sqlite3.connect(str(path),timeout=7.0,isolation_level=None)
    c.execute('PRAGMA busy_timeout=7000')
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    return c

def init_case(root):
    root.mkdir(mode=0o700,parents=True,exist_ok=False)
    (root/'gate.lock').touch(mode=0o600)
    s=db(root/'stop.sqlite3')
    s.execute('CREATE TABLE stop_latch(id INTEGER PRIMARY KEY,epoch INTEGER NOT NULL,stopped INTEGER NOT NULL,seq INTEGER NOT NULL)')
    s.execute('INSERT INTO stop_latch VALUES(1,1,0,0)');s.close()
    w=db(root/'work.sqlite3')
    for tab in ('receipts','memory','plasticity'):
        w.execute('CREATE TABLE '+tab+'(ticket TEXT PRIMARY KEY,epoch INTEGER NOT NULL)')
    w.close()

def get_state(root):
    c=db(root/'stop.sqlite3')
    try:return tuple(c.execute('SELECT epoch,stopped,seq FROM stop_latch WHERE id=1').fetchone())
    finally:c.close()

def inspect(root):
    s=db(root/'stop.sqlite3');w=db(root/'work.sqlite3')
    try:
        state=tuple(s.execute('SELECT epoch,stopped,seq FROM stop_latch WHERE id=1').fetchone())
        sets=[set(w.execute('SELECT ticket,epoch FROM '+tab).fetchall()) for tab in ('receipts','memory','plasticity')]
        return {'state':state,'rows':len(sets[0]),'atomic':sets[0]==sets[1]==sets[2],
                'db_ok':s.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and w.execute('PRAGMA integrity_check').fetchone()[0]=='ok'}
    finally:s.close();w.close()

def guarded_commit(root,ticket='T1'):
    with (root/'gate.lock').open('rb') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        try:
            s=db(root/'stop.sqlite3');w=db(root/'work.sqlite3')
            try:
                if s.execute('SELECT stopped FROM stop_latch WHERE id=1').fetchone()[0]:return 'STOPPED',None
                w.execute('BEGIN IMMEDIATE')
                if w.execute('SELECT 1 FROM receipts WHERE ticket=?',(ticket,)).fetchone():
                    w.execute('ROLLBACK');return 'DUPLICATE',None
                for tab in ('receipts','memory','plasticity'):
                    w.execute('INSERT INTO '+tab+' VALUES (?,1)',(ticket,))
                w.execute('COMMIT')
                return 'COMMITTED',time.monotonic_ns()
            finally:
                if w.in_transaction:w.execute('ROLLBACK')
                w.close();s.close()
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

def stop_ingress(root,mode,ch):
    """Separate process; STOP is durable only after SQLite FULL COMMIT and ACK.
    The shared advisory file lock orders all participating lab committers and STOP acceptance.
    """
    c=None
    try:
        c=db(root/'stop.sqlite3')
        ch.send(('READY',os.getpid()))
        if not ch.poll(10):raise TimeoutError('NO_STOP_REQUEST')
        if ch.recv()!=('STOP',):raise RuntimeError('BAD_STOP_REQUEST')
        receive_ns=time.monotonic_ns();ch.send(('RECEIVED',receive_ns))
        if mode=='WAIT_BEFORE_ACCEPT':
            ch.send(('PARKED',))
            if not ch.poll(12):raise TimeoutError('WAIT_RELEASE_STOP')
            if ch.recv()!=('RELEASE',):raise RuntimeError('WRONG_RELEASE')
        with (root/'gate.lock').open('rb') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                if mode=='HOLD_LOCK':
                    ch.send(('LOCKED',))
                    if not ch.poll(12):raise TimeoutError('WAIT_LOCK_RELEASE')
                    if ch.recv()!=('RELEASE',):raise RuntimeError('WRONG_LOCK_RELEASE')
                c.execute('BEGIN IMMEDIATE')
                c.execute('UPDATE stop_latch SET stopped=1,epoch=2,seq=seq+1 WHERE id=1')
                c.execute('COMMIT')
                latch_ns=time.monotonic_ns()
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
        ch.send(('ACK_DURABLE',latch_ns))
    except BaseException as ex:
        try:ch.send(('ERROR',type(ex).__name__,str(ex)[:130]))
        except Exception:pass
    finally:
        if c:
            try:
                if c.in_transaction:c.execute('ROLLBACK')
                c.close()
            except Exception:pass
        ch.close()

def work_actor(root,mode,ch):
    """Fixture worker holds global lock and work transaction to force exact interleavings."""
    w=None
    try:
        with (root/'gate.lock').open('rb') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            try:
                state=get_state(root)
                if state[1]:ch.send(('BLOCKED',));return
                w=db(root/'work.sqlite3');w.execute('BEGIN IMMEDIATE')
                for tab in ('receipts','memory','plasticity'):
                    w.execute('INSERT INTO '+tab+' VALUES (?,1)',('T1',))
                ch.send(('HELD',os.getpid()))
                if not ch.poll(12):raise TimeoutError('WORKER_RELEASE_TIMEOUT')
                if ch.recv()!=('RELEASE',):raise RuntimeError('INVALID_WORKER_RELEASE')
                if mode=='CRASH_UNCOMMITTED':os._exit(33)
                w.execute('COMMIT')
                ch.send(('COMMITTED',time.monotonic_ns()))
            finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
    except BaseException as ex:
        try:ch.send(('ERROR',type(ex).__name__,str(ex)[:130]))
        except Exception:pass
    finally:
        if w:
            try:
                if w.in_transaction:w.execute('ROLLBACK')
                w.close()
            except Exception:pass
        ch.close()

def writer_try_actor(root,ch):
    try:
        ch.send(('TRYING',time.monotonic_ns()))
        outcome,ns=guarded_commit(root)
        ch.send(('RESULT',outcome,ns))
    except BaseException as ex:
        try:ch.send(('ERROR',type(ex).__name__,str(ex)[:130]))
        except Exception:pass
    finally:ch.close()

def dummy_controller(ch):
    try:
        ch.send(('READY',os.getpid()))
        while True:time.sleep(.1)
    finally:ch.close()

def start(ctx,target,*args):
    a,b=ctx.Pipe(duplex=True)
    p=ctx.Process(target=target,args=(*args,b))
    p.start();b.close()
    return p,a

def get(ch,expected,timeout=12):
    if not ch.poll(timeout):raise TimeoutError('WAIT_'+expected)
    v=ch.recv()
    if v[0]=='ERROR':raise RuntimeError('CHILD_ERROR_'+str(v))
    if v[0]!=expected:raise RuntimeError('EXPECTED_'+expected+'_GOT_'+str(v))
    return v

def join(p,exitcode=0):
    p.join(4)
    if p.is_alive():raise TimeoutError('CHILD_DID_NOT_EXIT')
    if p.exitcode!=exitcode:raise RuntimeError('BAD_CHILD_EXIT_'+str(p.exitcode))

def cleanup(actors):
    for p,ch in actors:
        try:
            if p.is_alive():p.kill()
            p.join(2)
        except Exception:pass
        try:ch.close()
        except Exception:pass

def case(ctx,root,mode):
    init_case(root);actors=[];t={};expected=False;label=''
    try:
        if mode=='ACK_FIRST_BLOCKS':
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic))
            get(ic,'READY');t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];t['ack']=get(ic,'ACK_DURABLE')[1];join(ip)
            out,ns=guarded_commit(root)
            expected=out=='STOPPED' and ns is None
            label='POST_ACK_COMMIT_BLOCKED'
        elif mode=='COMMIT_FIRST_RETAINED':
            out,t['commit']=guarded_commit(root)
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic))
            get(ic,'READY');t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];t['ack']=get(ic,'ACK_DURABLE')[1];join(ip)
            expected=out=='COMMITTED' and t['commit']<t['request']
            label='PAST_COMMIT_RETAINED'
        elif mode=='STOP_LOCK_FIRST':
            ip,ic=start(ctx,stop_ingress,root,'HOLD_LOCK');actors.append((ip,ic))
            get(ic,'READY');t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];get(ic,'LOCKED')
            wp,wc=start(ctx,writer_try_actor,root);actors.append((wp,wc))
            get(wc,'TRYING');time.sleep(.012);ic.send(('RELEASE',))
            t['ack']=get(ic,'ACK_DURABLE')[1]
            status=get(wc,'RESULT');join(ip);join(wp)
            expected=status[1]=='STOPPED' and status[2] is None
            label='STOP_LOCK_PRECEDES_WORK_COMMIT'
        elif mode=='WORK_LOCK_FIRST':
            wp,wc=start(ctx,work_actor,root,'NORMAL');actors.append((wp,wc));get(wc,'HELD')
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic));get(ic,'READY')
            t['request']=time.monotonic_ns();ic.send(('STOP',));t['receive']=get(ic,'RECEIVED')[1]
            time.sleep(.012);wc.send(('RELEASE',));t['commit']=get(wc,'COMMITTED')[1]
            t['ack']=get(ic,'ACK_DURABLE')[1];join(wp);join(ip)
            expected=t['request']<t['commit']<t['ack']
            label='KNOWN_REQUEST_TO_ACK_WINDOW'
        elif mode=='CTRL_CRASH_PRE_ACK_INGRESS_SURVIVES':
            wp,wc=start(ctx,work_actor,root,'NORMAL');actors.append((wp,wc));get(wc,'HELD')
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic));get(ic,'READY')
            t['request']=time.monotonic_ns();ic.send(('STOP',));t['receive']=get(ic,'RECEIVED')[1]
            # Work/controller process dies while holding the transaction lock. Ingress remains alive.
            wp.kill();join(wp,-9)
            t['ack']=get(ic,'ACK_DURABLE')[1];join(ip)
            out,ns=guarded_commit(root,'T_AFTER_CTRL_CRASH')
            expected=out=='STOPPED' and ns is None
            label='INDEPENDENT_STOP_PERSISTS_AFTER_CONTROLLER_CRASH'
        elif mode=='CTRL_CRASH_POST_ACK':
            controller,cc=start(ctx,dummy_controller);actors.append((controller,cc));get(cc,'READY')
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic));get(ic,'READY')
            t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];t['ack']=get(ic,'ACK_DURABLE')[1];join(ip)
            controller.kill();join(controller,-9)
            out,_=guarded_commit(root,'T_AFTER_ACK_AND_CRASH')
            expected=out=='STOPPED'
            label='DURABLE_ACK_SURVIVES_CONTROLLER_CRASH'
        elif mode=='INGRESS_CRASH_PRE_ACK_NEGATIVE':
            ip,ic=start(ctx,stop_ingress,root,'WAIT_BEFORE_ACCEPT');actors.append((ip,ic))
            get(ic,'READY');t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];get(ic,'PARKED')
            ip.kill();join(ip,-9)
            out,t['commit']=guarded_commit(root,'T_AFTER_INGRESS_CRASH')
            expected=out=='COMMITTED'
            label='UNACKNOWLEDGED_STOP_CAN_BE_LOST_WHEN_INGRESS_CRASHES'
        elif mode=='POST_ACK_QUEUE_32':
            ip,ic=start(ctx,stop_ingress,root,'DIRECT');actors.append((ip,ic));get(ic,'READY')
            t['request']=time.monotonic_ns();ic.send(('STOP',))
            t['receive']=get(ic,'RECEIVED')[1];t['ack']=get(ic,'ACK_DURABLE')[1];join(ip)
            outcomes=[guarded_commit(root,'Q'+str(i))[0] for i in range(32)]
            expected=outcomes.count('STOPPED')==32
            label='ALL_32_POST_ACK_DENIED'
        else:raise RuntimeError('NO_CASE_'+mode)
        result=inspect(root)
        expected=expected and result['db_ok'] and result['atomic']
        if mode in ('COMMIT_FIRST_RETAINED','WORK_LOCK_FIRST','INGRESS_CRASH_PRE_ACK_NEGATIVE'):
            expected=expected and result['rows']==1
        else:expected=expected and result['rows']==0
        if mode=='INGRESS_CRASH_PRE_ACK_NEGATIVE':expected=expected and result['state']==(1,0,0)
        else:expected=expected and result['state']==(2,1,1)
        return {'mode':mode,'status':'PASS' if expected else 'FAIL','label':label,
                'rows':result['rows'],'state':result['state'],'atomic':result['atomic'],'integrity':result['db_ok'],
                'request_ack_ms':(t['ack']-t['request'])/1e6 if 'ack' in t else None,
                'receive_ms':(t['receive']-t['request'])/1e6 if 'receive' in t else None,
                'commit_request_ms':(t['commit']-t['request'])/1e6 if t.get('commit') is not None and 'request' in t else None}
    finally:cleanup(actors)

def native_worker(binary,quit,results):
    rates=[];errs=[]
    while not quit.is_set():
        try:
            p=subprocess.run([binary,'rank','full','0.70'],text=True,capture_output=True,timeout=5)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):
                errs.append('NATIVE_S5_BAD_EXIT_OR_CONTRACTION');break
            m=re.search(r'estimated_F_GMAC_s=([0-9.]+)',p.stdout)
            if not m:errs.append('MISSING_GMAC');break
            rates.append(float(m.group(1)))
        except BaseException as ex:errs.append(type(ex).__name__+':'+str(ex)[:80]);break
    try:results.put((os.getpid(),len(rates),min(rates) if rates else None,statistics.mean(rates) if rates else None,errs),timeout=2)
    except Exception:pass

def hold_mem(amount,quit,ready):
    try:
        a=bytearray(amount*MiB)
        for i in range(0,len(a),4096):a[i]=1
        ready.put(('READY',os.getpid()),timeout=2)
        while not quit.wait(.2):
            for i in range(0,len(a),262144):a[i]^=1
    except BaseException as ex:
        try:ready.put(('ERROR',repr(ex)),timeout=2)
        except Exception:pass

def native_binary():
    p=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_NOT_FOUND: Run earlier F operator benchmark')
    x=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=5)
    if x.returncode!=0 or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',x.stdout):
        raise RuntimeError('NATIVE_S5_SELF_CHECK_FAILED')
    return str(p)

def fmt(x):return '-' if x is None else f'{x:.3f}'

def stage(ctx,root,log,quick,name,n,ram,duration,repeats,binary):
    stop=ctx.Event();out=ctx.Queue();ready=ctx.Queue();workers=[];holder=None
    results=[];failures=0;begin=time.monotonic()
    modes=('ACK_FIRST_BLOCKS','COMMIT_FIRST_RETAINED','STOP_LOCK_FIRST','WORK_LOCK_FIRST',
           'CTRL_CRASH_PRE_ACK_INGRESS_SURVIVES','CTRL_CRASH_POST_ACK',
           'INGRESS_CRASH_PRE_ACK_NEGATIVE','POST_ACK_QUEUE_32')
    try:
        holder=ctx.Process(target=hold_mem,args=(ram,stop,ready));holder.start()
        msg=ready.get(timeout=5)
        if msg[0]!='READY':raise RuntimeError('MEM_HOLDER_BAD_'+str(msg))
        for _ in range(n):
            p=ctx.Process(target=native_worker,args=(binary,stop,out));p.start();workers.append(p)
        log(f'STAGE_BEGIN name={name} native_S5_workers={n} touched_ram_MiB={ram} duration_floor_s={duration}')
        for repeat in range(1,repeats+1):
            for mode in modes:
                issue=safety(quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                place=root/f'{name}_{repeat:02}_{mode}'
                r=case(ctx,place,mode);results.append(r)
                if r['status']!='PASS':failures+=1
                log('CASE stage=%s rep=%d mode=%s status=%s rows=%d stopped=%d atomic=%s integrity=%s request_ack_ms=%s receive_ms=%s commit_minus_request_ms=%s meaning=%s'%(
                    name,repeat,mode,r['status'],r['rows'],r['state'][1],r['atomic'],r['integrity'],fmt(r['request_ack_ms']),
                    fmt(r['receive_ms']),fmt(r['commit_request_ms']),r['label']))
        while time.monotonic()<begin+duration:
            issue=safety(quick)
            if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
            time.sleep(.20)
    finally:
        stop.set()
        for p in workers:
            p.join(4)
            if p.is_alive():p.kill();p.join(1)
        if holder is not None:
            holder.join(2)
            if holder.is_alive():holder.kill();holder.join(1)
        for _ in workers:
            try:
                pid,runs,mn,avg,problems=out.get(timeout=1)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={runs} min_GMAC_s={mn} mean_GMAC_s={avg} errors={problems}')
                if runs<1 or problems:failures+=1
            except queue.Empty:
                log('ERROR MISSING_S5_WORKER_RESULT stage='+name);failures+=1
        out.cancel_join_thread();out.close();ready.cancel_join_thread();ready.close()
    acks=sorted(v['request_ack_ms'] for v in results if v['request_ack_ms'] is not None)
    p95=acks[math.ceil(.95*len(acks))-1] if acks else None
    late=sum(v['mode']=='WORK_LOCK_FIRST' and v['commit_request_ms'] is not None and v['commit_request_ms']>0 for v in results)
    saved=sum(v['mode']=='CTRL_CRASH_PRE_ACK_INGRESS_SURVIVES' and v['state']==(2,1,1) for v in results)
    lost=sum(v['mode']=='INGRESS_CRASH_PRE_ACK_NEGATIVE' and v['state']==(1,0,0) for v in results)
    log('STAGE_SUMMARY stage=%s cases=%d failures=%d durable_ack_samples=%d ack_median_ms=%s ack_p95_nearest_rank_ms=%s ack_max_ms=%s pre_ack_ctrl_crash_saved=%d ingress_pre_ack_crash_lost=%d request_before_commit_windows=%d'%(
        name,len(results),failures,len(acks),fmt(statistics.median(acks) if acks else None),fmt(p95),fmt(max(acks) if acks else None),saved,lost,late))
    return failures==0,saved,lost,late

def main():
    p=argparse.ArgumentParser();p.add_argument('--quick',action='store_true',help='Linux developer smoke test; no phone conclusions')
    opt=p.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/('UNO_A52_R41_S5_STOP_INGRESS_DURABILITY_V4_'+stamp+'.txt')
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA R4.1 -- SEPARATE DURABLE STOP INGRESS UNDER NATIVE S5 LOAD '+VERSION)
            log('Native C256R32 S5 workers on Android CPU + 32/64MiB RAM; Python orchestrates processes, SQLite WAL FULL and advisory flock.')
            log('One independent STOP ingress journal, separate from work DB. Shared lock serializes STOP acceptance and participating commits.')
            log('STOP request != receive != durable ACK. Physical user press, Android actions and hard real-time are NOT tested.')
            log('Negative controls: pre-ACK ingress crash loses STOP; writer already holding gate may commit after STOP request and before ACK.')
            log('No idle stage, root, APK, Android dispatch, permission escalation, model learning, trained weights or system changes.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            issue=safety(opt.quick)
            if issue:log('RESULT SAFETY_SKIP '+issue);return 3
            binary=native_binary();log('VERIFIED_NATIVE_S5 '+binary)
            root=home/'uno_a52_r41_stop_ingress_durability_v4'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            ctx=mp.get_context('fork')
            plans=[('S5x2_RAM32',2,32,4,1),('S5x4_RAM64',4,64,5,1)] if opt.quick else [
                ('S5x2_RAM32',2,32,18,2),('S5x4_RAM64',4,64,24,2)]
            saved=lost=late=0;okay=True
            def timeout_handler(_sig,_frame):raise TimeoutError('STAGE_WATCHDOG_TIMEOUT')
            old=signal.signal(signal.SIGALRM,timeout_handler)
            try:
                for name,n,ram,duration,reps in plans:
                    issue=safety(opt.quick)
                    if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                    signal.alarm(100 if n==2 else 150)
                    try:o,sv,ls,la=stage(ctx,root,log,opt.quick,name,n,ram,duration,reps,binary)
                    finally:signal.alarm(0)
                    saved+=sv;lost+=ls;late+=la;okay=okay and o
                    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
                    if not o:break
            finally:
                signal.alarm(0);signal.signal(signal.SIGALRM,old)
            log('RESULT '+('PASS_LAB_DURABLE_INGRESS_WITH_DOCUMENTED_GAPS' if okay else 'FAIL_INVARIANT')+
                f' controller_crash_pre_ack_stop_survived={saved} ingress_crash_pre_ack_stop_lost={lost} request_before_commit_windows={late}')
            log('LIMIT: ACK is durable only after separate SQLite FULL COMMIT; request before ACK can lose on ingress failure.')
            log('LIMIT: shared fcntl lock is ADVISORY, not Android permission boundary; all writers must cooperate. No power-cut test.')
            log('LIMIT: commit before STOP ACK remains possible if writer locked first; no guarantee from user physical press, no external OS action rollback.')
            log('REPORT '+str(report));return 0 if okay else 2
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPT');log('REPORT '+str(report));return 130
        except BaseException as ex:
            log('RESULT ERROR '+type(ex).__name__+' '+str(ex)[:220]);log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
