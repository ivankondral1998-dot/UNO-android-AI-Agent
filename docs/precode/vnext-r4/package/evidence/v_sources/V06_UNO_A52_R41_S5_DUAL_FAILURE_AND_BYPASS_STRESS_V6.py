#!/usr/bin/env python3
"""UNO R4.1 V6 bounded PRECODE lab: simultaneous guard failure, vote replay, and same-UID bypass.
All staged cases run while native ARM S5 operator jobs occupy the phone CPU.
NOT a secure authorization protocol; synthetic votes and data; no Android control.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse, datetime, multiprocessing as mp, os, queue, re, secrets, sqlite3
import statistics, subprocess, sys, time, traceback
from pathlib import Path

VERSION='UNO_R41_A52_S5_DUAL_FAILURE_AND_BYPASS_STRESS_V6'
MiB=1048576
PERMIT_TTL_NS=750_000_000
MODES=(
 'COLD_BOOT_DENIED','BOTH_GUARDS_ALIVE_COMMIT',
 'INGRESS_DEAD_BEFORE_VOTE','WATCHDOG_DEAD_BEFORE_VOTE','BOTH_DEAD_BEFORE_VOTE',
 'ONE_SHOT_VOTE_REPLAY_DENIED','VOTE_EXPIRED_DENIED',
 'NEGATIVE_BOTH_DIE_AFTER_VOTES','NEGATIVE_BOTH_DIE_WITH_OPEN_TX',
 'BOTH_DIE_RESTART_DISARMED','DURABLE_STOP_DUAL_CRASH_RESTART',
 'NEGATIVE_SAME_UID_DIRECT_DB_WRITE',
)
NEGATIVE={'NEGATIVE_BOTH_DIE_AFTER_VOTES','NEGATIVE_BOTH_DIE_WITH_OPEN_TX',
          'NEGATIVE_SAME_UID_DIRECT_DB_WRITE'}

def read_int(path):
    try:return int(Path(path).read_text().strip())
    except (ValueError,OSError):return None

def telemetry():
    try: mem=next(int(s.split()[1]) for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    except (OSError,StopIteration,IndexError,ValueError):mem=None
    return read_int('/sys/class/power_supply/battery/capacity'),read_int('/sys/class/power_supply/battery/temp'),mem

def safety(quick):
    if quick:return None
    battery,temp,avail=telemetry()
    if battery is None or temp is None or avail is None or not 100 <= temp <= 800:return 'SENSORS_UNAVAILABLE'
    if battery < 40:return 'BATTERY_BELOW_40'
    if temp >= 375:return 'BATTERY_TEMPERATURE_AT_LEAST_37_5_C'
    if avail < 400000:return 'MEMAVAILABLE_BELOW_400000_KB'
    return None

def connect(root):
    c=sqlite3.connect(str(root/'synthetic_control.sqlite3'),timeout=7,isolation_level=None)
    c.execute('PRAGMA busy_timeout=7000')
    c.execute('PRAGMA synchronous=FULL')
    return c

def initialize(root):
    root.mkdir(parents=True,exist_ok=False,mode=0o700)
    c=connect(root)
    try:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),epoch INTEGER NOT NULL,armed INTEGER NOT NULL,stopped INTEGER NOT NULL)')
        c.execute('INSERT INTO state VALUES(1,1,0,0)')
        for tab in ('receipts','memory','plasticity'):
            c.execute(f'CREATE TABLE {tab}(ticket TEXT PRIMARY KEY,epoch INTEGER NOT NULL)')
        c.execute('CREATE TABLE used_votes(nonce TEXT PRIMARY KEY,ticket TEXT NOT NULL)')
    finally:c.close()

def transition(root,command):
    c=connect(root)
    try:
        c.execute('BEGIN IMMEDIATE')
        epoch,armed,stopped=c.execute('SELECT epoch,armed,stopped FROM state WHERE id=1').fetchone()
        if command=='LAB_ARM_SYNTHETIC':
            out='STOPPED' if stopped else 'LAB_ARMED'
            if not stopped:c.execute('UPDATE state SET armed=1 WHERE id=1')
        elif command=='NEW_BOOT':
            c.execute('UPDATE state SET epoch=epoch+1,armed=0 WHERE id=1');out='BOOT_DISARMED'
        elif command=='STOP_DURABLE':
            c.execute('UPDATE state SET stopped=1,armed=0,epoch=epoch+1 WHERE id=1');out='STOP_DURABLE'
        else:raise ValueError('UNKNOWN_TRANSITION')
        c.execute('COMMIT');return out
    finally:
        if c.in_transaction:c.execute('ROLLBACK')
        c.close()

def put_record(c,ticket,epoch,nonce):
    for tab in ('receipts','memory','plasticity'):
        c.execute(f'INSERT INTO {tab}(ticket,epoch) VALUES(?,?)',(ticket,epoch))
    c.execute('INSERT INTO used_votes(nonce,ticket) VALUES(?,?)',(nonce,ticket))

def commit(root,ticket,epoch,permit):
    """A deliberately cooperative lab writer. Cannot prevent same-UID noncooperative writes."""
    c=connect(root)
    try:
        c.execute('BEGIN IMMEDIATE')
        now=time.monotonic_ns()
        current,armed,stopped=c.execute('SELECT epoch,armed,stopped FROM state WHERE id=1').fetchone()
        if stopped:out='STOPPED'
        elif not armed:out='DISARMED'
        elif epoch!=current:out='STALE_EPOCH'
        elif permit is None:out='NO_DUAL_VOTE'
        elif now-permit['issued_ns']<0 or now-permit['issued_ns']>PERMIT_TTL_NS:out='EXPIRED_VOTE'
        elif c.execute('SELECT 1 FROM used_votes WHERE nonce=?',(permit['nonce'],)).fetchone():out='VOTE_REPLAY'
        elif c.execute('SELECT 1 FROM receipts WHERE ticket=?',(ticket,)).fetchone():out='DUPLICATE_TICKET'
        else:
            put_record(c,ticket,epoch,permit['nonce']);out='COMMITTED'
        c.execute('COMMIT');return out,time.monotonic_ns()
    finally:
        if c.in_transaction:c.execute('ROLLBACK')
        c.close()

def inspect(root):
    c=connect(root)
    try:
        st=c.execute('SELECT epoch,armed,stopped FROM state WHERE id=1').fetchone()
        sets=[set(c.execute(f'SELECT ticket,epoch FROM {tab}').fetchall()) for tab in ('receipts','memory','plasticity')]
        used=c.execute('SELECT COUNT(*) FROM used_votes').fetchone()[0]
        good=c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        return st,len(sets[0]),sets[0]==sets[1]==sets[2] and len(sets[0])==used,good
    finally:c.close()

def safe_send(ch,value):
    try:ch.send(value)
    except (BrokenPipeError,EOFError,OSError):pass

def guard_actor(kind,ch):
    try:
        safe_send(ch,('READY',kind,os.getpid()))
        while True:
            if not ch.poll(.05):continue
            msg=ch.recv()
            if msg=='QUIT':return
            if not isinstance(msg,tuple) or len(msg)!=2 or msg[0]!='VOTE':continue
            safe_send(ch,('YES',kind,msg[1],time.monotonic_ns()))
    except (EOFError,ConnectionResetError,OSError):pass
    finally:ch.close()

def bypass_actor(root,ch):
    """Negative control: a process with the same OS UID ignores all lab gates."""
    try:
        c=connect(root)
        try:
            c.execute('BEGIN IMMEDIATE')
            ep,armed,stopped=c.execute('SELECT epoch,armed,stopped FROM state WHERE id=1').fetchone()
            for tab in ('receipts','memory','plasticity'):
                c.execute(f'INSERT INTO {tab}(ticket,epoch) VALUES(?,?)',('DIRECT_BYPASS',ep))
            c.execute('INSERT INTO used_votes(nonce,ticket) VALUES(?,?)',('BYPASS_NO_VOTES','DIRECT_BYPASS'))
            c.execute('COMMIT')
            safe_send(ch,('BYPASS_WRITTEN',stopped,armed,os.getuid()))
        finally:
            if c.in_transaction:c.execute('ROLLBACK')
            c.close()
    except BaseException as exc:safe_send(ch,('ERROR',type(exc).__name__,str(exc)[:90]))
    finally:ch.close()

def begin_actor(ctx,fn,*args):
    par,child=ctx.Pipe()
    p=ctx.Process(target=fn,args=(*args,child));p.start();child.close()
    return p,par

def expect(ch,what,timeout=8):
    if not ch.poll(timeout):raise TimeoutError('WAIT_'+what)
    result=ch.recv()
    if result[0]!=what:raise RuntimeError(f'EXPECTED_{what}_GOT_{result}')
    return result

def kill_actor(p):
    if p.is_alive():p.kill()
    p.join(3)
    if p.is_alive():raise TimeoutError('CHILD_STILL_ALIVE')

def actors(ctx):
    ap,ac=begin_actor(ctx,guard_actor,'INGRESS');expect(ac,'READY')
    wp,wc=begin_actor(ctx,guard_actor,'WATCHDOG');expect(wc,'READY')
    return [(ap,ac),(wp,wc)]

def approve(pair):
    """Synthetic dual-vote protocol; votes are not cryptographically authenticated."""
    if any(not p.is_alive() for p,_ in pair):return None
    nonce=secrets.token_hex(12)
    for _,ch in pair:safe_send(ch,('VOTE',nonce))
    for i,(_,ch) in enumerate(pair):
        try:
            if not ch.poll(3):return None
            response=ch.recv()
        except (EOFError,OSError):return None
        if response[:3]!=('YES',('INGRESS','WATCHDOG')[i],nonce):return None
    return {'nonce':nonce,'issued_ns':time.monotonic_ns()}

def cleanup(pair):
    for p,ch in reversed(pair):
        try:kill_actor(p)
        except BaseException:pass
        try:ch.close()
        except BaseException:pass

def run_case(ctx,root,mode):
    initialize(root)
    stage_ns=time.monotonic_ns();group=[];extra='';result='';valid=False
    try:
        if mode=='COLD_BOOT_DENIED':
            result,_=commit(root,'T',1,None);valid=result=='DISARMED'
        elif mode=='NEGATIVE_SAME_UID_DIRECT_DB_WRITE':
            transition(root,'STOP_DURABLE')
            p,ch=begin_actor(ctx,bypass_actor,root);group.append((p,ch))
            observed=expect(ch,'BYPASS_WRITTEN');p.join(4)
            if p.is_alive():raise TimeoutError('BYPASS_ACTOR_TIMEOUT')
            result='SAME_UID_BYPASS_OBSERVED'
            extra=f'actor_stopped={observed[1]} actor_uid={observed[3]}'
            valid=observed[1]==1 and observed[2]==0 and os.getuid()==observed[3]
        else:
            group=actors(ctx);transition(root,'LAB_ARM_SYNTHETIC')
            if mode=='INGRESS_DEAD_BEFORE_VOTE':kill_actor(group[0][0])
            if mode=='WATCHDOG_DEAD_BEFORE_VOTE':kill_actor(group[1][0])
            if mode=='BOTH_DEAD_BEFORE_VOTE':
                for p,_ in group:kill_actor(p)
            if mode in ('INGRESS_DEAD_BEFORE_VOTE','WATCHDOG_DEAD_BEFORE_VOTE','BOTH_DEAD_BEFORE_VOTE'):
                permit=approve(group)
                result,_=commit(root,'T',1,permit);valid=result=='NO_DUAL_VOTE'
            elif mode=='BOTH_GUARDS_ALIVE_COMMIT':
                permit=approve(group)
                result,_=commit(root,'T',1,permit);valid=result=='COMMITTED'
            elif mode=='ONE_SHOT_VOTE_REPLAY_DENIED':
                permit=approve(group);first,_=commit(root,'T1',1,permit)
                result,_=commit(root,'T2',1,permit)
                valid=first=='COMMITTED' and result=='VOTE_REPLAY'
                extra='first='+first
            elif mode=='VOTE_EXPIRED_DENIED':
                permit=approve(group)
                time.sleep(.88)
                result,_=commit(root,'T',1,permit);valid=result=='EXPIRED_VOTE'
            elif mode=='NEGATIVE_BOTH_DIE_AFTER_VOTES':
                permit=approve(group)
                if permit is None:raise RuntimeError('VOTE_NOT_READY')
                for p,_ in group:kill_actor(p)
                lastdeath=time.monotonic_ns()
                result,committed=commit(root,'T',1,permit)
                extra=f'commit_after_both_deaths_ms={(committed-lastdeath)/1e6:.3f}'
                valid=result=='COMMITTED' and committed>lastdeath
            elif mode=='NEGATIVE_BOTH_DIE_WITH_OPEN_TX':
                permit=approve(group)
                if permit is None:raise RuntimeError('VOTE_NOT_READY')
                c=connect(root)
                try:
                    c.execute('BEGIN IMMEDIATE')
                    ep,armed,stopped=c.execute('SELECT epoch,armed,stopped FROM state WHERE id=1').fetchone()
                    if ep!=1 or not armed or stopped:raise RuntimeError('GATE_NOT_ARMED')
                    put_record(c,'INFLIGHT',ep,permit['nonce'])
                    for p,_ in group:kill_actor(p)
                    lastdeath=time.monotonic_ns()
                    c.execute('COMMIT');committed=time.monotonic_ns()
                    result='INFLIGHT_COMMITTED_AFTER_BOTH_DEAD'
                    extra=f'commit_after_both_deaths_ms={(committed-lastdeath)/1e6:.3f}'
                    valid=committed>lastdeath
                finally:
                    if c.in_transaction:c.execute('ROLLBACK')
                    c.close()
            elif mode=='BOTH_DIE_RESTART_DISARMED':
                permit=approve(group)
                for p,_ in group:kill_actor(p)
                transition(root,'NEW_BOOT')
                result,_=commit(root,'T',2,permit);valid=result=='DISARMED'
            elif mode=='DURABLE_STOP_DUAL_CRASH_RESTART':
                permit=approve(group)
                transition(root,'STOP_DURABLE')
                for p,_ in group:kill_actor(p)
                transition(root,'NEW_BOOT')
                arm=transition(root,'LAB_ARM_SYNTHETIC')
                result,_=commit(root,'T',3,permit)
                valid=arm=='STOPPED' and result=='STOPPED'
            else:raise ValueError('UNKNOWN_MODE')
        st,rows,atomic,integrity=inspect(root)
        if mode in NEGATIVE:
            valid=valid and rows==1 and atomic and integrity
        if mode in ('BOTH_GUARDS_ALIVE_COMMIT','ONE_SHOT_VOTE_REPLAY_DENIED'):
            valid=valid and rows==1
        if mode not in NEGATIVE and mode not in ('BOTH_GUARDS_ALIVE_COMMIT','ONE_SHOT_VOTE_REPLAY_DENIED'):
            valid=valid and rows==0
        valid=valid and atomic and integrity
        return dict(mode=mode,status='EXPECTED_BEHAVIOR_PASS' if valid else 'FAIL',outcome=result,
            rows=rows,epoch=st[0],armed=st[1],stopped=st[2],atomic=atomic,integrity=integrity,
            negative=mode in NEGATIVE,extra=extra,elapsed_ms=(time.monotonic_ns()-stage_ns)/1e6)
    finally:cleanup(group)

def native_worker(binary,stop,out):
    measurements=[];errors=[]
    while not stop.is_set():
        try:
            run=subprocess.run([binary,'rank','full','0.70'],capture_output=True,text=True,timeout=5)
            if run.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',run.stdout):
                errors.append('S5_NATIVE_CONTRACT_FAIL');break
            m=re.search(r'estimated_F_GMAC_s=([0-9.]+)',run.stdout)
            if not m:errors.append('MISSING_F_GMAC_RATE');break
            measurements.append(float(m.group(1)))
        except BaseException as exc:errors.append(type(exc).__name__+':'+str(exc)[:60]);break
    try:out.put((os.getpid(),len(measurements),min(measurements) if measurements else None,
        statistics.mean(measurements) if measurements else None,errors),timeout=2)
    except BaseException:pass

def memory_holder(megabytes,stop,ready):
    try:
        buf=bytearray(megabytes*MiB)
        for i in range(0,len(buf),4096):buf[i]=1
        ready.put(('READY',os.getpid()),timeout=3)
        while not stop.wait(.2):
            for i in range(0,len(buf),262144):buf[i]^=1
    except BaseException as exc:
        try:ready.put(('ERROR',str(exc)[:100]),timeout=1)
        except BaseException:pass

def native_binary(override=None):
    path=Path(override) if override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not path.is_file() or not os.access(path,os.X_OK):raise RuntimeError('NATIVE_S5_BINARY_MISSING')
    run=subprocess.run([str(path),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=5)
    if run.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',run.stdout):
        raise RuntimeError('NATIVE_S5_SELFTEST_FAILURE')
    return str(path)

def stage(ctx,root,log,quick,name,n,ram,duration,repeats,binary):
    stop=ctx.Event();res=ctx.Queue();ready=ctx.Queue();workers=[];holder=None
    cases=[];errors=0;began=time.monotonic()
    try:
        holder=ctx.Process(target=memory_holder,args=(ram,stop,ready));holder.start()
        msg=ready.get(timeout=6)
        if msg[0]!='READY':raise RuntimeError('RAM_HOLDER_FAILED '+str(msg))
        for _ in range(n):
            p=ctx.Process(target=native_worker,args=(binary,stop,res));p.start();workers.append(p)
        log(f'STAGE_BEGIN name={name} native_S5_workers={n} touched_RAM_MiB={ram} duration_floor_s={duration}')
        for repeat in range(1,repeats+1):
            for mode in MODES:
                issue=safety(quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                try:r=run_case(ctx,root/f'{name}_{repeat}_{mode}',mode)
                except BaseException as exc:
                    errors+=1;log(f'CASE stage={name} rep={repeat} mode={mode} status=ERROR exception={type(exc).__name__}:{exc}');continue
                cases.append(r)
                if r['status']!='EXPECTED_BEHAVIOR_PASS':errors+=1
                log(f"CASE stage={name} rep={repeat} mode={mode} status={r['status']} outcome={r['outcome']} "
                    f"rows={r['rows']} epoch={r['epoch']} armed={r['armed']} stopped={r['stopped']} "
                    f"atomic={r['atomic']} integrity={r['integrity']} negative_control={r['negative']} "
                    f"elapsed_ms={r['elapsed_ms']:.3f} {r['extra']}")
        while time.monotonic()<began+duration:
            issue=safety(quick)
            if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
            time.sleep(.15)
    finally:
        stop.set()
        for p in workers:
            p.join(4)
            if p.is_alive():p.kill();p.join(2)
        if holder is not None:
            holder.join(2)
            if holder.is_alive():holder.kill();holder.join(2)
        for _ in workers:
            try:
                pid,runs,minimum,mean,failures=res.get(timeout=2)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={runs} min_GMAC_s={minimum} mean_GMAC_s={mean} errors={failures}')
                if runs<1 or failures:errors+=1
            except queue.Empty:errors+=1;log('S5_WORKER_FAILURE missing_result')
        res.cancel_join_thread();res.close();ready.cancel_join_thread();ready.close()
    negative_count=sum(c['negative'] and c['status']=='EXPECTED_BEHAVIOR_PASS' for c in cases)
    log(f'STAGE_SUMMARY stage={name} cases={len(cases)} expected={repeats*len(MODES)} '
        f'failures={errors} negative_controls_reproduced={negative_count} '
        f'restart_denials={sum(c["mode"]=="BOTH_DIE_RESTART_DISARMED" and c["status"]=="EXPECTED_BEHAVIOR_PASS" for c in cases)}')
    return errors==0 and len(cases)==repeats*len(MODES),cases

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--quick',action='store_true',help='local smoke test ONLY, not phone evidence')
    p.add_argument('--binary',help='local S5 binary override; omit on phone')
    args=p.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_DUAL_FAILURE_BYPASS_STRESS_V6_{stamp}.txt'
    with report.open('x',encoding='utf-8') as file:
        def log(s):print(s,flush=True);file.write(s+'\n');file.flush()
        try:
            log('UNO / UNOVYRA -- DUAL GUARD CRASH, PERMIT REPLAY AND SAME-UID BYPASS UNDER REAL NATIVE S5 LOAD '+VERSION)
            log('Synthetic ingress + watchdog roles; two one-shot per-commit votes. Not cryptographic owner authentication.')
            log('All cases run while native ARM C256R32 FP32 S5 is computing on Android CPU (2 or 4 workers + 32/64MiB RAM).')
            log('Negative controls intentionally show: both guards dead AFTER approval can still be followed by COMMIT; same-UID DB writer can bypass app gates.')
            log('This is a PRECODE fixture, not a real trusted Android permission boundary, user STOP, production agent, or neural P training.')
            log('No Android actions, root, USB, ADB, network, reboot, or modification outside own Termux lab directory.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            issue=safety(args.quick)
            if issue:log('RESULT SAFETY_SKIP '+issue);return 3
            binary=native_binary(args.binary);log('VERIFIED_NATIVE_S5 '+binary)
            root=home/'uno_a52_r41_dual_guard_stress_v6'/stamp;root.mkdir(parents=True,mode=0o700,exist_ok=False)
            ctx=mp.get_context('fork')
            plans=[('S5x2_RAM32',2,32,7,1),('S5x4_RAM64',4,64,8,1)] if args.quick else [
                ('S5x2_RAM32',2,32,24,2),('S5x4_RAM64',4,64,30,2)]
            total=0;observed=0;allpass=True
            for name,n,ram,duration,reps in plans:
                issue=safety(args.quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                good,cases=stage(ctx,root,log,args.quick,name,n,ram,duration,reps,binary)
                total+=len(cases);observed+=sum(c['negative'] and c['status']=='EXPECTED_BEHAVIOR_PASS' for c in cases)
                allpass=allpass and good
                b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
                if not good:break
            log(f'RESULT {"EXPECTED_FINDINGS_REPRODUCED" if allpass else "FAIL_OR_INCOMPLETE"} cases={total} negative_control_findings={observed}')
            log('IMPORTANT: expected negative findings are NOT safety passes. Live actors before commit are NOT enough to prevent post-check commit after both die.')
            log('IMPORTANT: lab SQLite gates cannot enforce Android trust isolation against same-UID writers. Need process/UID/capability separation for real controller.')
            log('UNRESOLVED: user STOP physical press, platform-level isolation, power cut, already linearized Android effects, hard real-time SLA.')
            log('REPORT '+str(report))
            return 0 if allpass else 2
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPT');log('REPORT '+str(report));return 130
        except BaseException as exc:
            log('RESULT ERROR '+type(exc).__name__+': '+str(exc)[:200]);log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
