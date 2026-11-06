#!/usr/bin/env python3
"""UNO R4.1 V19 isolated causal clock / timer / one-shot outbox lab.

Virtual event time is used for deterministic S2/S3 ordering; actual Android
monotonic timer jitter is measured separately under continuously active native S5.
No production agent, Android action or authority is implemented.
"""
from __future__ import annotations
import argparse
import datetime as dt
import heapq
import multiprocessing as mp
import os
from pathlib import Path
import queue
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_CAUSAL_CLOCK_TIMER_RACE_V19'
MIB=1048576
MODES=(
 'TIMER_BEFORE_EXTERNAL', 'NEW_EARLIER_TIMER', 'STOP_PRECEDES_DUE_TIMER',
 'REVOKE_PRECEDES_OWNER', 'DEATH_PRECEDES_SENSOR', 'DEADLINE_PRECEDES_OUTBOX',
 'READBACK_PRECEDES_OWNER', 'EQUAL_PRIORITY_SERIAL', 'IMMEDIATE_TIMER_MICROSTEP',
 'REVOKE_PENDING_OUTBOX', 'OUTBOX_SINGLE_CONSUME', 'STOP_AFTER_ISSUE',
 'NO_EVENTS_NO_NEURAL_TICKS', 'BOOT_INVALIDATES_OLD_TIMER',
)
PRIORITY={'STOP':0,'REVOKE':0,'DEATH':0,'BOOT':0,'DEADLINE':1,
          'READBACK':2,'OWNER':3,'ARM_TIMER':3,'SENSOR':4,'TIMER':5}
CONTROL={'STOP','REVOKE','DEATH','BOOT','DEADLINE'}


def readnum(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:mem=int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])
    except (OSError,ValueError,StopIteration,IndexError):mem=None
    try:charge=Path('/sys/class/power_supply/battery/status').read_text().strip()
    except OSError:charge='UNAVAILABLE'
    return {'battery':readnum('/sys/class/power_supply/battery/capacity'),
            'battery_temp_deciC':readnum('/sys/class/power_supply/battery/temp'),
            'MemAvailable_kB':mem,'charge':charge}

def guard(host):
    if host:return None
    a=telemetry();b=a['battery'];t=a['battery_temp_deciC'];m=a['MemAvailable_kB']
    if None in (b,t,m) or not 100<=t<=800:return 'SAFETY_TELEMETRY_UNAVAILABLE'
    if b<40:return 'SAFETY_BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'SAFETY_BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'SAFETY_MEMAVAILABLE_LT_400000_KB'
    return None

def native_binary(host,override):
    p=Path(override) if host and override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_MISSING '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=15)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_S5_CONTRACT_NOT_PASS '+r.stdout[-180:])
    return p

def s5worker(binary,stop,ready,out):
    values=[];errors=[]
    try:
        while not stop.is_set():
            r=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=18)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
                raise RuntimeError('NATIVE_S5_WORKER_FAILED')
            m=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not m:raise RuntimeError('NATIVE_S5_THROUGHPUT_MISSING')
            values.append(float(m[1]))
            if len(values)==1:ready.put(os.getpid(),timeout=4)
    except BaseException as e:errors.append(str(e)[:160])
    try:out.put((os.getpid(),len(values),statistics.mean(values) if values else None,
                 min(values) if values else None,errors),timeout=3)
    except BaseException:pass

def ramholder(stop,ready):
    try:
        a=bytearray(32*MIB)
        for i in range(0,len(a),4096):a[i]=1
        ready.put(True,timeout=4)
        while not stop.wait(0.15):
            for i in range(0,len(a),262144):a[i]^=1
    except BaseException:
        try:ready.put(False,timeout=3)
        except BaseException:pass

# Event = tuple(time_monotonic_virtual_ms, priority, source_serial, insertion_id, type, payload)
class Scheduler:
    def __init__(self):
        self.heap=[];self.counter=0;self.now=0;self.stop=False;self.revoke=False
        self.dead=False;self.deadline=False;self.boot=1;self.outbox=None
        self.traces=[];self.neural=[];self.issue=[];self.consumed=0
        self.denied=0;self.quarantine=0;self.micro=0;self.times=[]
    def push(self,t,kind,serial=0,payload=None):
        if not isinstance(t,int) or t<self.now or kind not in PRIORITY:raise ValueError('BAD_EVENT')
        self.counter+=1
        heapq.heappush(self.heap,(t,PRIORITY[kind],serial,self.counter,kind,payload))
    def run(self):
        processed=0
        while self.heap:
            if processed>=64:raise RuntimeError('EVENT_LIMIT')
            t=self.heap[0][0]
            if t<self.now:raise AssertionError('CAUSAL_TIME_WENT_BACKWARD')
            if t==self.now and self.times:self.micro+=1
            self.now=t;self.times.append(t)
            # Drain same-time external/control/due events before consuming the *previous* outbox.
            # A newly scheduled timer at current time becomes a zero-duration microstep.
            batch=[]
            while self.heap and self.heap[0][0]==t:
                batch.append(heapq.heappop(self.heap))
            batch.sort()
            controls=[e for e in batch if e[4] in CONTROL]
            others=[e for e in batch if e[4] not in CONTROL]
            for e in controls:
                _,_,serial,_,kind,payload=e
                self.traces.append(f'{kind}@{t}#{serial}')
                if kind=='STOP':self.stop=True
                elif kind=='REVOKE':self.revoke=True
                elif kind=='DEATH':self.dead=True
                elif kind=='DEADLINE':self.deadline=True
                elif kind=='BOOT':self.boot+=1
                processed+=1
            if self.outbox is not None:
                self.consumed+=1
                if not (self.stop or self.revoke or self.dead or self.deadline):
                    self.issue.append((t,self.outbox))  # synthetic request, NOT OS effect
                else:self.denied+=1
                self.outbox=None
            for e in others:
                _,_,serial,_,kind,payload=e
                self.traces.append(f'{kind}@{t}#{serial}')
                if kind=='ARM_TIMER':
                    # (due_time, boot_generation) is an internal timer, not an OS permission
                    due=payload if payload is not None else t
                    self.push(due,'TIMER',serial+1,self.boot)
                elif kind=='OWNER':
                    if self.stop or self.revoke or self.dead or self.deadline:self.denied+=1
                    elif self.outbox is None:self.outbox=f'outbox_from_{t}_{serial}'
                    else:raise AssertionError('UNCONSUMED_OUTBOX_OVERWRITE')
                elif kind in ('SENSOR','TIMER'):
                    if kind=='TIMER' and payload!=self.boot:self.quarantine+=1
                    elif not (self.stop or self.revoke or self.dead or self.deadline):
                        self.neural.append((t,kind,serial))
                elif kind=='READBACK':pass
                processed+=1
        # Crucial: idle does NOT consume newly created outbox or generate a neural tick.
        return self

def scenario(mode):
    s=Scheduler()
    if mode=='TIMER_BEFORE_EXTERNAL':
        s.push(5,'TIMER',1,1);s.push(10,'SENSOR',2)
        expected=['TIMER@5#1','SENSOR@10#2'];nf=2;ni=0
    elif mode=='NEW_EARLIER_TIMER':
        s.push(10,'TIMER',1,1);s.push(2,'ARM_TIMER',2,4)
        expected=['ARM_TIMER@2#2','TIMER@4#3','TIMER@10#1'];nf=2;ni=0
    elif mode=='STOP_PRECEDES_DUE_TIMER':
        s.push(5,'TIMER',2,1);s.push(5,'STOP',1)
        expected=['STOP@5#1','TIMER@5#2'];nf=0;ni=0
    elif mode=='REVOKE_PRECEDES_OWNER':
        s.push(5,'OWNER',2);s.push(5,'REVOKE',1)
        expected=['REVOKE@5#1','OWNER@5#2'];nf=0;ni=0
    elif mode=='DEATH_PRECEDES_SENSOR':
        s.push(5,'SENSOR',2);s.push(5,'DEATH',1)
        expected=['DEATH@5#1','SENSOR@5#2'];nf=0;ni=0
    elif mode=='DEADLINE_PRECEDES_OUTBOX':
        s.push(1,'OWNER',1);s.push(2,'SENSOR',2);s.push(2,'DEADLINE',1)
        expected=['OWNER@1#1','DEADLINE@2#1','SENSOR@2#2'];nf=0;ni=0
    elif mode=='READBACK_PRECEDES_OWNER':
        s.push(5,'OWNER',2);s.push(5,'READBACK',1)
        expected=['READBACK@5#1','OWNER@5#2'];nf=0;ni=0
    elif mode=='EQUAL_PRIORITY_SERIAL':
        s.push(5,'SENSOR',20);s.push(5,'SENSOR',3)
        expected=['SENSOR@5#3','SENSOR@5#20'];nf=2;ni=0
    elif mode=='IMMEDIATE_TIMER_MICROSTEP':
        s.push(4,'ARM_TIMER',1,4);s.push(8,'SENSOR',3)
        expected=['ARM_TIMER@4#1','TIMER@4#2','SENSOR@8#3'];nf=2;ni=0
    elif mode=='REVOKE_PENDING_OUTBOX':
        s.push(1,'OWNER',1);s.push(2,'REVOKE',1);s.push(3,'SENSOR',1)
        expected=['OWNER@1#1','REVOKE@2#1','SENSOR@3#1'];nf=0;ni=0
    elif mode=='OUTBOX_SINGLE_CONSUME':
        s.push(1,'OWNER',1);s.push(2,'SENSOR',1);s.push(3,'SENSOR',2)
        expected=['OWNER@1#1','SENSOR@2#1','SENSOR@3#2'];nf=2;ni=1
    elif mode=='STOP_AFTER_ISSUE':
        s.push(1,'OWNER',1);s.push(2,'SENSOR',1);s.push(3,'STOP',1)
        expected=['OWNER@1#1','SENSOR@2#1','STOP@3#1'];nf=1;ni=1
    elif mode=='NO_EVENTS_NO_NEURAL_TICKS':
        expected=[];nf=0;ni=0
    elif mode=='BOOT_INVALIDATES_OLD_TIMER':
        s.push(2,'BOOT',1);s.push(5,'TIMER',1,1);s.push(6,'SENSOR',1)
        expected=['BOOT@2#1','TIMER@5#1','SENSOR@6#1'];nf=1;ni=0
    else:raise ValueError('UNKNOWN_SCENARIO')
    s.run()
    ok=(s.traces==expected and len(s.neural)==nf and len(s.issue)==ni
        and s.consumed==(1 if mode in ('DEADLINE_PRECEDES_OUTBOX','REVOKE_PENDING_OUTBOX',
                                      'OUTBOX_SINGLE_CONSUME','STOP_AFTER_ISSUE') else 0)
        and (mode!='BOOT_INVALIDATES_OLD_TIMER' or s.quarantine==1)
        and (mode!='NO_EVENTS_NO_NEURAL_TICKS' or s.times==[])
        and (mode!='IMMEDIATE_TIMER_MICROSTEP' or s.micro>=1))
    # An intentionally WRONG external-only clock would jump to the next external arrival,
    # skipping d_R=5 before external SENSOR at t=10, i.e. it violates R4.1 C01.
    naive_skip=(mode=='TIMER_BEFORE_EXTERNAL' and s.times[0]==5 or
                mode=='NEW_EARLIER_TIMER' and s.times[:3]==[2,4,10])
    return ok,s,naive_skip

class TimerJitter:
    def __init__(self):self.data=[];self.stop=threading.Event();self.thread=None
    def start(self):
        def f():
            # Real monotonic scheduling, NOT a hard-realtime OS guarantee.
            base=time.monotonic_ns()+10_000_000
            for n in range(18):
                if self.stop.is_set():break
                target=base+n*20_000_000
                remaining=(target-time.monotonic_ns())/1e9
                if remaining>0:self.stop.wait(remaining)
                if self.stop.is_set():break
                self.data.append((time.monotonic_ns()-target)/1e6)
        self.thread=threading.Thread(target=f,daemon=True);self.thread.start()
    def finish(self):
        if self.thread:
            self.thread.join(3)
            if self.thread.is_alive():self.stop.set();self.thread.join(1)
        return list(self.data)

def native_pulse(binary):
    r=subprocess.run([str(binary),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=15)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('NATIVE_F_PULSE_NOT_PASS')
    m=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
    if not m:raise RuntimeError('NATIVE_F_PULSE_MISSING_THROUGHPUT')
    return float(m[1])

def stage(log,ctx,binary,nworker,host,inject):
    label=f'S5x{nworker}_RAM32';expect=len(MODES)*2
    stop=ctx.Event();ready=ctx.Queue();out=ctx.Queue();ram_ready=ctx.Queue()
    workers=[];ram=None;jitter=TimerJitter();start=time.monotonic()
    cases=0;failures=0;negative=0;native_cases=0;workers_good=0;why=None;last_details=[]
    try:
        ram=ctx.Process(target=ramholder,args=(stop,ram_ready));ram.start()
        if ram_ready.get(timeout=10)!=True:raise RuntimeError('RAM_HOLDER_FAIL')
        for i in range(nworker):
            p=ctx.Process(target=s5worker,args=(binary,stop,ready,out));p.start();workers.append(p)
        if len(set(ready.get(timeout=25) for p in workers))!=nworker:raise RuntimeError('BACKGROUND_S5_NOT_ACTIVE')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={label} workers={nworker}')
        log(f'STAGE_BEGIN stage={label} scenarios={expect} background_S5={nworker} held_RAM_MiB=32')
        jitter.start()
        for rep in (1,2):
            for mode in MODES:
                if reason:=guard(host):why=reason;break
                if inject and cases>=3:why='INJECTED_HOST_SAFETY_ABORT';break
                t0=time.monotonic()
                try:
                    ok,s,neg=scenario(mode)
                    # The data/timer paths invoke the existing native S5 operator in an
                    # isolated process. This is NOT the production controller executing F.
                    throughput=native_pulse(binary) if s.neural else None
                    if s.neural:native_cases+=1
                except BaseException as e:
                    if 'SAFETY_' in str(e):why=str(e);break
                    ok=False;s=None;neg=False;throughput=None
                    detail=f'ERROR={type(e).__name__}:{str(e)[:100]}'
                else:
                    detail=(f'events={len(s.traces)} virtual_neural={len(s.neural)} '
                            f'outbox_issues={len(s.issue)} outbox_consumed={s.consumed} '
                            f'quarantined_old_timer={s.quarantine} microsteps={s.micro} '
                            f'last_virtual_ms={s.now} native_F_GMAC_s={throughput} '
                            f'causal_order={"OK" if ok else "FAIL"}')
                cases+=1;negative+=int(neg);failures+=int(not ok)
                status='FAIL' if not ok else 'PASS_C01_NEGATIVE_CONTROL' if neg else 'PASS'
                log(f'CASE stage={label} rep={rep} mode={mode} status={status} {detail} elapsed_ms={(time.monotonic()-t0)*1000:.3f}')
                last_details.append((mode,ok))
            if why:break
        jitter_values=jitter.finish()
        if reason:=guard(host):why=reason
        log(f'CLOCK_JITTER stage={label} samples={len(jitter_values)} '
            f'max_late_ms={round(max(jitter_values),3) if jitter_values else None} '
            f'median_late_ms={round(statistics.median(jitter_values),3) if jitter_values else None} '
            f'min_late_ms={round(min(jitter_values),3) if jitter_values else None} '
            f'NOTE=real_clock_not_hard_realtime')
        if not why and len(jitter_values)!=18:failures+=1
        floor=1 if host else (24 if nworker==2 else 30)
        while not why and time.monotonic()-start<floor:
            if reason:=guard(host):why=reason;break
            time.sleep(0.15)
    except BaseException as e:
        if str(e).startswith('SAFETY_'):why=str(e)
        else:failures+=1;log(f'STAGE_ERROR stage={label} type={type(e).__name__} detail={str(e)[:200]}')
    finally:
        jitter.stop.set();jitter.finish();stop.set()
        for p in workers:
            p.join(5)
            if p.is_alive():p.kill();p.join(3)
        if ram:
            ram.join(4)
            if ram.is_alive():ram.kill();ram.join(2)
        for p in workers:
            try:
                pid,runs,mean,minimum,errors=out.get(timeout=3)
                log(f'S5_WORKER stage={label} pid={pid} runs={runs} mean_GMAC_s={mean} min_GMAC_s={minimum} errors={errors}')
                if runs>0 and not errors:workers_good+=1
                else:failures+=1
            except queue.Empty:failures+=1;log(f'S5_WORKER stage={label} RESULT_MISSING')
        for q in (ready,out,ram_ready):q.cancel_join_thread();q.close()
    status='SAFETY_ABORT' if why else ('COMPLETE' if cases==expect and failures==0 and negative==4
                                and workers_good==nworker else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={label} status={status} cases={cases}/{expect} failures={failures} '
        f'c01_naive_skip_negative_findings={negative} native_F_case_invocations={native_cases} '
        f'background_workers_ok={workers_good}/{nworker} safety_reason={why or "-"}')
    log(f'STAGE_TELEMETRY stage={label} {telemetry()}')
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
    report=downloads/f'UNO_A52_R41_CAUSAL_CLOCK_TIMER_V19_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- CAUSAL CLOCK, DUE TIMERS, PRIORITY CONTROL & ONE-SHOT OUTBOX UNDER NATIVE S5 LOAD '+VERSION)
            log('R4.1 S2/S3/C01: virtual monotonic causal event scheduler, due timers, simultaneous control priority and one-shot outbox; real monotonic Android timer jitter measured separately.')
            log('Synthetic controller and request issuance, NOT OS action/owner authentication/Android Binder, physical STOP, hard deadline, model training, production runtime.')
            log('Actual native ARM S5 F invoked in neural-event cases while 2/4 additional S5 processes run continuously plus 32MiB RAM. No idle load stage.')
            log('Battery charger allowed but 40% battery, 37.5C battery temperature and 400000kB free memory guards unchanged.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            log(f'PRECHECK {telemetry()}')
            if reason:=guard(a.host_smoke):log('RESULT SAFETY_SKIP '+reason);return 3
            binary=native_binary(a.host_smoke,a.native_binary);log('VERIFIED_NATIVE_S5 '+str(binary))
            ctx=mp.get_context('fork')
            first=stage(log,ctx,binary,1 if a.host_smoke else 2,a.host_smoke,a.inject_host_abort)
            if first[0]!='COMPLETE':log(f'RESULT {first[0]} partial_cases={first[1]}');return 3
            second=stage(log,ctx,binary,2 if a.host_smoke else 4,a.host_smoke,False)
            if second[0]!='COMPLETE':log(f'RESULT {second[0]} partial_cases={first[1]+second[1]}');return 3
            log(f'RESULT COMPLETE_CAUSAL_CLOCK_TIMER_LAB cases={first[1]+second[1]} '
                f'naive_timer_skip_negatives={first[2]+second[2]} stages=2/2')
            log('LIMIT: virtual event schedule is deterministic fixture; real timer jitter measurements have no guaranteed bound. Synthetic issued request is NOT OS effect.')
            return 0
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:240]}')
            log('TRACE '+traceback.format_exc()[-1500:]);return 2
        finally:log('REPORT '+str(report))
if __name__=='__main__':sys.exit(main())
