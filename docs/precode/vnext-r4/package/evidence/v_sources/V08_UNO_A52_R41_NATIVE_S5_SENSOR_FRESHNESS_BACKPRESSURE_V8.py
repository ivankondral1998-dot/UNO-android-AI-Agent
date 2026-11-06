#!/usr/bin/env python3
"""UNO R4.1 S5-loaded sensor freshness/backpressure precode experiment V8.

Not production code, no Android actions, not an OS security boundary.
This is a directed comparison of a V7-style sequence-only store with a
new keyed, bounded, locally shared sensor register that survives DATA FIFO overflow.
OWNER_APPROVED_PRECODE=FALSE.
"""
from __future__ import annotations
import argparse
import datetime as dt
import math
import multiprocessing as mp
import os
import queue
import re
import sqlite3
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

VERSION='UNO_R41_A52_NATIVE_S5_SENSOR_FRESHNESS_BACKPRESSURE_V8'
CHANNELS=('battery','temp','cpu6','memavailable','voltage','status')
PATHS={'battery':'/sys/class/power_supply/battery/capacity',
       'temp':'/sys/class/power_supply/battery/temp',
       'cpu6':'/sys/devices/system/cpu/cpu6/cpufreq/scaling_cur_freq',
       'voltage':'/sys/class/power_supply/battery/voltage_now'}
N=len(CHANNELS)
W=6; STOP_POS=N*W
MiB=1048576
CAP=24

def read_int(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:
        avail=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    except (OSError,ValueError,IndexError,StopIteration):avail=None
    return read_int(PATHS['battery']),read_int(PATHS['temp']),avail

def read_real():
    values={k:read_int(v) for k,v in PATHS.items()}
    values['memavailable']=telemetry()[2]
    try:status=Path('/sys/class/power_supply/battery/status').read_text().strip()
    except OSError:status=''
    values['status']={'Charging':1,'Full':2,'Not charging':0,'Discharging':-1}.get(status)
    return values

def safety(quick):
    if quick:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100<=t<=800:return 'REQUIRED_TELEMETRY_MISSING'
    if b<40:return 'BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'BATTERY_TEMP_AT_LEAST_37_5C'
    if m<400000:return 'AVAILABLE_RAM_BELOW_400000_KB'
    return None

def initialize_slots(ctx):
    a=ctx.Array('q',N*W+1,lock=True)
    with a.get_lock():
        for i in range(N):
            a[W*i]=-1; a[W*i+1]=-1; a[W*i+2]=-1
    return a

def dump_slots(a):
    with a.get_lock():
        d={}
        for j,ch in enumerate(CHANNELS):
            b=W*j;d[ch]={'gen':a[b],'ns':a[b+1],'seq':a[b+2],
                         'value':a[b+3] if a[b+4] else None,
                         'present':bool(a[b+4]),'revision':a[b+5]}
        return d,bool(a[STOP_POS])

def publish(a,channel,gen,stamp,seq,value,missing=False):
    """Validation before shared write; status is explicit; no guessed thresholds."""
    if channel not in CHANNELS or type(gen) is not int or not 0<=gen<2**31 or \
       type(stamp) is not int or stamp<0 or type(seq) is not int or not 0<=seq<2**63 or \
       type(missing) is not bool or \
       (missing and value is not None) or \
       (not missing and (type(value) is not int or not -(2**62)<value<2**62)):
        return 'INVALID'
    # Test-only finite monotonic-clock horizon, NOT an approved SENSOR TTL.
    if stamp>time.monotonic_ns()+10_000_000:return 'FUTURE_REJECTED'
    idx=CHANNELS.index(channel)*W
    with a.get_lock():
        if a[STOP_POS]:return 'STOPPED'
        old=(a[idx],a[idx+1],a[idx+2])
        key=(gen,stamp,seq)
        if key<=old:return 'OLD_REJECTED'
        a[idx]=gen;a[idx+1]=stamp;a[idx+2]=seq
        a[idx+3]=0 if missing else value
        a[idx+4]=0 if missing else 1
        a[idx+5]+=1
        return 'UPDATED'

def open_db(path):
    c=sqlite3.connect(str(path),timeout=4,isolation_level=None)
    c.execute('PRAGMA synchronous=FULL')
    c.execute('PRAGMA busy_timeout=4000')
    return c

def create_db(path):
    c=open_db(path)
    try:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), stopped INTEGER NOT NULL)')
        c.execute('INSERT INTO state VALUES(1,0)')
    finally:c.close()

def read_db(path):
    c=open_db(path)
    try:return c.execute('SELECT stopped FROM state WHERE id=1').fetchone()[0],c.execute('PRAGMA integrity_check').fetchone()[0]
    finally:c.close()

def broker(a,dataq,ctrl,db):
    c=open_db(db);count=0;post=0
    try:
        ctrl.send(('READY',os.getpid()))
        while True:
            if ctrl.poll():
                cmd=ctrl.recv()
                if cmd=='QUIT':return
                if cmd=='STATS':ctrl.send(('STATS',count,post));continue
                if cmd=='STOP':
                    receive=time.monotonic_ns()
                    c.execute('BEGIN IMMEDIATE')
                    c.execute('UPDATE state SET stopped=1 WHERE id=1')
                    c.execute('COMMIT')
                    # ACK follows durable SQLite commit. This is not atomic with
                    # the sensor register; request-to-ACK remains a known gap.
                    with a.get_lock():a[STOP_POS]=1
                    ctrl.send(('ACK',receive,time.monotonic_ns(),count,post))
                    continue
            try:_=dataq.get(timeout=.003)
            except queue.Empty:continue
            with a.get_lock(): stopped=bool(a[STOP_POS])
            if stopped:post+=1
            else:count+=1
            time.sleep(.0015)  # deliberately slow synthetic data consumer
    finally:
        if c.in_transaction:c.execute('ROLLBACK')
        c.close();ctrl.close()

def start_broker(ctx,root):
    root.mkdir(parents=True,mode=0o700,exist_ok=False)
    a=initialize_slots(ctx)
    db=root/'stop.sqlite3';create_db(db)
    dataq=ctx.Queue(maxsize=CAP)
    parent,child=ctx.Pipe(duplex=True)
    p=ctx.Process(target=broker,args=(a,dataq,child,db));p.start();child.close()
    if not parent.poll(8):raise TimeoutError('CONTROLLER_NOT_READY')
    if parent.recv()[0]!='READY':raise RuntimeError('CONTROLLER_READY_INVALID')
    return p,a,db,dataq,parent

def end_broker(p,q,conn):
    if p.is_alive():
        try:conn.send('QUIT')
        except (OSError,EOFError):pass
    p.join(2)
    if p.is_alive():p.kill();p.join(2)
    conn.close();q.cancel_join_thread();q.close()

def stop_ack(conn):
    before=time.monotonic_ns();conn.send('STOP')
    if not conn.poll(5):raise TimeoutError('STOP_ACK_TIMEOUT')
    ret=conn.recv();after=time.monotonic_ns()
    if ret[0]!='ACK':raise RuntimeError('WRONG_STOP_ACK')
    return {'ack_ms':(after-before)/1e6,'receive_ms':(ret[1]-before)/1e6,
            'latch_ms':(ret[2]-before)/1e6}

def flood(q,count):
    rejected=0;accepted=0
    for i in range(count):
        try:q.put_nowait(b'PCM_SYNTHETIC_FRAME_OR_SCREEN'+str(i).encode());accepted+=1
        except queue.Full:rejected+=1
    return accepted,rejected

def real_seed(a):
    values=read_real();ts=time.monotonic_ns()
    for i,ch in enumerate(CHANNELS):
        value=values[ch]
        st=publish(a,ch,1,ts+i,1,value,value is None)
        if st!='UPDATED':raise AssertionError('FAILED_REAL_SENSOR_SEED')
    return values

def one_case(ctx,root,mode):
    p,a,db,q,ctrl=start_broker(ctx,root)
    try:
        real=real_seed(a)
        initial,_=dump_slots(a)
        ts=time.monotonic_ns()-2_000_000
        reasons=[];expected=None;negative=0;drops=0;offered=0
        ch='cpu6'
        if mode=='REORDERED_NEWEST_WINS':
            # Same source-generation, higher sequence but older SAMPLE timestamp:
            # V7-style seq-only replacement erroneously accepts the stale payload.
            assert publish(a,ch,2,ts,100,202600,False)=='UPDATED'
            oldstamp=ts-500_000_000
            verdict=publish(a,ch,2,oldstamp,101,111111,False)
            reasons.append(verdict)
            assert verdict=='OLD_REJECTED'
            v7_like={'seq':100,'time':ts,'value':202600}
            if 101>v7_like['seq']:
                v7_like={'seq':101,'time':oldstamp,'value':111111}
            negative=int(v7_like['time']<ts and v7_like['value']==111111)
            expected=(2,ts,100,202600,True)
        elif mode=='GENERATION_REPLAY_DENIED':
            assert publish(a,ch,2,ts,22,222222,False)=='UPDATED'
            reasons.append(publish(a,ch,1,ts+1,999999,777777,False))
            reasons.append(publish(a,ch,2,ts-1,999999,666666,False))
            assert reasons==['OLD_REJECTED','OLD_REJECTED']
            expected=(2,ts,22,222222,True)
        elif mode=='MISSING_NEWER_IS_NOT_ZERO':
            assert publish(a,ch,2,ts,10,0,False)=='UPDATED'
            assert publish(a,ch,2,ts+1,11,None,True)=='UPDATED'
            reasons.append(publish(a,ch,2,ts-1,12,938000,False))
            assert reasons==['OLD_REJECTED']
            expected=(2,ts+1,11,None,False)
        elif mode=='INVALID_AND_FUTURE_REJECT':
            assert publish(a,ch,2,ts,30,0,False)=='UPDATED'
            negatives=[(2,ts+1,31,float('nan'),False),
                       (2,ts+2,32,None,False),
                       (2,ts+3,33,0,True),
                       (2,ts+4,34,True,False),
                       (2,ts+5,-1,5,False),
                       (2,time.monotonic_ns()+2_000_000_000,36,5,False)]
            reasons=[publish(a,ch,gen,t,s,val,miss) for gen,t,s,val,miss in negatives]
            assert reasons==['INVALID']*5+['FUTURE_REJECTED'],reasons
            expected=(2,ts,30,0,True)
        elif mode=='QUEUE_OVERFLOW_SENSOR_LAST_WINS':
            # Saturate a bounded DATA FIFO. Sensors bypass it via six keyed slots.
            accepted,drops=flood(q,1800)
            offered=accepted+drops
            start=time.monotonic_ns()-3_000_000
            assert publish(a,ch,2,start,40,400000,False)=='UPDATED'
            for i in range(400):
                stamp=start+i*1000
                assert publish(a,ch,2,stamp,41+i,500000+i,False)=='UPDATED'
            expected=(2,start+399000,440,500399,True)
            assert publish(a,ch,2,start+398000,99999,123,False)=='OLD_REJECTED'
            negative=0  # overflow is a distinct finding, not a seq-only comparator finding
        else:raise ValueError('UNKNOWN_CASE')
        slots_before,stop_before=dump_slots(a)
        current=slots_before[ch]
        got=(current['gen'],current['ns'],current['seq'],current['value'],current['present'])
        fresh=(got==expected and not stop_before)
        # Other real sensor channels retain their original values, including
        # explicit missing masks. None are fabricated by this stress fixture.
        others_ok=all((slots_before[k]['value']==real[k] if real[k] is not None
                       else not slots_before[k]['present']) for k in CHANNELS if k!=ch)
        timing=stop_ack(ctrl)
        before_post,_=dump_slots(a)
        post_status=publish(a,ch,3,time.monotonic_ns(),10000000,1,False)
        after_post,stop_flag=dump_slots(a)
        dbstop,integrity=read_db(db)
        valid=bool(fresh and others_ok and post_status=='STOPPED' and
                   before_post==after_post and stop_flag and dbstop==1 and integrity=='ok' and
                   (mode!='REORDERED_NEWEST_WINS' or negative==1) and
                   (mode!='QUEUE_OVERFLOW_SENSOR_LAST_WINS' or (drops>0 and offered==1800)))
        return {'mode':mode,'pass':valid,'ack_ms':timing['ack_ms'],
                'latch_ms':timing['latch_ms'],'readable':sum(v is not None for v in real.values()),
                'fresh':fresh,'others':others_ok,'post':post_status,
                'dropped':drops,'offered':offered,'negative':negative,
                'mask':int(current['present']),'gen':current['gen'],
                'seq':current['seq'],'value':current['value'],
                'reasons':reasons,'integrity':integrity}
    finally:end_broker(p,q,ctrl)

def native_bin(override):
    path=Path(override) if override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not path.is_file() or not os.access(path,os.X_OK):raise RuntimeError('NATIVE_S5_BINARY_MISSING')
    x=subprocess.run([str(path),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=6)
    if x.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',x.stdout):raise RuntimeError('NATIVE_S5_SELFTEST_FAILED')
    return str(path)

def native_worker(binary,ev,out,active):
    rates=[];errors=[]
    while not ev.is_set():
        try:
            p=subprocess.run([binary,'rank','full','0.70'],capture_output=True,text=True,timeout=6)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):
                errors.append('BAD_NATIVE_S5_CONTRACT');break
            match=re.search(r'estimated_F_GMAC_s=([0-9.]+)',p.stdout)
            if not match:errors.append('NO_GMAC_METRIC');break
            rates.append(float(match.group(1)))
            if len(rates)==1:
                try:active.put(('ACTIVE',os.getpid()),timeout=2)
                except BaseException:errors.append('ACTIVE_SIGNAL_FAILED');break
        except BaseException as exc:errors.append(type(exc).__name__);break
    try:out.put((os.getpid(),len(rates),min(rates) if rates else None,
                 statistics.mean(rates) if rates else None,errors),timeout=2)
    except BaseException:pass

def memory_hold(meg,ev,ready):
    try:
        b=bytearray(meg*MiB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(('READY',os.getpid()),timeout=2)
        while not ev.wait(.15):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException as e:
        try:ready.put(('ERROR',str(e)[:90]),timeout=1)
        except BaseException:pass

def run_stage(ctx,root,log,quick,stage,num,ram,minimum,repeats,binary):
    cancel=ctx.Event();out=ctx.Queue();ready=ctx.Queue();active=ctx.Queue();workers=[];holder=None
    cases=[];fail=0;since=time.monotonic()
    try:
        holder=ctx.Process(target=memory_hold,args=(ram,cancel,ready));holder.start()
        msg=ready.get(timeout=7)
        if msg[0]!='READY':raise RuntimeError('MEMORY_RESERVATION_FAILED '+str(msg))
        for i in range(num):
            p=ctx.Process(target=native_worker,args=(binary,cancel,out,active));p.start();workers.append(p)
        # Do not begin a directed case before ALL native S5 workers have
        # actually completed their first FP32 run on the device.
        until=time.monotonic()+25
        confirmed=set()
        while len(confirmed)<num:
            left=until-time.monotonic()
            if left<=0:raise TimeoutError('NATIVE_S5_LOAD_NOT_CONFIRMED')
            try:msg=active.get(timeout=left)
            except queue.Empty:raise TimeoutError('NATIVE_S5_LOAD_NOT_CONFIRMED')
            if msg[0]!='ACTIVE':raise RuntimeError('NATIVE_LOAD_INVALID_READY')
            confirmed.add(msg[1])
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={stage} workers={len(confirmed)}')
        log(f'STAGE_BEGIN name={stage} native_s5_workers={num} held_ram_MiB={ram} min_duration_s={minimum}')
        modes=('REORDERED_NEWEST_WINS','GENERATION_REPLAY_DENIED','MISSING_NEWER_IS_NOT_ZERO',
               'INVALID_AND_FUTURE_REJECT','QUEUE_OVERFLOW_SENSOR_LAST_WINS')
        for rep in range(1,repeats+1):
            for mode in modes:
                err=safety(quick)
                if err:raise RuntimeError('SAFETY_ABORT_'+err)
                try:
                    result=one_case(ctx,root/f'{stage}_{rep}_{mode}',mode);cases.append(result)
                    if not result['pass']:fail+=1
                    log(f"CASE stage={stage} rep={rep} mode={mode} status={'PASS' if result['pass'] else 'FAIL'} "
                        f"freshness_verified={result['fresh']} real_sensor_fields={result['readable']}/6 "
                        f"gen={result['gen']} seq={result['seq']} value={result['value']} present_mask={result['mask']} "
                        f"dropped_data={result['dropped']}/{result['offered']} "
                        f"seq_only_negative_control={result['negative']} post_stop={result['post']} "
                        f"stop_ack_ms={result['ack_ms']:.3f} sqlite_integrity={result['integrity']}")
                except BaseException as e:
                    fail+=1;log(f'CASE stage={stage} rep={rep} mode={mode} status=ERROR reason={type(e).__name__}:{str(e)[:140]}')
        while time.monotonic()<since+minimum:
            err=safety(quick)
            if err:raise RuntimeError('SAFETY_ABORT_'+err)
            time.sleep(.12)
    finally:
        cancel.set()
        for p in workers:
            p.join(5)
            if p.is_alive():p.kill();p.join(2)
        if holder:
            holder.join(3)
            if holder.is_alive():holder.kill();holder.join(2)
        for p in workers:
            try:
                pid,runs,low,mean,problems=out.get(timeout=2)
                log(f'S5_WORKER stage={stage} pid={pid} runs={runs} min_GMAC_s={low} mean_GMAC_s={mean} errors={problems}')
                if problems or not runs:fail+=1
            except queue.Empty:fail+=1;log(f'S5_WORKER stage={stage} status=MISSING_RESULT')
        out.cancel_join_thread();out.close();ready.cancel_join_thread();ready.close();active.cancel_join_thread();active.close()
    ack=[r['ack_ms'] for r in cases]
    log(f'STAGE_SUMMARY name={stage} cases={len(cases)} expected={5*repeats} '
        f'failures={fail} stop_ack_max_ms={max(ack) if ack else None} '
        f'data_fifo_drops={sum(r["dropped"] for r in cases)} '
        f'v7_seq_only_negative_reproduced={sum(r["negative"] for r in cases if r["mode"]=="REORDERED_NEWEST_WINS")}')
    return fail==0 and len(cases)==5*repeats,len(cases)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--quick',action='store_true',help='short smoke check only; NOT device evidence')
    parser.add_argument('--binary',help='native S5 path override for local smoke test')
    args=parser.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_SENSOR_FRESHNESS_STRESS_V8_{stamp}.txt'
    with report.open('x',encoding='utf-8') as file:
        def log(s):print(s,flush=True);file.write(s+'\n');file.flush()
        try:
            log('UNO / UNOVYRA -- NATIVE S5 SENSOR LATEST-SAMPLE BACKPRESSURE STRESS '+VERSION)
            log('On A52: native ARM S5 CPU runs continuously per stage; real sysfs/proc sensors seed bounded six-slot shared register.')
            log('Directed V7-like seq-only negative control versus candidate generation/sample-time/seq latest-wins arbitration.')
            log('Separate 24-entry slow DATA FIFO and STOP IPC; DATA overflow cannot evict keyed sensor slots in this fixture.')
            log('STOP request != durable ACK. No Android Binder, OS dispatch, real microphone/screen, trained neural P, authenticated owner or production controller.')
            log('Fixed monotonic future-skew filter is synthetic; no production sensor TTL, dictionary, or hardware durability approved.')
            log('No root, ADB, USB, network, APK, permissions or system changes. OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            issue=safety(args.quick)
            if issue:log('RESULT SAFETY_SKIP '+issue);return 3
            binary=native_bin(args.binary);log('VERIFIED_NATIVE_S5 '+binary)
            ctx=mp.get_context('fork')
            root=home/'uno_a52_r41_sensor_freshness_stress_v8'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            plans=[('S5x2_RAM32',2,32,7,1),('S5x4_RAM64',4,64,8,1)] if args.quick else [
                ('S5x2_RAM32',2,32,24,2),('S5x4_RAM64',4,64,30,2)]
            total=0;passes=True
            for name,n,ram,minimum,repeats in plans:
                issue=safety(args.quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                good,num=run_stage(ctx,root,log,args.quick,name,n,ram,minimum,repeats,binary)
                total+=num;passes=passes and good
                b,t,m=telemetry();log(f'STAGE_TELEMETRY name={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
                if not good:break
            log(f'RESULT {"PASS_BOUNDED_LATEST_SAMPLE_FIXTURE" if passes else "FAIL_OR_INCOMPLETE"} cases={total}')
            log('LIMIT: source-generated fixture values synthetic; only seed readings are real. Same-UID shared memory is not a trusted Android boundary.')
            log('LIMIT: no guaranteed STOP-from-physical-press or power-cut durability; V7 seq-only outcome is a code-rule replica, not an independent V7 binary replay.')
            log('REPORT '+str(report))
            return 0 if passes else 2
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPTED');log('REPORT '+str(report));return 130
        except BaseException as e:
            log('RESULT ERROR '+type(e).__name__+': '+str(e)[:180]);log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
