#!/usr/bin/env python3
"""R4.1 S6 local synthetic AFTER-STEP state-dependent hazard, real ARM S5 CPU load.
LAB-ONLY. No production code, real authorization, model weights, Android dispatch or training.
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

VERSION = 'UNO_R41_A52_S6_AFTER_STEP_HAZARD_LOADED_V12'
BM = 28672
EPS = 0.05
MIB = 1048576
BUDGET_UNITS = (0,1,2,3,4,6,8,12,16,24,32,48,64)
C_SOURCE = '\n#define _POSIX_C_SOURCE 200809L\n#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n#include <string.h>\n#include <math.h>\n#include <time.h>\n#define D 256\n#define B 32\n#define NB 8\n#define U 128\n#define R 32\n#define BM 28672ull\nstatic float A2[NB][R][D], A1[NB][U][R], C2[NB][R][D], C1[NB][U][R], BB[NB][B][U];\nstatic volatile double discard_sink=0, output_sink=0;\nstatic uint32_t prng=0x3acd71b9u;\nstatic uint32_t r32(void){prng^=prng<<13;prng^=prng>>17;prng^=prng<<5;return prng;}\nstatic float sval(void){return ((float)(r32()%20001)/10000.f-1.f)*.008f;}\nstatic double clk(clockid_t id){struct timespec ts;clock_gettime(id,&ts);return ts.tv_sec+ts.tv_nsec*1e-9;}\nstatic void initialize(void){\n for(int j=0;j<NB;j++){\n  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A2[j][r][i]=sval();C2[j][r][i]=sval();}\n  for(int x=0;x<U;x++)for(int r=0;r<R;r++){A1[j][x][r]=sval();C1[j][x][r]=sval();}\n  for(int b=0;b<B;b++)for(int x=0;x<U;x++)BB[j][b][x]=sval();\n }\n}\nstatic void init_hz(float h[D],float z[D]){\n for(int i=0;i<D;i++){h[i]=.02f*(float)((i%17)-8);z[i]=.015f*(float)((i%11)-5);}\n}\nstatic int selected(int j,int q,int turn){return (j-turn+NB)%NB<q;}\nstatic unsigned long long do_step(float h[D],const float z[D],int q,int turn,int late){\n float next[D],a[R],c[R],u[U],v[B];unsigned long long done=0;\n memcpy(next,h,sizeof(next));\n for(int j=0;j<NB;j++){\n  int active=selected(j,q,turn);\n  if(!active&&!late)continue;\n  done++;\n  for(int r=0;r<R;r++){\n   float sa=0,sc=0;\n   for(int i=0;i<D;i++){sa+=A2[j][r][i]*h[i];sc+=C2[j][r][i]*z[i];}\n   a[r]=sa;c[r]=sc;\n  }\n  for(int x=0;x<U;x++){\n   float sa=0,sc=0;\n   for(int r=0;r<R;r++){sa+=A1[j][x][r]*a[r];sc+=C1[j][x][r]*c[r];}\n   u[x]=tanhf(sa+sc);\n  }\n  for(int b=0;b<B;b++){\n   float sv=0;for(int x=0;x<U;x++)sv+=BB[j][b][x]*u[x];\n   v[b]=tanhf(sv);\n  }\n  if(!active){discard_sink+=(double)v[j%B];continue;}\n  for(int b=0;b<B;b++)next[j*B+b]=.5f*h[j*B+b]+.5f*v[b];\n }\n memcpy(h,next,sizeof(next));return done;\n}\n\nstatic unsigned long long tick_seed=0;\nstatic uint64_t digest(uint64_t hsh,const float *h,int k){\n  hsh ^= (uint64_t)k; hsh*=1099511628211ull;\n  for(int i=0;i<D;i+=17){uint32_t bits;memcpy(&bits,&h[i],4);hsh ^= bits;hsh*=1099511628211ull;}\n  return hsh;\n}\nstatic float hazard_probability(const float h[D],int active_index){\n  // DEMO STATE-DEPENDENT HAZARD: current h after native F step, not the initial h or pre-sampled K.\n  double x=4.0*(double)h[active_index];\n  return (float)(1.0/(1.0+exp(-x)));\n}\nstatic int mask_contract(int q,int turn){\n float h[D],z[D],x[D],y[D];init_hz(h,z);\n memcpy(x,h,sizeof(x));memcpy(y,h,sizeof(y));\n unsigned long long a=do_step(x,z,q,turn,0),b=do_step(y,z,q,turn,1);\n int same=memcmp(x,y,sizeof(x))==0,untouched=1;\n for(int j=0;j<NB;j++)if(!selected(j,q,turn))for(int i=j*B;i<(j+1)*B;i++)\n  if(h[i]!=x[i])untouched=0;\n printf("MASK_CONTRACT early_equals_late=%s inactive_preserved=%s early_blocks=%llu late_blocks=%llu status=%s\\n",\n   same?"YES":"NO",untouched?"YES":"NO",a,b,(same&&untouched&&a==(unsigned long long)q&&b==NB)?"PASS":"FAIL");\n return same&&untouched&&a==(unsigned long long)q&&b==NB;\n}\nstatic int execute_turn(float h[D],float z[D],int q,int turn,int maxsteps,float *p_first,float *p_last,int *draws){\n int active_index=(turn%NB)*B;\n int k=0;*draws=0;\n for(int step=1;step<=maxsteps;step++){\n  unsigned long long blocks=do_step(h,z,q,turn,0);\n  if(blocks!=(unsigned long long)q)return -1;\n  float p=hazard_probability(h,active_index); // AFTER F(h) updated h\n  if(step==1)*p_first=p;\n  *p_last=p;\n  double u=(double)r32()/4294967296.0;(*draws)++;k=step;\n  if(u<(double)p)break;\n }\n return k;\n}\nstatic int control_pair(int q,int turn,int maxsteps){\n // Same post-F uniform draw 0.5, opposite state signs; fixed z=0, no pre-sampled K.\n if(q!=1||maxsteps!=8){puts("PAIR required_q=1 required_maxsteps=8 status=FAIL");return 3;}\n float p1[2]={0,0},plast[2]={0,0};int ks[2]={0,0};\n for(int sign=0;sign<2;sign++){\n  float h[D]={0},z[D]={0};h[(turn%NB)*B]=sign==0?1.0f:-1.0f;\n  for(int k=1;k<=maxsteps;k++){\n   if(do_step(h,z,q,turn,0)!=(unsigned long long)q)return 3;\n   float p=hazard_probability(h,(turn%NB)*B);\n   if(k==1)p1[sign]=p;\n   plast[sign]=p;\n   ks[sign]=k;\n   // forced controlled uniform draw for each AFTER-step hazard decision\n   if(.5f<p)break;\n  }\n }\n int ok=ks[0]==1&&ks[1]==8&&p1[0]>.5f&&p1[1]<.5f;\n printf("STATE_CAUSAL_PAIR same_draw=0.5 plus_K=%d minus_K=%d plus_p1=%.6f minus_p1=%.6f minus_p_last=%.6f post_step_only=YES status=%s\\n",\n  ks[0],ks[1],p1[0],p1[1],plast[1],ok?"PASS":"FAIL");\n return ok?0:4;\n}\nstatic int trace_run(int q,int turn,int maxsteps,uint32_t seed){\n float h[D],z[D];init_hz(h,z);prng=seed;\n uint64_t dh=1469598103934665603ull;unsigned long long ksum=0;int drawsum=0;\n char ks[256]={0};\n for(int e=0;e<16;e++){\n  for(int i=0;i<D;i++)z[i]=.012f*(float)(((i+e)%11)-5);\n  float a=0,b=0;int nd=0;\n  int k=execute_turn(h,z,q,turn,maxsteps,&a,&b,&nd);\n  if(k<1||k>maxsteps||nd!=k)return 5;\n  char tmp[16];snprintf(tmp,sizeof(tmp),"%s%d",e?",":"",k);strcat(ks,tmp);\n  dh=digest(dh,h,k);ksum+=k;drawsum+=nd;\n }\n printf("TRACE q=%d maxsteps=%d n_events=16 K_sequence=%s sumK=%llu draw_count=%d total_F_MAC=%llu digest=%016llx status=PASS\\n",\n  q,maxsteps,ks,ksum,drawsum,ksum*(unsigned long long)q*BM,(unsigned long long)dh);\n return 0;\n}\nstatic int benchmark(int q,int turn,int maxsteps,uint32_t seed,double seconds){\n float h[D],z[D];init_hz(h,z);prng=seed;\n unsigned long long n=0,sumk=0,blocks=0;unsigned int ks[9]={0};\n int drawsum=0,kmin=9,kmax=0;double p_first=0,p_last=0;\n double w0=clk(CLOCK_MONOTONIC),c0=clk(CLOCK_PROCESS_CPUTIME_ID);\n do{\n  for(int i=0;i<D;i++)z[i]=.012f*(float)(((i+(int)(n%11))%11)-5);\n  float p1=0,p2=0;int draws=0;\n  int k=execute_turn(h,z,q,turn,maxsteps,&p1,&p2,&draws);\n  if(k<1||k>maxsteps||draws!=k)return 5;\n  if(n==0)p_first=p1;\n  p_last=p2;ks[k]++;sumk+=k;drawsum+=draws;blocks+=q*k;\n  if(k<kmin)kmin=k;if(k>kmax)kmax=k;\n  n++;\n }while(clk(CLOCK_MONOTONIC)-w0<seconds && n<3000000ull);\n double wall=clk(CLOCK_MONOTONIC)-w0,cpu=clk(CLOCK_PROCESS_CPUTIME_ID)-c0;\n if(n==0||drawsum!=(int)sumk)return 6;\n uint64_t dh=digest(1469598103934665603ull,h,(int)(sumk&0xff));\n printf("BENCH q=%d maxsteps=%d events=%llu K_min=%d K_max=%d K_mean=%.5f hazard_calls=%d F_blocks=%llu total_F_MAC=%llu avg_wall_ms=%.6f avg_cpu_ms=%.6f first_p=%.6f last_p=%.6f h_digest=%016llx status=PASS\\n",\n  q,maxsteps,n,kmin,kmax,(double)sumk/n,drawsum,blocks,blocks*BM,wall*1000./n,cpu*1000./n,p_first,p_last,(unsigned long long)dh);\n return 0;\n}\nint main(int argc,char **argv){\n if(argc!=7){fprintf(stderr,"usage: fixture bench|trace|pair|abort q turn budget_mac seed duration_s\\n");return 2;}\n const char *mode=argv[1];int q=atoi(argv[2]),turn=atoi(argv[3]);\n unsigned long long budget=strtoull(argv[4],NULL,10);\n uint32_t seed=(uint32_t)strtoul(argv[5],NULL,10);double dur=atof(argv[6]);\n if((strcmp(mode,"bench")&&strcmp(mode,"trace")&&strcmp(mode,"pair")&&strcmp(mode,"abort"))||turn<0||turn>=8||!seed||dur<.01||dur>1.5)return 2;\n if(q<1||q>8||budget<(unsigned long long)q*BM){\n  printf("BUDGET_ABORT budget_F_MAC=%llu q=%d F_invocations=0 hazard_calls=0 state_untouched=YES status=PASS\\n",budget,q);\n  return 0;\n }\n int maxsteps=(int)(budget/((unsigned long long)q*BM));if(maxsteps>8)maxsteps=8;\n if(maxsteps<1)return 3;\n initialize();if(!mask_contract(q,turn))return 4;\n if(!strcmp(mode,"pair"))return control_pair(q,turn,maxsteps);\n if(!strcmp(mode,"trace"))return trace_run(q,turn,maxsteps,seed);\n if(!strcmp(mode,"bench"))return benchmark(q,turn,maxsteps,seed,dur);\n fprintf(stderr,"abort mode budget unexpectedly feasible\\n");return 4;\n}\n'

class Xorshift32:
    def __init__(self,seed):
        assert 0<seed<2**32
        self.s=seed;self.draws=0
    def random(self):
        x=self.s
        x^=(x<<13)&0xffffffff;x^=x>>17;x^=(x<<5)&0xffffffff
        self.s=x&0xffffffff;self.draws+=1
        return self.s/4294967296.0

def candidate_logits(turn):
    return tuple(.65*math.sin((j+1)*.7+turn*.11)+.35*math.cos(j*1.3) for j in range(8))

def probabilities(feasible,turn):
    l=candidate_logits(turn);scores=[sum(l[(j+turn)%8] for j in range(q))/math.sqrt(q) for q in feasible]
    mx=max(scores);es=[math.exp(x-mx) for x in scores];total=sum(es)
    out=[EPS/len(feasible)+(1-EPS)*p/total for p in es]
    assert math.isclose(sum(out),1.0,abs_tol=1e-12)
    return out

def select_prefix(budget,turn,rng):
    feasible=tuple(range(1,min(8,budget//BM)+1))
    if not feasible:return None,(),0
    probs=probabilities(feasible,turn);draw=rng.random();v=0.;q=feasible[-1]
    for prefix,p in zip(feasible,probs):
        v+=p
        if draw<v:q=prefix;break
    kcap=min(8,budget//(q*BM))
    assert kcap>=1
    return q,probs,kcap

def parse_int(path):
    try:return int(Path(path).read_text().strip())
    except (ValueError,OSError):return None

def telemetry():
    try:mem=int(next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')).split()[1])
    except (OSError,StopIteration,ValueError,IndexError):mem=None
    return parse_int('/sys/class/power_supply/battery/capacity'),parse_int('/sys/class/power_supply/battery/temp'),mem

def safety(smoke):
    if smoke:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100<=t<=800:return 'INVALID_TELEMETRY'
    if b<40:return 'BATTERY_BELOW_40'
    if t>=375:return 'BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'MEMAVAILABLE_BELOW_400000_KB'
    return None

def compile_native(root):
    clang=shutil.which('clang')
    if not clang:raise RuntimeError('CLANG_NOT_FOUND')
    src=root/'after_step_hazard.c';exe=root/'after_step_hazard'
    src.write_text(C_SOURCE,encoding='utf-8')
    result=subprocess.run([clang,'-O3','-std=c11','-Wall','-Wextra',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=50)
    if result.returncode:raise RuntimeError('CLANG_FAILED '+result.stderr[-800:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def background_binary():
    exe=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not exe.exists() or not os.access(exe,os.X_OK):raise RuntimeError('BACKGROUND_S5_MISSING')
    p=subprocess.run([str(exe),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=9)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BACKGROUND_S5_CONTRACT_FAIL')
    return exe

def worker(exe,cancel,ready,result):
    vals=[];errors=[]
    try:
        while not cancel.is_set():
            p=subprocess.run([str(exe),'rank','full','0.70'],capture_output=True,text=True,timeout=9)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BASELINE_F_ERROR')
            match=re.search(r'estimated_F_GMAC_s=([.\d]+)',p.stdout)
            if not match:raise RuntimeError('NO_BACKGROUND_MEASUREMENT')
            vals.append(float(match[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=3)
    except BaseException as e:errors.append(str(e)[:160])
    try:result.put((os.getpid(),len(vals),statistics.mean(vals) if vals else None,min(vals) if vals else None,errors),timeout=3)
    except BaseException:pass

def mem_holder(mib,cancel,ready):
    try:
        data=bytearray(mib*MIB)
        for i in range(0,len(data),4096):data[i]=1
        ready.put(True,timeout=4)
        while not cancel.wait(.15):
            for i in range(0,len(data),262144):data[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def run_native(exe,mode,q,turn,budget,seed,dur=.20):
    p=subprocess.run([str(exe),mode,str(q),str(turn%8),str(budget),str(seed),f'{dur:.2f}'],capture_output=True,text=True,timeout=14)
    if p.returncode:raise RuntimeError('NATIVE_EXIT '+str(p.returncode)+' '+p.stdout[-280:]+' '+p.stderr[-280:])
    return p.stdout

def get_val(line,name):
    m=re.search(r'\b'+re.escape(name)+r'=([^\s]+)',line)
    if not m:raise RuntimeError('FIELD_MISSING '+name+' '+line[:180])
    return m.group(1)

def selftest(exe):
    x=run_native(exe,'abort',0,0,0,9,.05)
    if 'BUDGET_ABORT' not in x or 'F_invocations=0' not in x or 'hazard_calls=0' not in x:raise RuntimeError('ZERO_BUDGET_FAIL')
    pair=run_native(exe,'pair',1,0,8*BM,9,.05)
    if 'STATE_CAUSAL_PAIR' not in pair or 'plus_K=1 minus_K=8' not in pair or 'status=PASS' not in pair:raise RuntimeError('CAUSE_PAIR_FAIL '+pair[-320:])
    for q,kcap in [(1,8),(3,4),(8,8)]:
        a=run_native(exe,'trace',q,2,q*kcap*BM,0x34a86c2e,.05)
        b=run_native(exe,'trace',q,2,q*kcap*BM,0x34a86c2e,.05)
        if a!=b:raise RuntimeError('TRACE_REPLAY_NOT_EXACT')
        line=next((l for l in a.splitlines() if l.startswith('TRACE ')),None)
        if not line or get_val(line,'status')!='PASS':raise RuntimeError('TRACE_CONTRACT')
    return pair.strip().splitlines()[-1]

def stage(log,ctx,exe,bg,name,nworkers,smoke):
    cancel=ctx.Event();ready=ctx.Queue();result=ctx.Queue();rready=ctx.Queue()
    workers=[];holder=None;start=time.monotonic();errors=0;reason=None;completed=0;aborts=0;first=0
    measurements=[];plans=[];tracechecks=0;pairchecks=0;goodworkers=0
    seed=0x1156e01f+nworkers;chooser=Xorshift32(seed)
    ntrials=6 if smoke else 24
    try:
        holder=ctx.Process(target=mem_holder,args=(32,cancel,rready));holder.start()
        if rready.get(timeout=9) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(nworkers):
            w=ctx.Process(target=worker,args=(bg,cancel,ready,result));w.start();workers.append(w)
        if len({ready.get(timeout=24) for _ in workers})!=nworkers:raise RuntimeError('WORKERS_NOT_READY')
        log(f'STAGE_BEGIN name={name} S5_workers={nworkers} RAM_MiB=32 trials={ntrials} no_idle_phase=YES')
        # Under load, prove same uniform sample has different K because F updated h differently.
        pair=run_native(exe,'pair',1,nworkers,8*BM,0x41a9,.05)
        if 'plus_K=1 minus_K=8' not in pair or 'status=PASS' not in pair:raise RuntimeError('STATE_DEPENDENCE_NOT_PROVEN')
        log('STATE_CONTROL stage='+name+' '+next(l for l in pair.splitlines() if l.startswith('STATE_CAUSAL_PAIR ')))
        pairchecks+=1
        for i in range(ntrials):
            if why:=safety(smoke):reason=why;break
            # Mix tight budgets, broad budgets, and empty budgets.
            units=BUDGET_UNITS[(i*5+i//3)%len(BUDGET_UNITS)]
            if i in (0,11,20):units=0
            turn=i
            before=chooser.draws
            q,p,kcap=select_prefix(units*BM,turn,chooser)
            plans.append((units,turn,q,kcap,before,chooser.draws))
            if q is None:
                aborts+=1
                out=run_native(exe,'abort',0,turn,0,0x54ed,.05)
                if 'BUDGET_ABORT' not in out or 'F_invocations=0' not in out:raise RuntimeError('ABORT_INVOKED_F')
                log(f'ADMISSION stage={name} trial={i} status=BUDGET_ABORT no_F=YES budget_F_MAC=0 rng_draws={chooser.draws-before}')
                continue
            budget=units*BM;native_seed=(0x63ac7181 + i*977 + nworkers*31)&0xffffffff
            if i%6==2:
                a=run_native(exe,'trace',q,turn,budget,native_seed,.05)
                b=run_native(exe,'trace',q,turn,budget,native_seed,.05)
                if a!=b:raise RuntimeError('STATEFUL_TRACE_REPLAY_MISMATCH')
                t=next(l for l in a.splitlines() if l.startswith('TRACE '))
                tracechecks+=1
                log('HAZARD_REPLAY stage='+name+' trial='+str(i)+' '+t)
            out=run_native(exe,'bench',q,turn,budget,native_seed,.20 if smoke else .26)
            if 'MASK_CONTRACT early_equals_late=YES inactive_preserved=YES' not in out:raise RuntimeError('MASK_STATE_CONTRACT_FAIL')
            line=next((l for l in out.splitlines() if l.startswith('BENCH ')),None)
            if not line or get_val(line,'status')!='PASS':raise RuntimeError('BENCH_UNAVAILABLE '+out[-200:])
            events=int(get_val(line,'events'));km=float(get_val(line,'K_mean'));kmin=int(get_val(line,'K_min'));kmax=int(get_val(line,'K_max'))
            calls=int(get_val(line,'hazard_calls'));blocks=int(get_val(line,'F_blocks'));mac=int(get_val(line,'total_F_MAC'))
            if not (1<=kmin<=km<=kmax<=kcap and blocks==q*calls and mac==blocks*BM and calls>=events):raise RuntimeError('AFTER_STEP_LEDGER_FAIL')
            if blocks>events*q*kcap or mac>events*budget:raise RuntimeError('HAZARD_MAC_BUDGET_OVERFLOW')
            wall=float(get_val(line,'avg_wall_ms'));cpu=float(get_val(line,'avg_cpu_ms'))
            measurements.append((wall,cpu,q,kcap,km))
            completed+=1
            if i%4==0 or i==ntrials-1:
                log(f'AFTER_STEP stage={name} trial={i} q={q} maxK={kcap} events={events} actual_mean_K={km:.3f} '
                    f'hazard_decisions_after_F={calls} actual_F_MAC={mac} max_F_MAC={events*budget} '
                    f'wall_ms_per_event={wall:.4f} cpu_ms_per_event={cpu:.4f} result=PASS')
        # Exact replay of PREFIX decisions (K is not sampled in Python).
        generator=Xorshift32(seed)
        for units,turn,q,kcap,before,after in plans:
            if generator.draws!=before:raise RuntimeError('PREFIX_RNG_OFFSET_FAIL')
            qq,_,kk=select_prefix(units*BM,turn,generator)
            if (q,kcap)!=(qq,kk) or generator.draws!=after:raise RuntimeError('PREFIX_REPLAY_MISMATCH')
        log(f'PREFIX_REPLAY stage={name} plans={len(plans)} exact=YES rng_draws={generator.draws}')
        floor=4 if smoke else (24 if nworkers==2 else 30)
        while time.monotonic()-start<floor:
            if why:=safety(smoke):reason=why;break
            time.sleep(.15)
    except BaseException as e:
        errors+=1;log(f'STAGE_ERROR stage={name} {type(e).__name__} {str(e)[:250]}')
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
                pid,runs,mean,low,errs=result.get(timeout=2)
                log(f'S5_WORKER stage={name} pid={pid} runs={runs} mean_GMAC_s={mean} min_GMAC_s={low} errors={errs}')
                if runs>=1 and not errs:goodworkers+=1
                else:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={name} MISSING_REPORT')
        for qobj in (ready,result,rready):
            qobj.cancel_join_thread();qobj.close()
    status='SAFETY_ABORT' if reason else ('COMPLETE' if errors==0 and len(plans)==ntrials and goodworkers==nworkers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={name} status={status} planned={len(plans)}/{ntrials} native_exec={completed} '
        f'budget_aborts={aborts} hazard_replays={tracechecks} state_causal_pairs={pairchecks} '
        f'workers_ok={goodworkers}/{nworkers} errors={errors} '
        f'median_wall_ms={statistics.median(v[0] for v in measurements) if measurements else None} '
        f'wall_max_ms={max(v[0] for v in measurements) if measurements else None} '
        f'safety_reason={reason or "-"}')
    log(f'STAGE_TELEMETRY stage={name} battery={telemetry()[0]} temp_deciC={telemetry()[1]} MemAvailable_kB={telemetry()[2]}')
    return status,completed,aborts,tracechecks

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host-smoke',action='store_true',help='Host-only integration check; never use on phone')
    args=ap.parse_args()
    root=Path.home();downloads=root/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=root
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/f'UNO_A52_R41_S6_AFTER_STEP_HAZARD_V12_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- R4.1 STATE-DEPENDENT AFTER-STEP HAZARD ON REAL ARM S5 '+VERSION)
            log('After native F updates h, candidate Bernoulli hazard p=sigmoid(4*h[active_first]) draws PRNG; cannot pre-sample K. C256R32, K<=8.')
            log('State carries across events in each native run. Prefix q uses synthetic epsilon-softmax, not learned W_M. Controlled +/- state pair uses same forced u=0.5.')
            log('F-only MAC budget; NOT complete turn admission or calibrated hazard. Not production learned model, Android Binder, OS actions, real user STOP, auth, hardware power-cut or energy.')
            log('Continuous 2/4 native S5 background workers + touched 32MiB RAM per stage. No zero-load stage. Platform guards unchanged.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if reason:=safety(args.host_smoke):
                log(f'RESULT SAFETY_SKIP {reason}');log('REPORT '+str(report));return 3
            bg=background_binary();log('VERIFIED_BACKGROUND_S5 '+str(bg))
            work=root/'uno_a52_r41_s6_afterstep_v12'/stamp
            work.mkdir(parents=True,exist_ok=False,mode=0o700)
            exe,sha=compile_native(work);log(f'COMPILED_NATIVE_HAZARD {exe} source_sha256={sha}')
            log('SELFTEST '+selftest(exe))
            ctx=mp.get_context('fork');tot=aborts=replays=complete=0
            for name,workers in [('S5x2_RAM32',2),('S5x4_RAM32',4)]:
                if reason:=safety(args.host_smoke):
                    log(f'RESULT SAFETY_ABORT_BEFORE_STAGE stage={name} reason={reason}');log('REPORT '+str(report));return 3
                status,n,a,r=stage(log,ctx,exe,bg,name,workers,args.host_smoke)
                tot+=n;aborts+=a;replays+=r;complete+=(status=='COMPLETE')
                if status!='COMPLETE':
                    log(f'RESULT {status} complete_stages={complete}/2 native_exec={tot} budget_aborts={aborts}')
                    log('REPORT '+str(report));return 3 if status=='SAFETY_ABORT' else 2
            log(f'RESULT COMPLETE_AFTER_STEP_HAZARD_LAB stages={complete}/2 native_exec={tot} budget_aborts={aborts} replay_checks={replays}')
            log('LIMIT: post-F hazard is SYNTHETIC and uses a controlled scalar readout, not trained state-dependent neural hazard or energy-validated policy; no Android trust boundary.')
            log('REPORT '+str(report));return 0
        except KeyboardInterrupt:
            log('RESULT USER_INTERRUPTED');log('REPORT '+str(report));return 130
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:260]}')
            log('TRACE '+traceback.format_exc().splitlines()[-1]);log('REPORT '+str(report));return 2

if __name__=='__main__':sys.exit(main())
