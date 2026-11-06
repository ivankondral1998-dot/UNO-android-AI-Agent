#!/usr/bin/env python3
"""UNO R4.1 V5: fail-closed restart + ingress watchdog laboratory, under native S5 load.
This is PRECODE experiment, not an implementation of real Android STOP or owner authentication.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse, datetime, math, multiprocessing as mp, os, queue, re, signal
import sqlite3, statistics, subprocess, sys, time, traceback
from pathlib import Path

VERSION = 'UNO_R41_A52_S5_FAILCLOSED_RESTART_WATCHDOG_STRESS_V5'
MiB = 1048576
MODES = (
    'COLD_START_DENIES', 'LAB_ARM_COMMIT', 'CTRL_CRASH_RESTART_DISARMS',
    'PREACK_INGRESS_CRASH_RESTART_DISARMS', 'DURABLE_STOP_RESTART_DENIES',
    'STALE_EPOCH_AFTER_REARM', 'DUPLICATE_AFTER_REARM',
    'WATCHDOG_INGRESS_LOSS', 'WATCHDOG_PREACK_STOP_LOSS',
    'NEGATIVE_HELD_TX_BLOCKS_WATCHDOG',
)

def read_i(path):
    try: return int(Path(path).read_text().strip())
    except (OSError, ValueError): return None

def telemetry():
    try: mem = next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    except (OSError, ValueError, StopIteration, IndexError): mem = None
    return read_i('/sys/class/power_supply/battery/capacity'), read_i('/sys/class/power_supply/battery/temp'), mem

def safety(quick):
    if quick:return None
    batt,temp,mem=telemetry()
    if batt is None or temp is None or mem is None or not 100 <= temp <= 800: return 'REQUIRED_SENSOR_UNAVAILABLE'
    if batt < 40: return 'BATTERY_BELOW_40_PCT'
    if temp >= 375: return 'BATTERY_AT_OR_ABOVE_37_5_C'
    if mem < 400000: return 'MEMAVAILABLE_BELOW_400000_KB'
    return None

def db(root):
    conn=sqlite3.connect(str(root/'lab.sqlite3'), timeout=7, isolation_level=None)
    conn.execute('PRAGMA busy_timeout=7000')
    conn.execute('PRAGMA synchronous=FULL')
    return conn

def init_case(root):
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    con=db(root)
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('CREATE TABLE control(id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, armed INTEGER NOT NULL, stopped INTEGER NOT NULL, ingress_ok INTEGER NOT NULL, seq INTEGER NOT NULL)')
        con.execute('INSERT INTO control VALUES(1,1,0,0,0,0)')
        for tab in ('receipts','memory','plasticity'):
            con.execute(f'CREATE TABLE {tab}(ticket TEXT PRIMARY KEY,epoch INTEGER NOT NULL)')
    finally:con.close()

def state(root):
    con=db(root)
    try:return tuple(con.execute('SELECT epoch,armed,stopped,ingress_ok,seq FROM control WHERE id=1').fetchone())
    finally:con.close()

def transact(root,op):
    con=db(root)
    try:
        con.execute('BEGIN IMMEDIATE')
        s=tuple(con.execute('SELECT epoch,armed,stopped,ingress_ok,seq FROM control WHERE id=1').fetchone())
        if op=='NEW_BOOT':
            con.execute('UPDATE control SET epoch=epoch+1,armed=0,ingress_ok=0 WHERE id=1')
            result=('BOOT_DISARMED',s[0]+1)
        elif op=='LAB_INGRESS_READY':
            if s[2]:result=('STOP_LATCHED',s[0])
            else:
                con.execute('UPDATE control SET ingress_ok=1 WHERE id=1')
                result=('LAB_INGRESS_READY',s[0])
        elif op=='LAB_ARM':
            if s[2] or not s[3]:result=('ARM_DENIED',s[0])
            else:
                con.execute('UPDATE control SET armed=1 WHERE id=1')
                result=('LAB_ARMED',s[0])
        elif op=='DURABLE_STOP':
            if not s[2]:con.execute('UPDATE control SET stopped=1,armed=0,ingress_ok=0,epoch=epoch+1,seq=seq+1 WHERE id=1')
            result=('DURABLE_STOP',s[0]+(0 if s[2] else 1))
        else:raise ValueError('UNSUPPORTED_OP')
        con.execute('COMMIT');return result
    finally:
        if con.in_transaction:con.execute('ROLLBACK')
        con.close()

def guarded_commit(root,ticket,epoch):
    con=db(root)
    try:
        con.execute('BEGIN IMMEDIATE')
        s=tuple(con.execute('SELECT epoch,armed,stopped,ingress_ok,seq FROM control WHERE id=1').fetchone())
        if s[2]:ans='STOPPED'
        elif epoch!=s[0]:ans='STALE_EPOCH'
        elif not s[1]:ans='DISARMED'
        elif not s[3]:ans='NO_INGRESS'
        elif con.execute('SELECT 1 FROM receipts WHERE ticket=?',(ticket,)).fetchone():ans='DUPLICATE'
        else:
            for tab in ('receipts','memory','plasticity'):
                con.execute(f'INSERT INTO {tab}(ticket,epoch) VALUES(?,?)',(ticket,epoch))
            ans='COMMITTED'
        con.execute('COMMIT')
        return ans,time.monotonic_ns()
    finally:
        if con.in_transaction:con.execute('ROLLBACK')
        con.close()

def inspect(root):
    con=db(root)
    try:
        s=tuple(con.execute('SELECT epoch,armed,stopped,ingress_ok,seq FROM control WHERE id=1').fetchone())
        sets=[set(con.execute('SELECT ticket,epoch FROM '+tab).fetchall()) for tab in ('receipts','memory','plasticity')]
        return s,len(sets[0]),(sets[0]==sets[1]==sets[2]),con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:con.close()

def send(ch,msg):
    try:ch.send(msg)
    except (BrokenPipeError,EOFError,OSError):pass

def ingress_actor(heartbeat,ch):
    try:
        heartbeat.value=time.monotonic_ns();send(ch,('READY',os.getpid()))
        while True:
            heartbeat.value=time.monotonic_ns()
            if ch.poll(.02):
                cmd=ch.recv()
                if cmd=='STOP':
                    send(ch,('STOP_RECEIVED',time.monotonic_ns()))
                    # Deliberately wait: parent will simulate ingress crash BEFORE durable STOP.
                    while True:time.sleep(.05)
                if cmd=='QUIT':break
    except (EOFError,ConnectionResetError):pass
    finally:ch.close()

def watchdog_actor(root,heartbeat,timeout_s,ch):
    try:
        send(ch,('READY',os.getpid()))
        start=time.monotonic()
        while True:
            if time.monotonic()-start>6:send(ch,('ERROR','WATCHDOG_NO_INGRESS_LOSS'));return
            age=(time.monotonic_ns()-heartbeat.value)/1e9 if heartbeat.value else 0
            if age>timeout_s:
                t_detect=time.monotonic_ns()
                # Fail-closed durable latch (same SQLite transaction ordering as commits).
                transact(root,'DURABLE_STOP')
                t_latch=time.monotonic_ns()
                send(ch,('LATCHED',t_detect,t_latch,age*1000));return
            time.sleep(.015)
    except BaseException as exc:send(ch,('ERROR',type(exc).__name__,str(exc)[:100]))
    finally:ch.close()

def dummy_controller(ch):
    send(ch,('READY',os.getpid()))
    while True:time.sleep(.05)

def blocked_writer(root,ch):
    con=None
    try:
        con=db(root);con.execute('BEGIN IMMEDIATE')
        s=tuple(con.execute('SELECT epoch,armed,stopped,ingress_ok,seq FROM control WHERE id=1').fetchone())
        if not(s[1] and s[3] and not s[2]):raise RuntimeError('WRITER_NOT_ARMED')
        for tab in ('receipts','memory','plasticity'):
            con.execute(f'INSERT INTO {tab}(ticket,epoch) VALUES(?,?)',('INFLIGHT',s[0]))
        send(ch,('HELD',time.monotonic_ns()))
        if not ch.poll(4):raise TimeoutError('WRITER_NOT_RELEASED')
        if ch.recv()!='RELEASE':raise RuntimeError('WRITER_BAD_RELEASE')
        con.execute('COMMIT')
        send(ch,('COMMITTED',time.monotonic_ns()))
    except BaseException as exc:send(ch,('ERROR',type(exc).__name__,str(exc)[:120]))
    finally:
        if con is not None:
            if con.in_transaction:con.execute('ROLLBACK')
            con.close()
        ch.close()

def start(ctx,target,*args):
    parent,child=ctx.Pipe()
    proc=ctx.Process(target=target,args=(*args,child))
    proc.start();child.close()
    return proc,parent

def recv(ch,expected,timeout=8):
    if not ch.poll(timeout):raise TimeoutError(f'WAIT_{expected}')
    msg=ch.recv()
    if msg[0]!=expected:raise RuntimeError(f'EXPECTED_{expected}_GOT_{msg}')
    return msg

def kill_and_reap(proc):
    if proc.is_alive():proc.kill()
    proc.join(3)
    if proc.is_alive():raise TimeoutError('PROCESS_NOT_KILLED')

def cleanup(actors):
    for proc,ch in reversed(actors):
        try:kill_and_reap(proc)
        except Exception:pass
        try:ch.close()
        except Exception:pass

def run_case(ctx,root,mode):
    init_case(root)
    actors=[];start_ns=time.monotonic_ns();out='';expect=False;watch_ms=None
    try:
        if mode=='COLD_START_DENIES':
            out=guarded_commit(root,'T0',1)[0]
            expect=out=='DISARMED'
        elif mode=='LAB_ARM_COMMIT':
            transact(root,'LAB_INGRESS_READY');arm=transact(root,'LAB_ARM')
            out=guarded_commit(root,'T1',arm[1])[0]
            expect=arm[0]=='LAB_ARMED' and out=='COMMITTED'
        elif mode=='CTRL_CRASH_RESTART_DISARMS':
            transact(root,'LAB_INGRESS_READY');arm=transact(root,'LAB_ARM')
            p,ch=start(ctx,dummy_controller);actors.append((p,ch));recv(ch,'READY');kill_and_reap(p)
            boot=transact(root,'NEW_BOOT')
            out=guarded_commit(root,'T1',boot[1])[0]
            expect=out=='DISARMED' and state(root)[2]==0
        elif mode=='PREACK_INGRESS_CRASH_RESTART_DISARMS':
            beat=ctx.Value('Q',0,lock=False);ip,ic=start(ctx,ingress_actor,beat);actors.append((ip,ic));recv(ic,'READY')
            transact(root,'LAB_INGRESS_READY');transact(root,'LAB_ARM')
            ic.send('STOP');recv(ic,'STOP_RECEIVED');kill_and_reap(ip)
            boot=transact(root,'NEW_BOOT')
            out=guarded_commit(root,'T1',boot[1])[0]
            expect=out=='DISARMED' and state(root)[2]==0
        elif mode=='DURABLE_STOP_RESTART_DENIES':
            transact(root,'LAB_INGRESS_READY');transact(root,'LAB_ARM')
            transact(root,'DURABLE_STOP');boot=transact(root,'NEW_BOOT')
            arm=transact(root,'LAB_ARM');out=guarded_commit(root,'T1',boot[1])[0]
            expect=out=='STOPPED' and arm[0]=='ARM_DENIED'
        elif mode=='STALE_EPOCH_AFTER_REARM':
            transact(root,'LAB_INGRESS_READY');old=transact(root,'LAB_ARM')[1]
            transact(root,'NEW_BOOT');transact(root,'LAB_INGRESS_READY');fresh=transact(root,'LAB_ARM')[1]
            old_result=guarded_commit(root,'T1',old)[0];out=guarded_commit(root,'T1',fresh)[0]
            expect=old_result=='STALE_EPOCH' and out=='COMMITTED'
            out='old='+old_result+',new='+out
        elif mode=='DUPLICATE_AFTER_REARM':
            transact(root,'LAB_INGRESS_READY');old=transact(root,'LAB_ARM')[1]
            first=guarded_commit(root,'T1',old)[0]
            transact(root,'NEW_BOOT');transact(root,'LAB_INGRESS_READY');fresh=transact(root,'LAB_ARM')[1]
            out=guarded_commit(root,'T1',fresh)[0]
            expect=first=='COMMITTED' and out=='DUPLICATE'
        elif mode in ('WATCHDOG_INGRESS_LOSS','WATCHDOG_PREACK_STOP_LOSS','NEGATIVE_HELD_TX_BLOCKS_WATCHDOG'):
            beat=ctx.Value('Q',0,lock=False)
            ip,ic=start(ctx,ingress_actor,beat);actors.append((ip,ic));recv(ic,'READY')
            transact(root,'LAB_INGRESS_READY');arm=transact(root,'LAB_ARM')
            wp,wc=start(ctx,watchdog_actor,root,beat,.25);actors.append((wp,wc));recv(wc,'READY')
            tx_t=None;kill_time=None
            if mode=='NEGATIVE_HELD_TX_BLOCKS_WATCHDOG':
                tp,tc=start(ctx,blocked_writer,root);actors.append((tp,tc));recv(tc,'HELD')
            if mode in ('WATCHDOG_PREACK_STOP_LOSS','NEGATIVE_HELD_TX_BLOCKS_WATCHDOG'):
                ic.send('STOP');recv(ic,'STOP_RECEIVED')
            kill_time=time.monotonic_ns();kill_and_reap(ip)
            if mode=='NEGATIVE_HELD_TX_BLOCKS_WATCHDOG':
                # A writer already inside its SQLite transaction can win before watchdog STOP.
                time.sleep(.32)
                tc.send('RELEASE');tx_t=recv(tc,'COMMITTED')[1]
            seen=recv(wc,'LATCHED',timeout=8)
            latch_time=seen[2];watch_ms=(latch_time-kill_time)/1e6
            out=guarded_commit(root,'T2',arm[1])[0]
            if mode=='NEGATIVE_HELD_TX_BLOCKS_WATCHDOG':
                expect=(tx_t is not None and tx_t>kill_time and tx_t<=latch_time and out=='STOPPED')
            else:expect=(out=='STOPPED')
            out+=f',kill_to_latch_ms={watch_ms:.3f}'
        else:raise ValueError('UNSUPPORTED_MODE')
        st,n,atomic,integrity=inspect(root)
        if mode=='NEGATIVE_HELD_TX_BLOCKS_WATCHDOG':expect=expect and n==1 and st[2]==1
        if mode=='WATCHDOG_INGRESS_LOSS' or mode=='WATCHDOG_PREACK_STOP_LOSS':expect=expect and n==0 and st[2]==1
        if not atomic or not integrity:expect=False
        return dict(mode=mode,status='PASS' if expect else 'FAIL',result=out,rows=n,stopped=st[2],armed=st[1],epoch=st[0],atomic=atomic,integrity=integrity,watch_ms=watch_ms,elapsed_ms=(time.monotonic_ns()-start_ns)/1e6)
    finally:cleanup(actors)

def native_worker(binary,quit,results):
    values=[];errors=[]
    while not quit.is_set():
        try:
            p=subprocess.run([binary,'rank','full','0.70'],capture_output=True,text=True,timeout=5)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):
                errors.append('NATIVE_S5_EXEC_OR_CHECK_FAILED');break
            m=re.search(r'estimated_F_GMAC_s=([0-9.]+)',p.stdout)
            if not m:errors.append('MISSING_RATE');break
            values.append(float(m.group(1)))
        except BaseException as exc:errors.append(type(exc).__name__+':'+str(exc)[:80]);break
    try:results.put((os.getpid(),len(values),min(values) if values else None,statistics.mean(values) if values else None,errors),timeout=2)
    except Exception:pass

def hold_mem(megabytes,quit,ready):
    try:
        area=bytearray(megabytes*MiB)
        for i in range(0,len(area),4096):area[i]=1
        ready.put(('READY',os.getpid()),timeout=2)
        while not quit.wait(.2):
            for i in range(0,len(area),262144):area[i]^=1
    except BaseException as exc:
        try:ready.put(('ERROR',str(exc)[:100]),timeout=2)
        except Exception:pass

def native_binary(override=None):
    binary=Path(override) if override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not binary.is_file() or not os.access(binary,os.X_OK):raise RuntimeError('NATIVE_S5_MISSING: run earlier S5 operator benchmark')
    p=subprocess.run([str(binary),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=5)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('NATIVE_S5_SELFTEST_FAILED')
    return str(binary)

def stage(ctx,root,log,quick,name,n,ram,duration,repeats,binary):
    stop=ctx.Event();out=ctx.Queue();ready=ctx.Queue();workers=[];holder=None
    results=[];failures=0;started=time.monotonic();watch_latencies=[]
    try:
        holder=ctx.Process(target=hold_mem,args=(ram,stop,ready));holder.start()
        msg=ready.get(timeout=5)
        if msg[0]!='READY':raise RuntimeError('MEM_HOLDER_FAILED '+str(msg))
        for _ in range(n):
            p=ctx.Process(target=native_worker,args=(binary,stop,out));p.start();workers.append(p)
        log(f'STAGE_BEGIN name={name} native_S5_workers={n} touched_ram_MiB={ram} duration_floor_s={duration}')
        for rep in range(1,repeats+1):
            for mode in MODES:
                issue=safety(quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                try:r=run_case(ctx,root/f'{name}_{rep}_{mode}',mode)
                except Exception as exc:
                    failures+=1
                    log(f'CASE stage={name} rep={rep} mode={mode} status=ERROR error={type(exc).__name__}:{exc}')
                    continue
                results.append(r)
                if r['status']!='PASS':failures+=1
                if r['watch_ms'] is not None:watch_latencies.append(r['watch_ms'])
                log('CASE stage=%s rep=%d mode=%s status=%s outcome=%s rows=%d stopped=%d armed=%d epoch=%d atomic=%s integrity=%s elapsed_ms=%.3f'%(
                    name,rep,mode,r['status'],r['result'],r['rows'],r['stopped'],r['armed'],r['epoch'],r['atomic'],r['integrity'],r['elapsed_ms']))
        while time.monotonic()<started+duration:
            issue=safety(quick)
            if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
            time.sleep(.15)
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
                pid,runs,mn,avg,errors=out.get(timeout=1)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={runs} min_GMAC_s={mn} mean_GMAC_s={avg} errors={errors}')
                if runs<1 or errors:failures+=1
            except queue.Empty:
                log('FAIL MISSING_WORKER_RESULT stage='+name);failures+=1
        out.cancel_join_thread();out.close();ready.cancel_join_thread();ready.close()
    log(f'STAGE_SUMMARY name={name} cases={len(results)} expected={repeats*len(MODES)} failures={failures} watchdog_samples={len(watch_latencies)} kill_to_durable_stop_max_ms={max(watch_latencies) if watch_latencies else None}')
    return failures==0 and len(results)==repeats*len(MODES),results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--quick',action='store_true',help='LOCAL developer smoke test; NOT valid hardware evidence')
    parser.add_argument('--binary',help='LOCAL developer mock native S5 binary; omit on A52')
    args=parser.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/('UNO_A52_R41_FAILCLOSED_WATCHDOG_STRESS_V5_'+stamp+'.txt')
    with report.open('x',encoding='utf-8') as f:
        def log(text):print(text,flush=True);f.write(text+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- FAIL-CLOSED RESTART + INGRESS WATCHDOG UNDER NATIVE S5 LOAD '+VERSION)
            log('Native ARM C256R32 S5 on Android CPU; Python orchestrates synthetic controller SQLite WAL FULL and watchdog.')
            log('No idle phase: all checks run under 2 native S5 +32 MiB and 4 native S5 +64 MiB.')
            log('LAB_ARM is SYNTHETIC and is NOT owner authorization; no true Android actions or neural training.')
            log('Critical scope: restart begins DISARMED; watchdog can latch STOP after ingress loss, not instant at physical user press.')
            log('Negative control: an in-flight SQLite transaction can commit after ingress crash before watchdog STOP latch.')
            log('No root, ADB, USB, network, Android permission escalation, forced reboot, or production changes.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            issue=safety(args.quick)
            if issue:log('RESULT SAFETY_SKIP '+issue);return 3
            binary=native_binary(args.binary);log('VERIFIED_NATIVE_S5 '+binary)
            root=home/'uno_a52_r41_failclosed_watchdog_v5'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            ctx=mp.get_context('fork');total=0;allpass=True
            plans=[('S5x2_RAM32',2,32,6,1),('S5x4_RAM64',4,64,7,1)] if args.quick else [
                ('S5x2_RAM32',2,32,24,2),('S5x4_RAM64',4,64,30,2)]
            for name,n,ram,duration,repeats in plans:
                issue=safety(args.quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                passed,results=stage(ctx,root,log,args.quick,name,n,ram,duration,repeats,binary)
                allpass=allpass and passed;total+=len(results)
                b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
                if not passed:break
            log('RESULT '+('PASS_BOUNDED_FAILCLOSED_RESTART_AND_WATCHDOG' if allpass else 'FAIL_OR_INCOMPLETE')+f' directed_cases={total}')
            log('UNRESOLVED: controller or watchdog and ingress simultaneous crash while live; window before watchdog latches; strict STOP from physical press; real Android authorization and dispatch.')
            log('LIMIT: a restart is disarmed only in this isolated laboratory; LAB_ARM is not authenticated; no platform hardware durability or full UNO inference proof.')
            log('REPORT '+str(report))
            return 0 if allpass else 2
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPT');log('REPORT '+str(report));return 130
        except BaseException as exc:
            log('RESULT ERROR '+type(exc).__name__+': '+str(exc)[:220])
            log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
