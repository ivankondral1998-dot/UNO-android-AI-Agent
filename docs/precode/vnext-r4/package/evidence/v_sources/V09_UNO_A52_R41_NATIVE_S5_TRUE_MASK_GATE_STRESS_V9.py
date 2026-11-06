#!/usr/bin/env python3
"""UNO R4.1 PRECODE V9: true pre-compute S5 masks vs post-compute discards.

Runs only under bounded native ARM S5 load on the user's A52; builds a separate
synthetic C256R32 K=8 gating fixture with clang. No production agent code.
OWNER_APPROVED_PRECODE=FALSE.
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
import statistics
import subprocess
import sys
import time
import traceback

V='UNO_R41_A52_S5_TRUE_PRECOMPUTE_MASK_GATE_STRESS_V9'
MIB=1048576
C_SOURCE=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#define D 256
#define B 32
#define U 128
#define R 32
#define NB 8
#define K 8
static float A2[NB][R][D],A1[NB][U][R],C2[NB][R][D],C1[NB][U][R],BB[NB][B][U];
static uint32_t rng=0x19acf57bu;
static volatile double late_sink=0, result_sink=0;
static uint32_t rand32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static float small(void){return ((float)(rand32()%20001)/10000.0f-1.0f)*.008f;}
static double seconds(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static void init(void){
 for(int j=0;j<NB;j++){
  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A2[j][r][i]=small();C2[j][r][i]=small();}
  for(int u=0;u<U;u++)for(int r=0;r<R;r++){A1[j][u][r]=small();C1[j][u][r]=small();}
  for(int b=0;b<B;b++)for(int u=0;u<U;u++)BB[j][b][u]=small();
 }
}
static void init_hz(float h[D],float z[D]){
 for(int i=0;i<D;i++){h[i]=.02f*(float)((i%17)-8);z[i]=.015f*(float)((i%11)-5);}
}
// mode 0 FULL: calculate and write all eight branches.
// mode 1 EARLY: skip the six inactive branches BEFORE any matrix products.
// mode 2 LATE: calculate all eight; throw away six already computed branches.
static void step(float h[D],const float z[D],int mode){
 float next[D],at[R],ct[R],u[U],v[U],rhs[B];
 memcpy(next,h,sizeof(float)*D);
 for(int j=0;j<NB;j++){
  if(mode==1 && j>=2)continue; // actual precompute gate
  for(int r=0;r<R;r++){
   float aa=0,cc=0;
   for(int i=0;i<D;i++){aa+=A2[j][r][i]*h[i];cc+=C2[j][r][i]*z[i];}
   at[r]=aa;ct[r]=cc;
  }
  for(int x=0;x<U;x++){
   float aa=0,cc=0;
   for(int r=0;r<R;r++){aa+=A1[j][x][r]*at[r];cc+=C1[j][x][r]*ct[r];}
   u[x]=tanhf(aa+cc);
  }
  for(int b=0;b<B;b++){
   float s=0;for(int x=0;x<U;x++)s+=BB[j][b][x]*u[x];
   rhs[b]=tanhf(s);
  }
  if(mode==2 && j>=2){late_sink+=(double)rhs[(j+3)%B];continue;}
  for(int b=0;b<B;b++)next[j*B+b]=.5f*h[j*B+b]+.5f*rhs[b];
 }
 memcpy(h,next,sizeof(float)*D);
}
static void event(float h[D],const float z[D],int mode){for(int k=0;k<K;k++)step(h,z,mode);}
static int selftest(void){
 float early[D],late[D],original[D],z[D];init_hz(original,z);
 memcpy(early,original,sizeof(early));memcpy(late,original,sizeof(late));
 event(early,z,1);event(late,z,2);
 int same=memcmp(early,late,sizeof(early))==0,unchanged=1;
 for(int i=64;i<D;i++)if(early[i]!=original[i])unchanged=0;
 printf("FIXED_K_VERIFY K=%d masked_early_equals_late=%s inactive_unchanged=%s status=%s\n",K,same?"YES":"NO",unchanged?"YES":"NO",(same&&unchanged)?"PASS":"FAIL");
 return same&&unchanged;
}
int main(int argc,char**argv){
 if(argc!=3){fputs("usage: binary full|early|late seconds\n",stderr);return 2;}
 int mode=!strcmp(argv[1],"full")?0:(!strcmp(argv[1],"early")?1:(!strcmp(argv[1],"late")?2:-1));
 double duration=atof(argv[2]);if(mode<0||duration<.30||duration>2.00)return 2;
 init();if(!selftest())return 3;
 // Per branch: two rank products A and C, one B projection; K is FIXED.
 const unsigned long long macperbranch=2ull*(R*D+U*R)+(unsigned long long)B*U;
 const int computed=mode==1?2:8, updated=mode==0?8:2;
 const unsigned long long mac=(unsigned long long)computed*macperbranch*K;
 printf("LEDGER mode=%s K=%d active_blocks=%d computed_blocks=%d event_F_MAC=%llu\n",argv[1],K,updated,computed,mac);
 float h[D],z[D],orig[D];init_hz(orig,z);
 double t0=seconds(),elapsed=0,checksum=0;unsigned long long n=0;
 do{
  memcpy(h,orig,sizeof(h));h[n%D]+=1e-5f;
  event(h,z,mode);checksum+=h[(n*17ull)%D];n++;
  elapsed=seconds()-t0;
 }while(elapsed<duration&&n<3000000ull);
 result_sink=checksum;
 printf("MEASURE mode=%s events=%llu elapsed_s=%.4f avg_ms_per_event=%.6f F_GMAC_s=%.5f checksum=%.8f\n",argv[1],n,elapsed,1000*elapsed/n,(double)mac*n/elapsed/1e9,checksum);
 return 0;
}
'''

def nint(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telem():
    try:
        line=next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
        m=int(line.split()[1])
    except (OSError,ValueError,StopIteration,IndexError):m=None
    return nint('/sys/class/power_supply/battery/capacity'),nint('/sys/class/power_supply/battery/temp'),m

def safety(quick):
    if quick:return None
    b,t,m=telem()
    if None in (b,t,m) or not 100<=t<=800:return 'TELEMETRY_UNAVAILABLE'
    if b<40:return 'BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'BATTERY_TEMP_AT_LEAST_37_5C'
    if m<400000:return 'AVAILABLE_RAM_BELOW_400000_KB'
    return None

class SafetyAbort(RuntimeError):pass

def compile_fixture(root):
    clang=shutil.which('clang')
    if not clang:raise RuntimeError('CLANG_NOT_INSTALLED')
    src=root/'true_mask_gate.c';exe=root/'true_mask_gate'
    src.write_text(C_SOURCE,encoding='utf-8')
    p=subprocess.run([clang,'-O3','-std=c11','-Wall','-Wextra',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError('C_COMPILE_FAIL '+p.stderr[-250:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def verify_background_binary():
    exe=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not exe.is_file() or not os.access(exe,os.X_OK):raise RuntimeError('BACKGROUND_S5_MISSING')
    p=subprocess.run([str(exe),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=8)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BACKGROUND_S5_SELFCHECK_FAILED')
    return exe

def background_worker(exe,cancel,out,ready):
    rates=[];errors=[]
    while not cancel.is_set():
        try:
            p=subprocess.run([str(exe),'rank','full','0.70'],capture_output=True,text=True,timeout=7)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):
                errors.append('CONTRACT_FAIL');break
            m=re.search(r'estimated_F_GMAC_s=([0-9.]+)',p.stdout)
            if not m:errors.append('GMAC_MISSING');break
            rates.append(float(m.group(1)))
            if len(rates)==1:ready.put(('ACTIVE',os.getpid()),timeout=3)
        except BaseException as e:errors.append(type(e).__name__);break
    try:out.put((os.getpid(),len(rates),min(rates) if rates else None,statistics.mean(rates) if rates else None,errors),timeout=2)
    except BaseException:pass

def ram_holder(mib,cancel,ready):
    try:
        data=bytearray(mib*MIB)
        for i in range(0,len(data),4096):data[i]=1
        ready.put(('READY',os.getpid()),timeout=3)
        while not cancel.wait(.14):
            for i in range(0,len(data),262144):data[i]^=1
    except BaseException as e:
        try:ready.put(('ERROR',str(e)[:90]),timeout=2)
        except BaseException:pass

def sample(exe,mode,seconds):
    p=subprocess.run([str(exe),mode,f'{seconds:.2f}'],capture_output=True,text=True,timeout=seconds+10)
    if p.returncode:raise RuntimeError('MASK_BINARY_EXIT '+str(p.returncode)+' '+p.stderr[-150:])
    if not re.search(r'FIXED_K_VERIFY[^\n]*status=PASS',p.stdout):raise RuntimeError('MASK_VERIFY_FAILED')
    ledger=re.search(r'LEDGER mode=(\w+) K=(\d+) active_blocks=(\d+) computed_blocks=(\d+) event_F_MAC=(\d+)',p.stdout)
    metric=re.search(r'MEASURE mode=(\w+) events=(\d+) elapsed_s=([0-9.]+) avg_ms_per_event=([0-9.]+) F_GMAC_s=([0-9.]+)',p.stdout)
    if not ledger or not metric or ledger[1]!=mode or metric[1]!=mode:raise RuntimeError('NATIVE_OUTPUT_PARSE_ERROR')
    mac=int(ledger[5]);comp=int(ledger[4]);active=int(ledger[3]);K=int(ledger[2]);
    expected=1835008 if mode!='early' else 458752
    if K!=8 or mac!=expected or comp!=(2 if mode=='early' else 8) or active!=(8 if mode=='full' else 2):
        raise RuntimeError('LEDGER_OR_MASK_MISMATCH')
    return {'mode':mode,'event_mac':mac,'events':int(metric[2]),'elapsed_s':float(metric[3]),'ms':float(metric[4]),'gmac':float(metric[5])}

def summarize(log,name,samples,failures,safety_reason,workers_ok):
    grouped={mode:[v['ms'] for v in samples if v['mode']==mode] for mode in ('early','late','full')}
    med={mode:(statistics.median(vals) if vals else None) for mode,vals in grouped.items()}
    ratio=med['late']/med['early'] if med['late'] and med['early'] else None
    ratio_full=med['full']/med['early'] if med['full'] and med['early'] else None
    incomplete=bool(safety_reason or failures or not workers_ok or any(len(v)<3 for v in grouped.values()))
    status='INCOMPLETE_SAFETY_ABORT' if safety_reason else ('FAIL' if incomplete else 'COMPLETE')
    log(f'STAGE_SUMMARY stage={name} status={status} measurements={len(samples)}/9 failures={failures} '
        f'early_median_ms={med["early"]} late_median_ms={med["late"]} full_median_ms={med["full"]} '
        f'late_over_early_time_ratio={ratio} full_over_early_time_ratio={ratio_full} '
        f'MAC_ratio_late_over_early=4.0 safety_reason={safety_reason or "-"}')
    return status=='COMPLETE',ratio

def run_stage(ctx,root,log,quick,name,count,mem_mib,min_duration,fixture,background):
    cancel=ctx.Event();out=ctx.Queue();ready=ctx.Queue();hold_ready=ctx.Queue()
    processes=[];holder=None;samples=[];errors=0;reason=None;since=time.monotonic()
    try:
        holder=ctx.Process(target=ram_holder,args=(mem_mib,cancel,hold_ready));holder.start()
        msg=hold_ready.get(timeout=8)
        if msg[0]!='READY':raise RuntimeError('RAM_HOLDER_NOT_READY '+str(msg))
        for _ in range(count):
            p=ctx.Process(target=background_worker,args=(background,cancel,out,ready));p.start();processes.append(p)
        confirmed=set();end=time.monotonic()+25
        while len(confirmed)<count:
            if time.monotonic()>end:raise TimeoutError('BACKGROUND_S5_NOT_ACTIVE')
            try:msg=ready.get(timeout=max(.1,end-time.monotonic()))
            except queue.Empty:raise TimeoutError('BACKGROUND_S5_NOT_ACTIVE')
            if msg[0]=='ACTIVE':confirmed.add(msg[1])
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={name} workers={len(confirmed)}')
        log(f'STAGE_BEGIN name={name} native_s5_workers={count} resident_MiB={mem_mib} min_duration_s={min_duration} fixed_K=8')
        for rep in range(1,4):
            modes=('early','late','full') if rep%2 else ('late','full','early')
            for mode in modes:
                problem=safety(quick)
                if problem:raise SafetyAbort(problem)
                v=sample(fixture,mode,.40 if quick else .60)
                samples.append(v)
                log(f'MASK_MEASURE stage={name} rep={rep} mode={mode} K=8 blocks_computed={2 if mode=="early" else 8} '
                    f'event_F_MAC={v["event_mac"]} avg_ms={v["ms"]:.6f} events={v["events"]} '
                    f'F_GMAC_s={v["gmac"]:.5f} fixture_contract=PASS')
        while time.monotonic()-since<min_duration:
            problem=safety(quick)
            if problem:raise SafetyAbort(problem)
            time.sleep(.15)
    except SafetyAbort as e:
        reason=str(e)
        log(f'SAFETY_ABORT stage={name} reason={reason} detail=workers_will_be_stopped')
    except BaseException as e:
        errors+=1
        log(f'STAGE_ERROR stage={name} type={type(e).__name__} detail={str(e)[:180]}')
    finally:
        cancel.set()
        for p in processes:
            p.join(5)
            if p.is_alive():p.kill();p.join(2)
        if holder:
            holder.join(3)
            if holder.is_alive():holder.kill();holder.join(2)
        good=0
        for _ in processes:
            try:
                pid,runs,low,mean,problems=out.get(timeout=3)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={runs} min_GMAC_s={low} mean_GMAC_s={mean} errors={problems}')
                if runs and not problems:good+=1
                else:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={name} status=RESULT_MISSING')
        for q in (out,ready,hold_ready):q.cancel_join_thread();q.close()
    okay,ratio=summarize(log,name,samples,errors,reason,good==count)
    b,t,m=telem();log(f'STAGE_TELEMETRY name={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return okay,reason,ratio,len(samples)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--quick',action='store_true',help='host smoke only; skips Android safety checks; not A52 evidence')
    args=parser.parse_args()
    home=Path.home();downloads=home/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_NATIVE_S5_TRUE_MASK_GATE_V9_{stamp}.txt'
    with report.open('x',encoding='utf-8') as fp:
        def log(msg):print(msg,flush=True);fp.write(msg+'\n');fp.flush()
        try:
            log('UNO / UNOVYRA -- NATIVE TRUE MASK GATE vs LATE DISCARD STRESS '+V)
            log('Synthetic C256R32 FP32, FIXED K=8: EARLY computes 2 blocks, LATE computes 8 but writes 2, FULL computes+writes 8.')
            log('Early and late are tested for identical state; late uses a volatile sink to prevent discarded work being optimized away.')
            log('2 and 4 existing native S5 load workers continuously active per stage; 32MiB held RAM per stage.')
            log('RAM hold x4 is 32MiB vs V8 64MiB to reduce memory pressure; 400000kB MemAvailable safety floor UNCHANGED.')
            log('NO real neural weights, learning, owner auth, OS dispatch, Android Binder, native STOP or production code.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telem();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            problem=safety(args.quick)
            if problem:log('RESULT SAFETY_SKIP reason='+problem);log('REPORT '+str(report));return 3
            background=verify_background_binary();log('VERIFIED_BACKGROUND_S5 '+str(background))
            root=home/'uno_a52_r41_true_mask_gate_v9'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            fixture,source_hash=compile_fixture(root)
            log('COMPILED_NATIVE_FIXTURE '+str(fixture)+' source_sha256='+source_hash)
            ctx=mp.get_context('fork')
            plans=[('S5x2_RAM32',2,32,7),('S5x4_RAM32',4,32,8)] if args.quick else [
                ('S5x2_RAM32',2,32,19),('S5x4_RAM32',4,32,23)]
            total=0;complete=0;ratios=[]
            for name,n,mem,duration in plans:
                problem=safety(args.quick)
                if problem:
                    log('RESULT SAFETY_ABORT_BEFORE_STAGE stage='+name+' reason='+problem)
                    log(f'PARTIAL_RESULT stages_complete={complete} measurements={total}')
                    log('REPORT '+str(report));return 3
                done,reason,ratio,num=run_stage(ctx,root,log,args.quick,name,n,mem,duration,fixture,background)
                total+=num;complete+=int(done);ratios.append(ratio)
                if reason:
                    log(f'RESULT SAFETY_ABORT stages_complete={complete} measurements={total} reason={reason}')
                    log('REPORT '+str(report));return 3
                if not done:
                    log(f'RESULT FAIL_OR_INCOMPLETE stages_complete={complete} measurements={total}')
                    log('REPORT '+str(report));return 2
            log(f'RESULT COMPLETE_NATIVE_MASK_EXPERIMENT stages_complete={complete} measurements={total} ratios={ratios}')
            log('INTERPRETATION: timing is local compute comparison, NOT real neural quality or Android energy; mask selection is synthetic.')
            log('LIMIT: same K=8 comparison isolates masked branch computation; none of this establishes full UNO global stability.')
            log('REPORT '+str(report));return 0
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPTED');log('REPORT '+str(report));return 130
        except BaseException as e:
            log('RESULT ERROR '+type(e).__name__+': '+str(e)[:200]);log('TRACE '+traceback.format_exc().splitlines()[-1])
            log('REPORT '+str(report));return 2
if __name__=='__main__':sys.exit(main())
