#!/usr/bin/env python3
"""UNO R4.1 V7 precode lab: typed IPC event backpressure under native S5 load.
Synthetic event queues, NOT a secure Android boundary, DSP/ASR, or a real neural implementation.
OWNER_APPROVED_PRECODE=FALSE. No OS dispatch, root, privilege elevation or network.
"""
from __future__ import annotations
import argparse, datetime, json, math, multiprocessing as mp, os, queue, re
import sqlite3, statistics, subprocess, sys, time, traceback
from pathlib import Path

VERSION='UNO_R41_A52_NATIVE_S5_EVENT_BACKPRESSURE_STRESS_V7'
MiB=1048576; CAP=65536; QUEUE_LIMIT=24; SENSOR_SLOTS=16; PCM_LIMIT=8
KINDS={'SENSOR','PCM','SCREEN','TASK','BARRIER'}

def read_int(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try: avail=next(int(s.split()[1]) for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    except (OSError,ValueError,StopIteration,IndexError):avail=None
    return read_int('/sys/class/power_supply/battery/capacity'),read_int('/sys/class/power_supply/battery/temp'),avail

def safety(quick):
    if quick:return None
    battery,temp,avail=telemetry()
    if None in (battery,temp,avail) or not 100<=temp<=800:return 'TELEMETRY_UNAVAILABLE'
    if battery<40:return 'LOW_BATTERY'
    if temp>=375:return 'BATTERY_TEMP_AT_LEAST_37_5C'
    if avail<400000:return 'LOW_MEMAVAILABLE'
    return None

def strict_pairs(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:raise ValueError('DUPLICATE_JSON_KEY')
        obj[k]=v
    return obj

def bad_constant(_):raise ValueError('NONFINITE_JSON')

def decode(raw):
    if not isinstance(raw,bytes) or len(raw)>CAP or len(raw)<2:raise ValueError('ENVELOPE_SIZE')
    obj=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=strict_pairs,parse_constant=bad_constant)
    if not isinstance(obj,dict) or set(obj)!={'v','kind','seq','data'}:raise ValueError('ENVELOPE_FIELDS')
    if type(obj['v']) is not int or obj['v']!=1:raise ValueError('VERSION')
    if obj['kind'] not in KINDS:raise ValueError('KIND_OR_CONTROL_IN_DATA')
    if type(obj['seq']) is not int or not 0<=obj['seq']<2**63:raise ValueError('SEQUENCE')
    data=obj['data']
    if not isinstance(data,dict):raise ValueError('PAYLOAD_NOT_OBJECT')
    kind=obj['kind']
    if kind=='SENSOR':
        if set(data)!={'channel','generation','value','missing','source','sample_ns'}:raise ValueError('SENSOR_FIELDS')
        if data['channel'] not in ('battery','temp','cpu6','memavailable','status','voltage'):raise ValueError('CHANNEL')
        if data['source']!='SYSFS_PROC_UNTRUSTED':raise ValueError('SOURCE')
        if type(data['generation']) is not int or not 0<=data['generation']<=1000000:raise ValueError('GENERATION')
        if type(data['sample_ns']) is not int or data['sample_ns']<0:raise ValueError('SAMPLE_TIME')
        if type(data['missing']) is not bool:raise ValueError('MISSING_FLAG')
        v=data['value']
        if data['missing'] and v is not None:raise ValueError('FABRICATED_PRESENT_VALUE')
        if not data['missing'] and (type(v) not in (int,float) or not math.isfinite(v)):raise ValueError('INVALID_READING')
    elif kind=='PCM':
        if set(data)!={'turn','frame','samples'} or not isinstance(data['turn'],str) or not 1<=len(data['turn'])<=24:raise ValueError('PCM_FIELDS')
        if type(data['frame']) is not int or not 0<=data['frame']<=10000 or data['samples']!=160:raise ValueError('PCM_FRAME')
    elif kind=='SCREEN':
        if set(data)!={'frame','sample_ns'} or type(data['frame']) is not int or type(data['sample_ns']) is not int:return_bad('SCREEN_FIELDS')
    elif kind=='TASK':
        if set(data)!={'ticket'} or not isinstance(data['ticket'],str) or not 1<=len(data['ticket'])<=64:raise ValueError('TASK_FIELDS')
    elif kind=='BARRIER':
        if set(data)!={'nonce'} or not isinstance(data['nonce'],str) or len(data['nonce'])>64:raise ValueError('BARRIER_FIELDS')
    return obj

def return_bad(s):raise ValueError(s)

def packet(kind,seq,data):return json.dumps({'v':1,'kind':kind,'seq':seq,'data':data},separators=(',',':'),allow_nan=False).encode()

def sqlite_open(path):
    c=sqlite3.connect(str(path),timeout=5,isolation_level=None)
    c.execute('PRAGMA synchronous=FULL');c.execute('PRAGMA busy_timeout=5000')
    return c

def start_state(path):
    c=sqlite_open(path)
    try:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),stopped INTEGER NOT NULL,epoch INTEGER NOT NULL)')
        c.execute('INSERT INTO state VALUES(1,0,1)')
    finally:c.close()

def check_stopped(path):
    c=sqlite_open(path)
    try:return c.execute('SELECT stopped,epoch FROM state WHERE id=1').fetchone(),c.execute('PRAGMA integrity_check').fetchone()[0]
    finally:c.close()

def controller(dataq,ctrl,barrierq,dbpath):
    st={'processed':0,'invalid':0,'after_stop_discarded':0,'sensor_slots':0,'sensor_coalesced':0,
        'pcm_incomplete':0,'screen_stale':0,'tasks_admitted':0,'tasks_terminal':0,
        'stop':0,'os_dispatch':0,'p_steps':0}
    sensors={};pcm={};tasks={};stopped=False
    c=sqlite_open(dbpath)
    try:
        ctrl.send(('READY',os.getpid()))
        while True:
            now=time.monotonic_ns()
            if ctrl.poll():
                cmd=ctrl.recv()
                if cmd=='QUIT':return
                if cmd=='STATS':
                    st['sensor_slots']=len(sensors)
                    ctrl.send(('STATS',dict(st),{k:v['seq'] for k,v in sensors.items()}))
                if cmd=='STOP':
                    receive_ns=time.monotonic_ns()
                    c.execute('BEGIN IMMEDIATE')
                    c.execute('UPDATE state SET stopped=1,epoch=epoch+1 WHERE id=1')
                    c.execute('COMMIT')
                    stopped=True;st['stop']=1
                    for k,v in tasks.items():
                        if isinstance(v,int):tasks[k]='CANCELLED';st['tasks_terminal']+=1
                    ctrl.send(('STOP_ACK',receive_ns,time.monotonic_ns(),st['tasks_admitted'],st['tasks_terminal']))
            for ticket,v in list(tasks.items()):
                if isinstance(v,int) and now>=v:
                    tasks[ticket]='COMPLETED';st['tasks_terminal']+=1
            try:raw=dataq.get(timeout=.003)
            except queue.Empty:continue
            st['processed']+=1
            if stopped:
                st['after_stop_discarded']+=1
                continue
            try:o=decode(raw)
            except (ValueError,TypeError,UnicodeError,json.JSONDecodeError):
                st['invalid']+=1;continue
            k=o['kind'];d=o['data']
            if k=='SENSOR':
                key=(d['channel'],d['generation'])
                if key not in sensors and len(sensors)>=SENSOR_SLOTS:
                    st['invalid']+=1;continue
                prev=sensors.get(key)
                if prev is not None:
                    if o['seq']<=prev['seq']:st['invalid']+=1;continue
                    st['sensor_coalesced']+=1
                sensors[key]={'seq':o['seq'],'missing':d['missing'],'value':d['value']}
                st['sensor_slots']=len(sensors)
            elif k=='PCM':
                tid=d['turn'];obj=pcm.setdefault(tid,{'last':-1,'count':0,'incomplete':False})
                if d['frame']!=obj['last']+1:obj['incomplete']=True
                obj['last']=d['frame'];obj['count']+=1
                if obj['count']>PCM_LIMIT:obj['incomplete']=True
                st['pcm_incomplete']=sum(int(p['incomplete']) for p in pcm.values())
            elif k=='SCREEN':
                if now-d['sample_ns']>50_000_000:st['screen_stale']+=1
            elif k=='TASK':
                ticket=d['ticket']
                if ticket in tasks:st['invalid']+=1
                elif len(tasks)>=256:st['invalid']+=1
                else:
                    tasks[ticket]=now+90_000_000;st['tasks_admitted']+=1
            elif k=='BARRIER':
                barrierq.put((d['nonce'],dict(st)),timeout=2)
            time.sleep(.0004)
    finally:
        if c.in_transaction:c.execute('ROLLBACK')
        c.close();ctrl.close()

def worker(binary,stop,out):
    rates=[];errs=[]
    while not stop.is_set():
        try:
            run=subprocess.run([binary,'rank','full','0.70'],capture_output=True,text=True,timeout=5)
            if run.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',run.stdout):errs.append('S5_CONTRACT_FAILURE');break
            mat=re.search(r'estimated_F_GMAC_s=([0-9.]+)',run.stdout)
            if not mat:errs.append('MISSING_GMAC');break
            rates.append(float(mat.group(1)))
        except BaseException as ex:errs.append(type(ex).__name__);break
    try:out.put((os.getpid(),len(rates),min(rates) if rates else None,statistics.mean(rates) if rates else None,errs),timeout=2)
    except BaseException:pass

def memory_holder(mib,stop,ready):
    try:
        buf=bytearray(mib*MiB)
        for i in range(0,len(buf),4096):buf[i]=1
        ready.put(('READY',os.getpid()),timeout=3)
        while not stop.wait(.2):
            for i in range(0,len(buf),262144):buf[i]^=1
    except BaseException as exc:
        try:ready.put(('ERROR',str(exc)[:80]),timeout=1)
        except BaseException:pass

def native_binary(override):
    b=Path(override) if override else Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not b.is_file() or not os.access(b,os.X_OK):raise RuntimeError('MISSING_S5_BINARY')
    r=subprocess.run([str(b),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=5)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):raise RuntimeError('S5_SELFTEST_FAIL')
    return str(b)

def probe_sensors():
    paths={'battery':'/sys/class/power_supply/battery/capacity',
       'temp':'/sys/class/power_supply/battery/temp',
       'cpu6':'/sys/devices/system/cpu/cpu6/cpufreq/scaling_cur_freq',
       'voltage':'/sys/class/power_supply/battery/voltage_now'}
    readings={k:read_int(p) for k,p in paths.items()}
    _,_,avail=telemetry();readings['memavailable']=avail
    # Encode an actually readable categorical charge-status as a lab-only enum.
    try: status_text=Path('/sys/class/power_supply/battery/status').read_text().strip()
    except OSError: status_text=''
    readings['status']={'Charging':1,'Full':2,'Not charging':0,'Discharging':-1}.get(status_text)
    return readings

def begin_broker(ctx,root):
    root.mkdir(parents=True,exist_ok=False,mode=0o700)
    db=root/'control.sqlite3';start_state(db)
    q=ctx.Queue(maxsize=QUEUE_LIMIT)
    par,child=ctx.Pipe(duplex=True);bar=ctx.Queue()
    proc=ctx.Process(target=controller,args=(q,child,bar,db));proc.start();child.close()
    if not par.poll(8):raise TimeoutError('BROKER_READY_TIMEOUT')
    if par.recv()[0]!='READY':raise RuntimeError('BROKER_READY_FAIL')
    return proc,q,par,bar,db

def close_broker(proc,q,ctrl,bar):
    if proc.is_alive():
        try:ctrl.send('QUIT')
        except BaseException:pass
    proc.join(2)
    if proc.is_alive():proc.kill();proc.join(2)
    ctrl.close();q.cancel_join_thread();q.close();bar.cancel_join_thread();bar.close()

def enqueue(q,raw,block=True):
    if block:q.put(raw,timeout=3);return True
    try:q.put_nowait(raw);return True
    except queue.Full:return False

def barrier(q,bar,n):
    enqueue(q,packet('BARRIER',n,{'nonce':str(n)}))
    target=str(n)
    until=time.monotonic()+6
    while time.monotonic()<until:
        try:uid,stats=bar.get(timeout=max(.05,until-time.monotonic()))
        except queue.Empty:break
        if uid==target:return stats
    raise TimeoutError('BARRIER_TIMEOUT')

def stop_and_stats(ctrl,db):
    sent_ns=time.monotonic_ns();ctrl.send('STOP')
    if not ctrl.poll(5):raise TimeoutError('STOP_ACK_TIMEOUT')
    ret=ctrl.recv();done_ns=time.monotonic_ns()
    if ret[0]!='STOP_ACK':raise RuntimeError('EXPECTED_STOP_ACK')
    ctrl.send('STATS')
    if not ctrl.poll(5):raise TimeoutError('STATS_TIMEOUT')
    st=ctrl.recv()
    if st[0]!='STATS':raise RuntimeError('STATS_INVALID')
    state,integrity=check_stopped(db)
    return {'ack_ms':(done_ns-sent_ns)/1e6,'receive_ms':(ret[1]-sent_ns)/1e6,
            'latch_ms':(ret[2]-sent_ns)/1e6,'state':state,'integrity':integrity,
            'stats':st[1],'sensor_seq':st[2]}

def exercise(ctx,root,mode,seqstart):
    proc,q,ctrl,bar,db=begin_broker(ctx,root)
    try:
        begin=time.monotonic_ns();seq=seqstart;dropped=0;readings=probe_sensors()
        def mk(kind,fields):
            nonlocal seq
            seq+=1;return packet(kind,seq,fields)
        if mode=='REAL_SENSOR_PCM_OVERFLOW':
            for ch,val in readings.items():
                enqueue(q,mk('SENSOR',{'channel':ch,'generation':1,'value':val,
                  'missing':val is None,'source':'SYSFS_PROC_UNTRUSTED','sample_ns':time.monotonic_ns()}))
            for i in range(12):
                cpu_val=read_int('/sys/devices/system/cpu/cpu6/cpufreq/scaling_cur_freq')
                enqueue(q,mk('SENSOR',{'channel':'cpu6','generation':1,'value':cpu_val,
                    'missing':cpu_val is None,'source':'SYSFS_PROC_UNTRUSTED','sample_ns':time.monotonic_ns()}))
            for i in range(20):enqueue(q,mk('PCM',{'turn':'synthetic-turn','frame':i,'samples':160}))
            enqueue(q,mk('SCREEN',{'frame':1,'sample_ns':time.monotonic_ns()-200_000_000}))
            enqueue(q,mk('SCREEN',{'frame':2,'sample_ns':time.monotonic_ns()}))
            for i in range(10):enqueue(q,mk('TASK',{'ticket':f'T{i}'}))
            mid=barrier(q,bar,seq+1)
            stopped=stop_and_stats(ctrl,db)
            valid=(mid['sensor_slots']>=5 and mid['sensor_coalesced']>=10 and mid['pcm_incomplete']>=1
                   and mid['screen_stale']>=1 and mid['tasks_admitted']==10 and
                   stopped['stats']['tasks_admitted']==stopped['stats']['tasks_terminal'])
        elif mode=='INVALID_ENVELOPES':
            examples=[b'{}',b'{"v":1,"v":1,"kind":"TASK","seq":2,"data":{"ticket":"x"}}',
             b'{"v":1,"kind":"CONTROL","seq":3,"data":{"STOP":true}}',b'\xff',
             b'{"v":1,"kind":"SENSOR","seq":1,"data":{"channel":"battery","generation":1,"value":NaN,"missing":false,"source":"SYSFS_PROC_UNTRUSTED","sample_ns":5}}',
             b'X'*(CAP+1),mk('SENSOR',{'channel':'battery','generation':1,'value':0,'missing':True,
               'source':'SYSFS_PROC_UNTRUSTED','sample_ns':1}),
             mk('TASK',{'ticket':''}),mk('PCM',{'turn':'a','frame':-1,'samples':160}),
             mk('SCREEN',{'frame':1,'sample_ns':'invalid'})]
            for raw in examples:enqueue(q,raw)
            mid=barrier(q,bar,seq+1)
            stopped=stop_and_stats(ctrl,db)
            valid=(mid['invalid']==len(examples) and mid['tasks_admitted']==0 and stopped['stats']['os_dispatch']==0)
        elif mode=='CONTROL_PRIORITY_SATURATED':
            for i in range(8):enqueue(q,mk('TASK',{'ticket':f'PRIOR{i}'}))
            barrier(q,bar,seq+1)
            for i in range(1200):
                if not enqueue(q,mk('SENSOR',{'channel':'cpu6','generation':1,'value':652800,
                      'missing':False,'source':'SYSFS_PROC_UNTRUSTED','sample_ns':time.monotonic_ns()}),False):dropped+=1
            stopped=stop_and_stats(ctrl,db)
            before=stopped['stats']['tasks_admitted']
            for i in range(6):enqueue(q,mk('TASK',{'ticket':f'AFTER{i}'}))
            time.sleep(.10)
            ctrl.send('STATS')
            if not ctrl.poll(4):raise TimeoutError('POST_STOP_STATS')
            post=ctrl.recv()
            if post[0]!='STATS':raise RuntimeError('POST_STOP_BAD_REPLY')
            valid=(dropped>0 and stopped['stats']['tasks_admitted']==stopped['stats']['tasks_terminal']
                    and before==post[1]['tasks_admitted'] and stopped['stats']['os_dispatch']==0)
            mid=post[1]
        else:raise ValueError('UNKNOWN_MODE')
        dur=(time.monotonic_ns()-begin)/1e6
        valid=bool(valid and stopped['state'][0]==1 and stopped['integrity']=='ok' and
                  stopped['stats']['os_dispatch']==0 and stopped['stats']['p_steps']==0)
        return {'mode':mode,'status':'PASS' if valid else 'FAIL','elapsed_ms':dur,
           'real_readable':sum(v is not None for v in readings.values()),
           'ack_ms':stopped['ack_ms'],'latch_ms':stopped['latch_ms'],
           'dropped':dropped,'mid':mid,'final':stopped['stats'],'db':db,'proc':proc}
    finally:close_broker(proc,q,ctrl,bar)

def run_stage(ctx,root,log,quick,name,n,ram,duration,repeat,binary):
    event=ctx.Event();results=ctx.Queue();ready=ctx.Queue();workers=[];holder=None;errors=0;cases=[]
    begin=time.monotonic()
    try:
        holder=ctx.Process(target=memory_holder,args=(ram,event,ready));holder.start()
        status=ready.get(timeout=7)
        if status[0]!='READY':raise RuntimeError('MEMORY_HOLDER_FAIL '+str(status))
        for _ in range(n):
            w=ctx.Process(target=worker,args=(binary,event,results));w.start();workers.append(w)
        log(f'STAGE_BEGIN name={name} native_S5_workers={n} touched_RAM_MiB={ram} duration_floor_s={duration}')
        for rep in range(1,repeat+1):
            for mode in ('REAL_SENSOR_PCM_OVERFLOW','INVALID_ENVELOPES','CONTROL_PRIORITY_SATURATED'):
                issue=safety(quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                try:
                    out=exercise(ctx,root/f'{name}_{rep}_{mode}',mode,rep*100000)
                    # After a confirmed STOP, kill the controller and independently read its durable latch.
                    state,integrity=check_stopped(out['db'])
                    if state[0]!=1 or integrity!='ok':out['status']='FAIL'
                    cases.append(out)
                    if out['status']!='PASS':errors+=1
                    x=out['final'];y=out['mid']
                    log(f"CASE stage={name} rep={rep} mode={mode} status={out['status']} "
                        f"ack_ms={out['ack_ms']:.3f} latch_ms={out['latch_ms']:.3f} "
                        f"dropped_data={out['dropped']} real_sensor_fields={out['real_readable']}/6 invalid={x['invalid']} "
                        f"sensor_coalesced={x['sensor_coalesced']} pcm_incomplete={x['pcm_incomplete']} "
                        f"screen_stale={x['screen_stale']} tasks={x['tasks_admitted']}/{x['tasks_terminal']} "
                        f"after_stop_discarded={x['after_stop_discarded']} elapsed_ms={out['elapsed_ms']:.3f} "
                        f"crash_readback_stop={state[0]} sqlite_integrity={integrity}")
                except BaseException as ex:
                    errors+=1
                    log(f'CASE stage={name} rep={rep} mode={mode} status=ERROR exception={type(ex).__name__}:{str(ex)[:130]}')
        while time.monotonic()<begin+duration:
            issue=safety(quick)
            if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
            time.sleep(.15)
    finally:
        event.set()
        for w in workers:
            w.join(4)
            if w.is_alive():w.kill();w.join(2)
        if holder:
            holder.join(2)
            if holder.is_alive():holder.kill();holder.join(2)
        for _ in workers:
            try:
                pid,runs,minimum,mean,problems=results.get(timeout=2)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={runs} min_GMAC_s={minimum} mean_GMAC_s={mean} errors={problems}')
                if runs==0 or problems:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={name} error=MISSING_RESULT')
        results.cancel_join_thread();results.close();ready.cancel_join_thread();ready.close()
    ack=[x['ack_ms'] for x in cases]
    log(f'STAGE_SUMMARY stage={name} cases={len(cases)} expected={3*repeat} failures={errors} '
        f'ack_max_ms={max(ack) if ack else None} real_sensor_probes={sum(x["mode"]=="REAL_SENSOR_PCM_OVERFLOW" for x in cases)}')
    return errors==0 and len(cases)==3*repeat,len(cases)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--quick',action='store_true',help='local smoke test only; NOT phone evidence')
    p.add_argument('--binary',help='S5 path override for local smoke test')
    args=p.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_NATIVE_EVENT_BACKPRESSURE_STRESS_V7_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- TYPED IPC / REAL SENSOR / PCM BACKPRESSURE UNDER NATIVE S5 LOAD '+VERSION)
            log('Separate priority STOP pipe versus bounded 24-item data queue. Synthetic PCM/SCREEN/TASK; SENSOR reads real A52 sysfs/proc.')
            log('STOP ack, post-STOP admission, missing-mask, canonical envelope parser, stale screen and incomplete PCM are checked under load.')
            log('All stages run native ARM C256R32 FP32 S5, with 2/4 worker processes plus 32/64 MiB RAM.')
            log('LIMIT: synthetic IPC queue, NOT Android Binder, real microphone/display, trained model, real owner consent or true OS STOP.')
            log('LIMIT: queue already receives Python bytes before envelope-size check; NOT a proof of allocation-before-parse protection.')
            log('No OS dispatch, root, USB, ADB, APK, network, permissions or production changes. OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            issue=safety(args.quick)
            if issue:log('RESULT SAFETY_SKIP '+issue);return 3
            binary=native_binary(args.binary);log('VERIFIED_NATIVE_S5 '+binary)
            ctx=mp.get_context('fork');root=home/'uno_a52_r41_native_event_backpressure_stress_v7'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            plans=[('S5x2_RAM32',2,32,7,1),('S5x4_RAM64',4,64,8,1)] if args.quick else [
                ('S5x2_RAM32',2,32,24,2),('S5x4_RAM64',4,64,30,2)]
            done=0;all_good=True
            for name,n,ram,duration,repeats in plans:
                issue=safety(args.quick)
                if issue:raise RuntimeError('SAFETY_ABORT_'+issue)
                okay,count=run_stage(ctx,root,log,args.quick,name,n,ram,duration,repeats,binary)
                all_good=all_good and okay;done+=count
                b,t,m=telemetry();log(f'STAGE_TELEMETRY name={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
                if not okay:break
            log(f'RESULT {"PASS_BOUNDED_IPC_BACKPRESSURE_LAB" if all_good else "FAIL_OR_INCOMPLETE"} cases={done}')
            log('OPEN: real Binder/Android callbacks, OS capability separation, PCM VAD/CTC, device UX, hard real-time STOP, OS action readback.')
            log('REPORT '+str(report))
            return 0 if all_good else 2
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPT');log('REPORT '+str(report));return 130
        except BaseException as ex:
            log('RESULT ERROR '+type(ex).__name__+': '+str(ex)[:190]);log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
