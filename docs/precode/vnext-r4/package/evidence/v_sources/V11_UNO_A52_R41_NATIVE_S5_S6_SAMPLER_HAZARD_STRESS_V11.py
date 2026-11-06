#!/usr/bin/env python3
"""UNO R4.1 experimental S6 prefix sampler / synthetic hazard / F-only MAC feasibility.
Actual native C256R32 FP32 on Android CPU under 2/4 continuously active S5 background jobs.
No trained selector or hazard, no whole-turn budget, no production code.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import math
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
from collections import Counter

VERSION = 'UNO_R41_A52_S6_SAMPLER_HAZARD_LOADED_V11'
BM = 28672
EPS = .05
TEMP = 1.0
SYNTHETIC_HAZARD_P = .35
MIB = 1048576
BUDGET_UNITS = (0,1,2,3,4,6,8,12,16,24,32,48,64)
C_SOURCE = '\n#define _POSIX_C_SOURCE 200809L\n#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n#include <string.h>\n#include <math.h>\n#include <time.h>\n#define D 256\n#define B 32\n#define NB 8\n#define U 128\n#define R 32\n#define BM 28672ull\nstatic float A2[NB][R][D], A1[NB][U][R], C2[NB][R][D], C1[NB][U][R], BB[NB][B][U];\nstatic volatile double discard_sink=0, output_sink=0;\nstatic uint32_t prng=0x3acd71b9u;\nstatic uint32_t r32(void){prng^=prng<<13;prng^=prng>>17;prng^=prng<<5;return prng;}\nstatic float sval(void){return ((float)(r32()%20001)/10000.f-1.f)*.008f;}\nstatic double clk(clockid_t id){struct timespec ts;clock_gettime(id,&ts);return ts.tv_sec+ts.tv_nsec*1e-9;}\nstatic void initialize(void){\n for(int j=0;j<NB;j++){\n  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A2[j][r][i]=sval();C2[j][r][i]=sval();}\n  for(int x=0;x<U;x++)for(int r=0;r<R;r++){A1[j][x][r]=sval();C1[j][x][r]=sval();}\n  for(int b=0;b<B;b++)for(int x=0;x<U;x++)BB[j][b][x]=sval();\n }\n}\nstatic void init_hz(float h[D],float z[D]){\n for(int i=0;i<D;i++){h[i]=.02f*(float)((i%17)-8);z[i]=.015f*(float)((i%11)-5);}\n}\nstatic int selected(int j,int q,int turn){return (j-turn+NB)%NB<q;}\nstatic unsigned long long do_step(float h[D],const float z[D],int q,int turn,int late){\n float next[D],a[R],c[R],u[U],v[B];unsigned long long done=0;\n memcpy(next,h,sizeof(next));\n for(int j=0;j<NB;j++){\n  int active=selected(j,q,turn);\n  if(!active&&!late)continue;\n  done++;\n  for(int r=0;r<R;r++){\n   float sa=0,sc=0;\n   for(int i=0;i<D;i++){sa+=A2[j][r][i]*h[i];sc+=C2[j][r][i]*z[i];}\n   a[r]=sa;c[r]=sc;\n  }\n  for(int x=0;x<U;x++){\n   float sa=0,sc=0;\n   for(int r=0;r<R;r++){sa+=A1[j][x][r]*a[r];sc+=C1[j][x][r]*c[r];}\n   u[x]=tanhf(sa+sc);\n  }\n  for(int b=0;b<B;b++){\n   float sv=0;for(int x=0;x<U;x++)sv+=BB[j][b][x]*u[x];\n   v[b]=tanhf(sv);\n  }\n  if(!active){discard_sink+=(double)v[j%B];continue;}\n  for(int b=0;b<B;b++)next[j*B+b]=.5f*h[j*B+b]+.5f*v[b];\n }\n memcpy(h,next,sizeof(next));return done;\n}\nstatic unsigned long long one_event(float h[D],const float z[D],int q,int K,int turn,int late){\n unsigned long long done=0;\n for(int k=0;k<K;k++)done+=do_step(h,z,q,turn,late);\n return done;\n}\nstatic int verify(int q,int K,int turn){\n float x[D],y[D],h[D],z[D];init_hz(h,z);\n memcpy(x,h,sizeof(x));memcpy(y,h,sizeof(y));\n unsigned long long a=one_event(x,z,q,K,turn,0),b=one_event(y,z,q,K,turn,1);\n int equal=memcmp(x,y,sizeof(x))==0,unchanged=1;\n for(int j=0;j<NB;j++)if(!selected(j,q,turn))\n  for(int i=j*B;i<(j+1)*B;i++)if(x[i]!=h[i])unchanged=0;\n printf("CONTRACT equal_gate_late=%s inactive_unchanged=%s gate_blocks=%llu late_blocks=%llu status=%s\\n",\n  equal?"YES":"NO",unchanged?"YES":"NO",a,b,(equal&&unchanged&&a==(unsigned long long)q*K&&b==(unsigned long long)NB*K)?"PASS":"FAIL");\n return equal&&unchanged&&a==(unsigned long long)q*K&&b==(unsigned long long)NB*K;\n}\nint main(int argc,char**argv){\n if(argc!=7){fprintf(stderr,"usage: fixture gate|late q K turn mac_budget duration_s\\n");return 2;}\n int late=!strcmp(argv[1],"late"),gate=!strcmp(argv[1],"gate");\n int q=atoi(argv[2]),K=atoi(argv[3]),turn=atoi(argv[4]);\n unsigned long long budget=strtoull(argv[5],NULL,10);\n double seconds=atof(argv[6]);\n if((!late&&!gate)||q<1||q>8||K<1||K>8||turn<0||turn>=8||seconds<.20||seconds>1.50)return 2;\n const unsigned long long required=(unsigned long long)(late?8:q)*K*BM;\n printf("REQUEST mode=%s q=%d K=%d turn=%d budget_mac=%llu required_mac=%llu\\n",argv[1],q,K,turn,budget,required);\n if(required>budget){\n  // Budget check precedes initialization and any F invocation.\n  printf("BUDGET_ABORT=no_F_invocation admission=DENIED executed_F_MAC=0 state_intact=YES beta_updated=NO status=PASS\\n");return 0;\n }\n initialize();\n if(!verify(q,K,turn))return 3;\n float h[D],z[D],orig[D];init_hz(orig,z);\n double wall_start=clk(CLOCK_MONOTONIC),cpu_start=clk(CLOCK_PROCESS_CPUTIME_ID);\n unsigned long long n=0,counted=0;double checksum=0;\n do{\n  memcpy(h,orig,sizeof(h));h[n%D]+=0.00001f;\n  counted+=one_event(h,z,q,K,turn,late);\n  checksum+=h[(n*31ull)%D];n++;\n }while(clk(CLOCK_MONOTONIC)-wall_start<seconds && n<3000000ull);\n double wall=clk(CLOCK_MONOTONIC)-wall_start,cpu=clk(CLOCK_PROCESS_CPUTIME_ID)-cpu_start;\n output_sink=checksum;\n unsigned long long executed=counted*BM,expected=n*required;\n printf("MEASURE mode=%s q=%d K=%d turn=%d events=%llu wall_ms_per_event=%.6f cpu_ms_per_event=%.6f total_F_MAC=%llu budget_per_event=%llu measured_blocks=%llu status=%s\\n",\n   argv[1],q,K,turn,n,wall*1000./n,cpu*1000./n,executed,budget,counted,executed==expected?"PASS":"FAIL");\n return executed==expected?0:4;\n}\n'


class Xorshift32:
    def __init__(self,seed):
        assert 0<seed<2**32
        self.s=seed
        self.draws=0
    def random(self):
        x=self.s
        x^=(x<<13)&0xffffffff
        x^=x>>17
        x^=(x<<5)&0xffffffff
        self.s=x & 0xffffffff
        self.draws+=1
        return self.s/4294967296.0

def candidate_logits(turn):
    # Deterministic synthetic logits; NOT W_M inference and NOT trained.
    return tuple(.65*math.sin((j+1)*.7+turn*.11)+.35*math.cos(j*1.3) for j in range(8))

def s6_probs(feasible,turn):
    if not feasible:return ()
    logits=candidate_logits(turn)
    scores=[]
    for q in feasible:
        # sigma(j)=(j+turn mod 8) mod 8
        scores.append(sum(logits[(j+turn)%8] for j in range(q))/math.sqrt(q)/TEMP)
    mx=max(scores)
    exps=[math.exp(a-mx) for a in scores]
    den=sum(exps)
    p=tuple(EPS/len(feasible)+(1-EPS)*v/den for v in exps)
    if not math.isclose(sum(p),1.0,rel_tol=0,abs_tol=1e-12):raise AssertionError('PROB_SUM')
    if min(p)+1e-14<EPS/len(feasible):raise AssertionError('NO_FULL_SUPPORT')
    return p

def choose(budget_mac,turn,rng):
    feasible=tuple(range(1,min(8,budget_mac//BM)+1))
    if not feasible:
        return (0,0,(),(),'BUDGET_ABORT')
    probs=s6_probs(feasible,turn)
    draw=rng.random()
    mass=0.0;q=feasible[-1]
    for prefix,p in zip(feasible,probs):
        mass+=p
        if draw<mass:
            q=prefix;break
    max_steps=min(8,budget_mac//(q*BM))
    if max_steps<1:raise AssertionError('EMPTY_STEPS')
    # Pre-sampled synthetic hazard. It does NOT use intermediate h_k;
    # production would sample hazard after each completed step.
    K=max_steps
    for k in range(1,max_steps+1):
        if rng.random()<SYNTHETIC_HAZARD_P:
            K=k;break
    if not (1<=q<=8 and 1<=K<=8 and q*K*BM<=budget_mac):
        raise AssertionError('BUDGET_OVERRUN')
    return(q,K,feasible,probs,'ADMITTED')

def selftest():
    assert choose(0,0,Xorshift32(1))[-1]=='BUDGET_ABORT'
    assert choose(BM-1,0,Xorshift32(1))[-1]=='BUDGET_ABORT'
    for turn in range(17):
        for b in BUDGET_UNITS:
            a=choose(b*BM,turn,Xorshift32(0x56ee2091))
            z=choose(b*BM,turn,Xorshift32(0x56ee2091))
            assert a==z
            q,K,feasible,probs,status=a
            if b==0:assert status=='BUDGET_ABORT'
            else:
                assert q in feasible and q*K<=b
                assert len(probs)==len(feasible)
                assert math.isclose(sum(probs),1.0,abs_tol=1e-12)
    # Check epsilon mixing on a fixed, fully feasible scenario by an independent empirical draw.
    feasible=tuple(range(1,9));p=s6_probs(feasible,5)
    rng=Xorshift32(0x38f7d1ab);count=Counter()
    for _ in range(8000):
        u=rng.random();sm=0
        for q,z in zip(feasible,p):
            sm+=z
            if u<sm:count[q]+=1;break
    assert sum(count.values())==8000
    assert max(abs(count[q]/8000-prob) for q,prob in zip(feasible,p))<.035
    return 'SELFTEST_PASS feasibility=YES epsilon_softmax=YES PRNG_replay=YES distribution_8000=YES'

def nint(p):
    try:return int(Path(p).read_text().strip())
    except (ValueError,OSError):return None

def telemetry():
    try:m=int(next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')).split()[1])
    except (ValueError,OSError,StopIteration,IndexError):m=None
    return nint('/sys/class/power_supply/battery/capacity'),nint('/sys/class/power_supply/battery/temp'),m

def safety(host_smoke):
    if host_smoke:return None
    b,t,m=telemetry()
    if None in(b,t,m) or not 100<=t<=800:return 'MISSING_OR_INVALID_HARDWARE_TELEMETRY'
    if b<40:return 'BATTERY_LT_40'
    if t>=375:return 'BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'MEMAVAILABLE_LT_400000_KB'
    return None

def compile_binary(root):
    src=root/'s6_synthetic_F.c';exe=root/'s6_synthetic_F'
    src.write_text(C_SOURCE,encoding='utf-8')
    clang=shutil.which('clang')
    if not clang:raise RuntimeError('CLANG_REQUIRED')
    p=subprocess.run([clang,'-O3','-std=c11','-Wall','-Wextra',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=40)
    if p.returncode:raise RuntimeError('COMPILATION_FAILURE '+p.stderr[-400:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def baseline_binary():
    exe=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not exe.exists() or not os.access(exe,os.X_OK):raise RuntimeError('BASELINE_S5_BINARY_MISSING')
    p=subprocess.run([str(exe),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=9)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BASELINE_S5_SELFTEST_FAILED')
    return exe

def background_worker(exe,cancel,res,ready):
    arr=[];err=[]
    try:
        while not cancel.is_set():
            p=subprocess.run([str(exe),'rank','full','0.70'],capture_output=True,text=True,timeout=9)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BACKGROUND_S5_ERROR')
            mt=re.search(r'estimated_F_GMAC_s=([.\d]+)',p.stdout)
            if not mt:raise RuntimeError('BACKGROUND_PERF_MISSING')
            arr.append(float(mt[1]))
            if len(arr)==1:ready.put(os.getpid(),timeout=2)
    except BaseException as e:err.append(str(e)[:120])
    try:res.put((os.getpid(),len(arr),statistics.mean(arr) if arr else None,min(arr) if arr else None,err),timeout=2)
    except BaseException:pass

def ram_holder(size_mib,cancel,ready):
    try:
        data=bytearray(size_mib*MIB)
        for i in range(0,len(data),4096):data[i]=1
        ready.put(True,timeout=3)
        while not cancel.wait(.15):
            for i in range(0,len(data),262144):data[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def native_execute(exe,q,K,turn,budget_mac,seconds):
    p=subprocess.run([str(exe),'gate',str(q),str(K),str(turn%8),str(budget_mac),f'{seconds:.2f}'],
                     capture_output=True,text=True,timeout=12)
    if p.returncode:raise RuntimeError(f'EXEC_FAIL_{p.returncode} '+p.stdout[-230:]+p.stderr[-100:])
    if 'CONTRACT equal_gate_late=YES inactive_unchanged=YES' not in p.stdout:raise RuntimeError('STATE_CONTRACT_FAIL')
    mt=re.search(r'MEASURE mode=gate q=(\d+) K=(\d+) turn=(\d+) events=(\d+) wall_ms_per_event=([.\d]+) cpu_ms_per_event=([.\d]+) total_F_MAC=(\d+) budget_per_event=(\d+) measured_blocks=(\d+) status=(PASS|FAIL)',p.stdout)
    if not mt:raise RuntimeError('MEASUREMENT_MISSING '+p.stdout[-120:])
    qq,kk,tt,ev,wall,cpu,total,bud,blocks,status=mt.groups()
    if (int(qq),int(kk),int(tt),int(bud),status)!=(q,K,turn%8,budget_mac,'PASS'):raise RuntimeError('PARAMETER_MISMATCH')
    if int(blocks)!=int(ev)*q*K or int(total)!=int(ev)*q*K*BM:raise RuntimeError('MAC_LEDGER_MISMATCH')
    return int(ev),float(wall),float(cpu)

def stage(log,ctx,exe,baseline,name,nworkers,stage_floor,host_smoke):
    cancel=ctx.Event();ready=ctx.Queue();res=ctx.Queue();rready=ctx.Queue();workers=[];holder=None
    started=time.monotonic();observations=[];plans=[];blocked=0;failures=0;stop_reason=None;finished=0
    seed=0x71c35519+nworkers
    generator=Xorshift32(seed)
    ntrials=10 if host_smoke else 39
    try:
        holder=ctx.Process(target=ram_holder,args=(32,cancel,rready));holder.start()
        if rready.get(timeout=8) is not True:raise RuntimeError('RAM_HOLDER_START_FAIL')
        for _ in range(nworkers):
            w=ctx.Process(target=background_worker,args=(baseline,cancel,res,ready));w.start();workers.append(w)
        r={ready.get(timeout=24) for _ in workers}
        if len(r)!=nworkers:raise RuntimeError('S5_NOT_CONTINUOUSLY_ACTIVE')
        log(f'STAGE_BEGIN stage={name} S5_background={nworkers} RAM_MiB=32 trials={ntrials} min_duration_s={stage_floor}')
        for idx in range(ntrials):
            if why:=safety(host_smoke):stop_reason=why;break
            units=BUDGET_UNITS[(idx*7+idx//len(BUDGET_UNITS))%len(BUDGET_UNITS)]
            # Ensure both zero budget and broad prefixes are exercised systematically.
            units=BUDGET_UNITS[idx%len(BUDGET_UNITS)] if idx%2==0 else units
            turn=idx
            before=generator.draws
            q,K,feasible,p,status=choose(units*BM,turn,generator)
            plans.append((units,turn,q,K,status,before,generator.draws))
            if status=='BUDGET_ABORT':
                blocked+=1
                log(f'ADMISSION stage={name} trial={idx} budget_F_MAC={units*BM} status=BUDGET_ABORT q=NONE K=NONE invoked_F=NO draws_used={generator.draws-before}')
                continue
            if q*K>units:raise RuntimeError('F_MAC_OVERRUN')
            ev,wall,cpu=native_execute(exe,q,K,turn,units*BM,.21 if host_smoke else .26)
            observations.append((wall,cpu,q,K,units))
            if idx%4==0 or idx==ntrials-1:
                log(f'S6_EXEC stage={name} trial={idx} turn={turn} budget_F_MAC={units*BM} feasible_prefixes={len(feasible)} '
                    f'selected_q={q} sampled_K={K} reserved_F_MAC={q*K*BM} events={ev} '
                    f'wall_ms_per_event={wall:.4f} cpu_ms_per_event={cpu:.4f} replay_draws={generator.draws-before} status=PASS')
        # Pure selector replay with the same logged seed, independent of executing F.
        rng=Xorshift32(seed)
        for units,turn,q,K,status,prev,post in plans:
            if prev!=rng.draws:raise RuntimeError('REPLAY_RNG_OFFSET_MISMATCH')
            a=choose(units*BM,turn,rng)
            if (q,K,status)!=(a[0],a[1],a[-1]) or rng.draws!=post:raise RuntimeError('SELECTOR_REPLAY_MISMATCH')
        log(f'REPLAY_CHECK stage={name} decisions={len(plans)} seed=0x{seed:08x} exact_match=YES random_draws={rng.draws}')
        while time.monotonic()-started<stage_floor:
            if why:=safety(host_smoke):stop_reason=why;break
            time.sleep(.15)
    except BaseException as e:
        failures+=1
        log(f'STAGE_ERROR stage={name} error={type(e).__name__} detail={str(e)[:200]}')
    finally:
        cancel.set()
        for w in workers:
            w.join(5)
            if w.is_alive():w.kill();w.join(2)
        if holder:
            holder.join(3)
            if holder.is_alive():holder.kill();holder.join(2)
        for _ in workers:
            try:
                pid,ran,avg,lo,err=res.get(timeout=2)
                log(f'S5_WORKER stage={name} pid={pid} native_runs={ran} mean_GMAC_s={avg} min_GMAC_s={lo} errors={err}')
                if ran>0 and not err:finished+=1
                else:failures+=1
            except queue.Empty:
                failures+=1;log(f'S5_WORKER stage={name} RESULT_MISSING')
        for qobj in (ready,res,rready):qobj.cancel_join_thread();qobj.close()
    status='SAFETY_ABORT' if stop_reason else ('COMPLETE' if failures==0 and len(plans)==ntrials and finished==nworkers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={name} status={status} planned={len(plans)}/{ntrials} native_exec={len(observations)} '
        f'zero_feasible_aborts={blocked} workers_ok={finished}/{nworkers} failures={failures} '
        f'wall_median_ms={statistics.median(z[0] for z in observations) if observations else None} '
        f'wall_max_ms={max(z[0] for z in observations) if observations else None} '
        f'cpu_median_ms={statistics.median(z[1] for z in observations) if observations else None} '
        f'PRNG_replay={"YES" if failures==0 else "UNKNOWN"} safety_reason={stop_reason or "-"}')
    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={name} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return status,len(observations),blocked

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='HOST-ONLY; never use this option on A52')
    args=ap.parse_args()
    root=Path.home();downloads=root/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=root
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_S6_SAMPLER_HAZARD_V11_{stamp}.txt'
    with report.open('x',encoding='utf-8') as fp:
        def log(s):print(s,flush=True);fp.write(s+'\n');fp.flush()
        try:
            log('UNO / UNOVYRA -- R4.1 S6 SYNTHETIC EPSILON-SOFTMAX / HAZARD UNDER NATIVE ARM S5 '+VERSION)
            log('S6 trial: nonempty cyclic prefixes, epsilon=0.05 T=1, deterministic recorded PRNG, synthetic logits and presampled hazard=0.35; NOT W_M or neural hazard inference.')
            log('Feasibility is F-only MAC cap, NOT full turn admission: encoder, heads, time, memory, tokens and OS/thermal costs excluded.')
            log('Real native FP32 C256R32 work runs on Android CPU under 2/4 continuously active S5 workers plus touched 32MiB RAM. No idle stage.')
            log('NO: model training, production neural weights, Android permissions, real actions, owner authorization, Binder, hardware power-cut, global stability, quality proof or deadline guarantee.')
            log('SAFETY: battery>=40%; battery temperature<37.5C; MemAvailable>=400000 kB; script cleans up child processes on exit.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if reason:=safety(args.host_smoke):
                log(f'RESULT SAFETY_SKIP reason={reason}');log(f'REPORT {report}');return 3
            log(selftest())
            baseline=baseline_binary();log('VERIFIED_BACKGROUND_S5 '+str(baseline))
            work=root/'uno_a52_r41_s6_sampler_v11'/stamp
            work.mkdir(parents=True,mode=0o700,exist_ok=False)
            exe,sha=compile_binary(work);log(f'COMPILED_NATIVE_F {exe} source_sha256={sha}')
            specs=[('S5x2_RAM32',2,3),('S5x4_RAM32',4,4)] if args.host_smoke else [('S5x2_RAM32',2,24),('S5x4_RAM32',4,30)]
            total_exec=total_abort=complete=0
            for name,nworkers,floor in specs:
                if reason:=safety(args.host_smoke):
                    log(f'RESULT SAFETY_ABORT_BEFORE_STAGE name={name} reason={reason} completed={complete}')
                    log(f'REPORT {report}');return 3
                status,exec_n,abort_n=stage(log,mp.get_context('fork'),exe,baseline,name,nworkers,floor,args.host_smoke)
                total_exec+=exec_n;total_abort+=abort_n;complete+=status=='COMPLETE'
                if status!='COMPLETE':
                    log(f'RESULT {status} completed_stages={complete}/2 native_executions={total_exec} budget_aborts={total_abort}')
                    log(f'REPORT {report}');return 3 if status=='SAFETY_ABORT' else 2
            log(f'RESULT COMPLETE_S6_SAMPLER_LAB stages={complete}/2 native_executions={total_exec} budget_aborts={total_abort}')
            log('LIMIT: seeded synthetic selector with presampled K is not learned adaptive computation; it does not satisfy S6 full-resource feasibility or after-step state-dependent hazard.')
            log(f'REPORT {report}');return 0
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPTED');log(f'REPORT {report}');return 130
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:200]}')
            log('TRACE '+traceback.format_exc().splitlines()[-1]);log(f'REPORT {report}');return 2

if __name__=='__main__':sys.exit(main())
