#!/usr/bin/env python3
"""UNO R4.1 PRECODE V10: native cyclic-prefix mask / K / MAC budget under actual S5 background load.

No production neural weights; synthetic deterministic low-rank C256R32 workload.
The lab budget is for F MAC only: not a bound on real elapsed time, overhead or energy.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
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

VERSION='UNO_R41_A52_NATIVE_S5_PREFIX_BUDGET_STRESS_V10'
MIB=1048576
BRANCH_MAC=28672
CONFIGS=[(1,1,3),(1,8,7),(2,4,1),(4,4,5),(4,8,2),(8,8,0)]
C_SOURCE=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#define D 256
#define B 32
#define NB 8
#define U 128
#define R 32
#define BM 28672ull
static float A2[NB][R][D], A1[NB][U][R], C2[NB][R][D], C1[NB][U][R], BB[NB][B][U];
static volatile double discard_sink=0, output_sink=0;
static uint32_t prng=0x3acd71b9u;
static uint32_t r32(void){prng^=prng<<13;prng^=prng>>17;prng^=prng<<5;return prng;}
static float sval(void){return ((float)(r32()%20001)/10000.f-1.f)*.008f;}
static double clk(clockid_t id){struct timespec ts;clock_gettime(id,&ts);return ts.tv_sec+ts.tv_nsec*1e-9;}
static void initialize(void){
 for(int j=0;j<NB;j++){
  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A2[j][r][i]=sval();C2[j][r][i]=sval();}
  for(int x=0;x<U;x++)for(int r=0;r<R;r++){A1[j][x][r]=sval();C1[j][x][r]=sval();}
  for(int b=0;b<B;b++)for(int x=0;x<U;x++)BB[j][b][x]=sval();
 }
}
static void init_hz(float h[D],float z[D]){
 for(int i=0;i<D;i++){h[i]=.02f*(float)((i%17)-8);z[i]=.015f*(float)((i%11)-5);}
}
static int selected(int j,int q,int turn){return (j-turn+NB)%NB<q;}
static unsigned long long do_step(float h[D],const float z[D],int q,int turn,int late){
 float next[D],a[R],c[R],u[U],v[B];unsigned long long done=0;
 memcpy(next,h,sizeof(next));
 for(int j=0;j<NB;j++){
  int active=selected(j,q,turn);
  if(!active&&!late)continue;
  done++;
  for(int r=0;r<R;r++){
   float sa=0,sc=0;
   for(int i=0;i<D;i++){sa+=A2[j][r][i]*h[i];sc+=C2[j][r][i]*z[i];}
   a[r]=sa;c[r]=sc;
  }
  for(int x=0;x<U;x++){
   float sa=0,sc=0;
   for(int r=0;r<R;r++){sa+=A1[j][x][r]*a[r];sc+=C1[j][x][r]*c[r];}
   u[x]=tanhf(sa+sc);
  }
  for(int b=0;b<B;b++){
   float sv=0;for(int x=0;x<U;x++)sv+=BB[j][b][x]*u[x];
   v[b]=tanhf(sv);
  }
  if(!active){discard_sink+=(double)v[j%B];continue;}
  for(int b=0;b<B;b++)next[j*B+b]=.5f*h[j*B+b]+.5f*v[b];
 }
 memcpy(h,next,sizeof(next));return done;
}
static unsigned long long one_event(float h[D],const float z[D],int q,int K,int turn,int late){
 unsigned long long done=0;
 for(int k=0;k<K;k++)done+=do_step(h,z,q,turn,late);
 return done;
}
static int verify(int q,int K,int turn){
 float x[D],y[D],h[D],z[D];init_hz(h,z);
 memcpy(x,h,sizeof(x));memcpy(y,h,sizeof(y));
 unsigned long long a=one_event(x,z,q,K,turn,0),b=one_event(y,z,q,K,turn,1);
 int equal=memcmp(x,y,sizeof(x))==0,unchanged=1;
 for(int j=0;j<NB;j++)if(!selected(j,q,turn))
  for(int i=j*B;i<(j+1)*B;i++)if(x[i]!=h[i])unchanged=0;
 printf("CONTRACT equal_gate_late=%s inactive_unchanged=%s gate_blocks=%llu late_blocks=%llu status=%s\n",
  equal?"YES":"NO",unchanged?"YES":"NO",a,b,(equal&&unchanged&&a==(unsigned long long)q*K&&b==(unsigned long long)NB*K)?"PASS":"FAIL");
 return equal&&unchanged&&a==(unsigned long long)q*K&&b==(unsigned long long)NB*K;
}
int main(int argc,char**argv){
 if(argc!=7){fprintf(stderr,"usage: fixture gate|late q K turn mac_budget duration_s\n");return 2;}
 int late=!strcmp(argv[1],"late"),gate=!strcmp(argv[1],"gate");
 int q=atoi(argv[2]),K=atoi(argv[3]),turn=atoi(argv[4]);
 unsigned long long budget=strtoull(argv[5],NULL,10);
 double seconds=atof(argv[6]);
 if((!late&&!gate)||q<1||q>8||K<1||K>8||turn<0||turn>=8||seconds<.20||seconds>1.50)return 2;
 const unsigned long long required=(unsigned long long)(late?8:q)*K*BM;
 printf("REQUEST mode=%s q=%d K=%d turn=%d budget_mac=%llu required_mac=%llu\n",argv[1],q,K,turn,budget,required);
 if(required>budget){
  // Budget check precedes initialization and any F invocation.
  printf("BUDGET_ABORT=no_F_invocation admission=DENIED executed_F_MAC=0 state_intact=YES beta_updated=NO status=PASS\n");return 0;
 }
 initialize();
 if(!verify(q,K,turn))return 3;
 float h[D],z[D],orig[D];init_hz(orig,z);
 double wall_start=clk(CLOCK_MONOTONIC),cpu_start=clk(CLOCK_PROCESS_CPUTIME_ID);
 unsigned long long n=0,counted=0;double checksum=0;
 do{
  memcpy(h,orig,sizeof(h));h[n%D]+=0.00001f;
  counted+=one_event(h,z,q,K,turn,late);
  checksum+=h[(n*31ull)%D];n++;
 }while(clk(CLOCK_MONOTONIC)-wall_start<seconds && n<3000000ull);
 double wall=clk(CLOCK_MONOTONIC)-wall_start,cpu=clk(CLOCK_PROCESS_CPUTIME_ID)-cpu_start;
 output_sink=checksum;
 unsigned long long executed=counted*BM,expected=n*required;
 printf("MEASURE mode=%s q=%d K=%d turn=%d events=%llu wall_ms_per_event=%.6f cpu_ms_per_event=%.6f total_F_MAC=%llu budget_per_event=%llu measured_blocks=%llu status=%s\n",
   argv[1],q,K,turn,n,wall*1000./n,cpu*1000./n,executed,budget,counted,executed==expected?"PASS":"FAIL");
 return executed==expected?0:4;
}
'''

def nint(p):
    try:return int(Path(p).read_text().strip())
    except (OSError,ValueError):return None

def telem():
    try:
        m=int(next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')).split()[1])
    except (OSError,ValueError,StopIteration,IndexError):m=None
    return nint('/sys/class/power_supply/battery/capacity'),nint('/sys/class/power_supply/battery/temp'),m

def safety(host_smoke):
    if host_smoke:return None
    b,t,m=telem()
    if None in (b,t,m) or not 100<=t<=800:return 'UNAVAILABLE_OR_INVALID_TELEMETRY'
    if b<40:return 'BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'BATTERY_TEMP_AT_LEAST_37_5C'
    if m<400000:return 'MEMAVAILABLE_BELOW_400000_KB'
    return None

def compile_native(root):
    exe=root/'budgeted_cyclic_mask';src=root/'budgeted_cyclic_mask.c'
    src.write_text(C_SOURCE,encoding='utf-8')
    clang=shutil.which('clang')
    if not clang:raise RuntimeError('CLANG_REQUIRED')
    p=subprocess.run([clang,'-O3','-std=c11','-Wall','-Wextra',str(src),'-lm','-o',str(exe)],text=True,capture_output=True,timeout=35)
    if p.returncode:raise RuntimeError('C_COMPILATION_FAILED '+p.stderr[-350:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def background_check():
    bin=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not bin.is_file() or not os.access(bin,os.X_OK):raise RuntimeError('NATIVE_S5_BASELINE_BINARY_MISSING')
    p=subprocess.run([str(bin),'rank','prefix2','0.30'],text=True,capture_output=True,timeout=9)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('NATIVE_S5_BASELINE_SELFTEST_FAILED')
    return bin

def bg_worker(bin,cancel,results,ready):
    rates=[];errs=[]
    try:
        while not cancel.is_set():
            p=subprocess.run([str(bin),'rank','full','0.70'],text=True,capture_output=True,timeout=9)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BASELINE_EXEC_FAIL')
            mt=re.search(r'estimated_F_GMAC_s=([0-9.]+)',p.stdout)
            if not mt:raise RuntimeError('GMAC_NOT_PRESENT')
            rates.append(float(mt[1]))
            if len(rates)==1:ready.put(os.getpid(),timeout=2)
    except BaseException as e:errs.append(str(e)[:100])
    try:results.put((os.getpid(),len(rates),min(rates) if rates else None,statistics.mean(rates) if rates else None,errs),timeout=2)
    except BaseException:pass

def hold_ram(mib,cancel,ready):
    try:
        mem=bytearray(mib*MIB)
        for i in range(0,len(mem),4096):mem[i]=1
        ready.put(True,timeout=3)
        while not cancel.wait(.12):
            for i in range(0,len(mem),262144):mem[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def run_fixture(bin,mode,q,K,turn,budget,seconds):
    args=[str(bin),mode,str(q),str(K),str(turn),str(budget),f'{seconds:.2f}']
    p=subprocess.run(args,capture_output=True,text=True,timeout=max(9,seconds+8))
    if p.returncode:raise RuntimeError(f'FIXTURE_EXIT_{p.returncode} '+p.stdout[-200:]+p.stderr[-100:])
    if p.stdout.count('BUDGET_ABORT='):
        if 'admission=DENIED executed_F_MAC=0' not in p.stdout or 'status=PASS' not in p.stdout:raise RuntimeError('ABORT_MISMATCH')
        return {'abort':True,'mode':mode,'q':q,'K':K,'turn':turn}
    if not re.search(r'CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('GATE_DENSE_STATE_CONTRACT_FAIL')
    mm=re.search(r'MEASURE mode=(\w+) q=(\d+) K=(\d+) turn=(\d+) events=(\d+) wall_ms_per_event=([.\d]+) cpu_ms_per_event=([.\d]+) total_F_MAC=(\d+) budget_per_event=(\d+) measured_blocks=(\d+) status=(PASS|FAIL)',p.stdout)
    if not mm:raise RuntimeError('BAD_MEASURE_OUTPUT '+p.stdout[-200:])
    mode0,q0,k0,turn0,n,wall,cpu,total,budget0,blocks,status=mm.groups()
    n=int(n);total=int(total);blocks=int(blocks)
    expected_blocks=n*(8 if mode=='late' else q)*K
    if (mode0,q0,k0,turn0,status)!=(mode,str(q),str(K),str(turn),'PASS') or total!=expected_blocks*BRANCH_MAC or blocks!=expected_blocks or int(budget0)!=budget:
        raise RuntimeError('EXECUTED_LEDGER_MISMATCH')
    return {'abort':False,'mode':mode,'q':q,'K':K,'turn':turn,'events':n,'wall_ms':float(wall),'cpu_ms':float(cpu),'mac':total//n}

def stage(log,ctx,bin,background,name,workers,min_seconds,host_smoke,inject_abort=False):
    cancel=ctx.Event();results=ctx.Queue();ready=ctx.Queue();ram_ready=ctx.Queue()
    procs=[];holder=None;measurements=[];abort_count=0;failures=0;stop_reason=None;start=time.monotonic()
    try:
        holder=ctx.Process(target=hold_ram,args=(32,cancel,ram_ready));holder.start()
        if ram_ready.get(timeout=9) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(workers):
            p=ctx.Process(target=bg_worker,args=(background,cancel,results,ready));p.start();procs.append(p)
        active=set()
        for _ in range(workers):active.add(ready.get(timeout=22))
        if len(active)!=workers:raise RuntimeError('BACKGROUND_WORKER_COUNT_MISMATCH')
        log(f'STAGE_BEGIN name={name} S5_active={len(active)} resident_ram_MiB=32 synthetic_F=YES min_duration_s={min_seconds}')
        # The order is changed between repetitions; no zero-load phase.
        for rep in (1,2):
            configs=CONFIGS if rep==1 else tuple(reversed(CONFIGS))
            for q,K,turn in configs:
                if (err:=safety(host_smoke)):
                    stop_reason=err;break
                grant=q*K*BRANCH_MAC
                # A real gate is charged for actually executed branches.
                g=run_fixture(bin,'gate',q,K,turn,grant,.28 if host_smoke else .38)
                l=run_fixture(bin,'late',q,K,turn,8*K*BRANCH_MAC,.28 if host_smoke else .38)
                if g['abort'] or l['abort']:raise RuntimeError('UNEXPECTED_BUDGET_ABORT')
                measurements.extend((g,l))
                if inject_abort and len(measurements)>=6:
                    stop_reason='HOST_INJECTED_SAFETY_ABORT_AFTER_3_PAIRS'
                    log(f'SAFETY_ABORT stage={name} reason={stop_reason} cleanup=IN_PROGRESS')
                    break
                ratio=l['wall_ms']/g['wall_ms'] if g['wall_ms'] else float('nan')
                log(f'PAIR stage={name} rep={rep} q={q} K={K} turnSerial={turn} '
                    f'gate_MAC={g["mac"]} late_MAC={l["mac"]} '
                    f'gate_wall_ms={g["wall_ms"]:.6f} late_wall_ms={l["wall_ms"]:.6f} '
                    f'gate_cpu_ms={g["cpu_ms"]:.6f} late_cpu_ms={l["cpu_ms"]:.6f} '
                    f'wall_ratio={ratio:.3f} state_contract=PASS ledger=PASS')
                # Negative control: the same underfunded late compute must refuse before F invocation.
                if q<8 and K==8:
                    denied=run_fixture(bin,'late',q,K,turn,grant,.28)
                    if not denied['abort']:raise RuntimeError('UNDERBUDGET_LATE_WAS_ADMITTED')
                    abort_count+=1
                    log(f'BUDGET_ABORT_CHECK stage={name} rep={rep} q={q} K={K} '
                        f'budget_MAC={grant} late_required_MAC={8*K*BRANCH_MAC} '
                        'no_F_invocation=YES state_intact=YES result=PASS')
            if stop_reason:break
        # Impossible zero-budget prefix: must abstain, never invent q=0.
        if not stop_reason:
            for rep in range(2):
                x=run_fixture(bin,'gate',1,1,rep,0,.28)
                if not x['abort']:raise RuntimeError('EMPTY_FEASIBLE_SET_DID_NOT_ABORT')
                abort_count+=1
            log(f'EMPTY_FEASIBLE_SET stage={name} zero_budget_trials=2 result=BUDGET_ABORT no_F_invocation=YES')
            while time.monotonic()-start<min_seconds:
                if (err:=safety(host_smoke)):
                    stop_reason=err;break
                time.sleep(.12)
    except BaseException as e:
        failures+=1
        log(f'STAGE_ERROR stage={name} type={type(e).__name__} message={str(e)[:220]}')
    finally:
        cancel.set()
        for p in procs:
            p.join(5)
            if p.is_alive():p.kill();p.join(2)
        if holder:
            holder.join(3)
            if holder.is_alive():holder.kill();holder.join(2)
        done=0
        for _ in procs:
            try:
                pid,n,lo,avg,err=results.get(timeout=2)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={n} min_GMAC_s={lo} mean_GMAC_s={avg} errors={err}')
                if n>0 and not err:done+=1
                else:failures+=1
            except queue.Empty:
                failures+=1;log(f'S5_WORKER stage={name} RESULT_MISSING')
        for mq in (results,ready,ram_ready):mq.cancel_join_thread();mq.close()
    pairs=[(measurements[i],measurements[i+1]) for i in range(0,len(measurements)-1,2)]
    cpu_ratios=[l['cpu_ms']/g['cpu_ms'] for g,l in pairs if g['cpu_ms']>0]
    wall_ratios=[l['wall_ms']/g['wall_ms'] for g,l in pairs if g['wall_ms']>0]
    status='SAFETY_ABORT' if stop_reason else ('COMPLETE' if failures==0 and done==workers and len(pairs)==12 and abort_count==6 else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY name={name} status={status} pairs={len(pairs)}/12 abort_checks={abort_count}/6 '
        f'background_workers_ok={done}/{workers} errors={failures} '
        f'median_wall_ratio={statistics.median(wall_ratios) if wall_ratios else None} '
        f'median_cpu_ratio={statistics.median(cpu_ratios) if cpu_ratios else None} '
        f'wall_ratio_min={min(wall_ratios) if wall_ratios else None} '
        f'wall_ratio_max={max(wall_ratios) if wall_ratios else None} safety_reason={stop_reason or "-"}')
    b,t,m=telem();log(f'STAGE_TELEMETRY name={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return status,len(pairs),abort_count

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='HOST ONLY: bypasses battery telemetry; NOT phone evidence')
    ap.add_argument('--host-abort-check',action='store_true',help='HOST ONLY: inject safety abort after 3 pairs; not for Android')
    args=ap.parse_args()
    if args.host_abort_check and not args.host_smoke:
        ap.error('--host-abort-check requires --host-smoke')
    home=Path.home();download=home/'storage'/'downloads'
    if not download.is_dir() or not os.access(download,os.W_OK):download=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=download/f'UNO_A52_R41_S5_PREFIX_BUDGET_V10_{stamp}.txt'
    with report.open('x',encoding='utf-8') as fp:
        def log(s):print(s,flush=True);fp.write(s+'\n');fp.flush()
        try:
            log('UNO / UNOVYRA -- CYCLIC PREFIX MASK + MAC ADMISSION UNDER NATIVE S5 LOAD '+VERSION)
            log('R4.1 S6 candidate cyclic-prefix q and forced K in [1,8], not actual S6 learned logits/hazard or production policy.')
            log('Native synthetic C256R32 FP32; distinct measured CPU time vs elapsed wall time. Counted F-MAC excludes control, DSP, memory scan, cache effects and system overhead.')
            log('2 and 4 native S5 background workers, 32 MiB touched RAM; no zero-load stage. Fixed hardware safety guard: battery>=40%, battery temp<37.5C, MemAvailable>=400000 kB.')
            log('NOT real trained weights, model quality, energy, Android dispatcher, permissions, owner auth, production code, deadline SLA or neural learning.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telem();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if err:=safety(args.host_smoke):
                log('RESULT SAFETY_SKIP reason='+err);log('REPORT '+str(report));return 3
            background=background_check();log('VERIFIED_BACKGROUND_S5 '+str(background))
            root=home/'uno_a52_r41_prefix_budget_v10'/stamp
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            bin,sha=compile_native(root)
            log(f'COMPILED_NATIVE_FIXTURE {bin} source_sha256={sha}')
            plans=[('S5x2_RAM32',2,3),('S5x4_RAM32',4,4)] if args.host_smoke else [('S5x2_RAM32',2,22),('S5x4_RAM32',4,28)]
            passed=0;count=0;denied=0
            for name,workers,floor in plans:
                if err:=safety(args.host_smoke):
                    log(f'RESULT SAFETY_ABORT_BEFORE_STAGE name={name} reason={err} partial_pairs={count}')
                    log('REPORT '+str(report));return 3
                status,pairs,aborts=stage(log,mp.get_context('fork'),bin,background,name,workers,floor,args.host_smoke,args.host_abort_check)
                count+=pairs;denied+=aborts;passed+=status=='COMPLETE'
                if status!='COMPLETE':
                    log(f'RESULT {status} stages_complete={passed} pairs={count} budget_aborts={denied}')
                    log('REPORT '+str(report));return 3 if status=='SAFETY_ABORT' else 2
            log(f'RESULT COMPLETE_NATIVE_PREFIX_BUDGET_LAB stages={passed}/2 pairs={count}/24 budget_abort_checks={denied}/12')
            log('LIMIT: budget governs only counted synthetic F MAC; CPU and wall time are measured, not guaranteed, and no trained-model quality or platform security is shown.')
            log('REPORT '+str(report));return 0
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPTED');log('REPORT '+str(report));return 130
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:220]}')
            log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2
if __name__=='__main__':sys.exit(main())
