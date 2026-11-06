#!/usr/bin/env python3
"""UNO / UNOVYRA R4.1 S6 multi-resource precharge isolated Android A52 lab.
Uses native C256R32 FP32 F and *synthetic* encoder, memory scan, control and head.
Admission is additive F/aux MAC, a synthetic workspace allocation, tokens and
monotonic deadline observation. NOT calibrated real-time or full phone PSS.
OWNER_APPROVED_PRECODE = FALSE; NO production code or real Android actions.
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

VERSION = 'UNO_R41_A52_S6_MULTI_RESOURCE_ADMISSION_LOADED_V13'
BM=28672
OTHER_MAC=8192+16384+64+8192
WORKSPACE=64*256*4
MIB=1048576
C_SOURCE = '\n#define _POSIX_C_SOURCE 200809L\n#include <stdio.h>\n#include <stdlib.h>\n#include <stdint.h>\n#include <string.h>\n#include <math.h>\n#include <time.h>\n#define D 256\n#define B 32\n#define NB 8\n#define U 128\n#define R 32\n#define BM 28672ull\nstatic float A2[NB][R][D], A1[NB][U][R], C2[NB][R][D], C1[NB][U][R], BB[NB][B][U];\nstatic volatile double discard_sink=0, output_sink=0;\nstatic uint32_t prng=0x3acd71b9u;\nstatic uint32_t r32(void){prng^=prng<<13;prng^=prng>>17;prng^=prng<<5;return prng;}\nstatic float sval(void){return ((float)(r32()%20001)/10000.f-1.f)*.008f;}\nstatic double clk(clockid_t id){struct timespec ts;clock_gettime(id,&ts);return ts.tv_sec+ts.tv_nsec*1e-9;}\nstatic void initialize(void){\n for(int j=0;j<NB;j++){\n  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A2[j][r][i]=sval();C2[j][r][i]=sval();}\n  for(int x=0;x<U;x++)for(int r=0;r<R;r++){A1[j][x][r]=sval();C1[j][x][r]=sval();}\n  for(int b=0;b<B;b++)for(int x=0;x<U;x++)BB[j][b][x]=sval();\n }\n}\nstatic void init_hz(float h[D],float z[D]){\n for(int i=0;i<D;i++){h[i]=.02f*(float)((i%17)-8);z[i]=.015f*(float)((i%11)-5);}\n}\nstatic int selected(int j,int q,int turn){return (j-turn+NB)%NB<q;}\nstatic unsigned long long do_step(float h[D],const float z[D],int q,int turn,int late){\n float next[D],a[R],c[R],u[U],v[B];unsigned long long done=0;\n memcpy(next,h,sizeof(next));\n for(int j=0;j<NB;j++){\n  int active=selected(j,q,turn);\n  if(!active&&!late)continue;\n  done++;\n  for(int r=0;r<R;r++){\n   float sa=0,sc=0;\n   for(int i=0;i<D;i++){sa+=A2[j][r][i]*h[i];sc+=C2[j][r][i]*z[i];}\n   a[r]=sa;c[r]=sc;\n  }\n  for(int x=0;x<U;x++){\n   float sa=0,sc=0;\n   for(int r=0;r<R;r++){sa+=A1[j][x][r]*a[r];sc+=C1[j][x][r]*c[r];}\n   u[x]=tanhf(sa+sc);\n  }\n  for(int b=0;b<B;b++){\n   float sv=0;for(int x=0;x<U;x++)sv+=BB[j][b][x]*u[x];\n   v[b]=tanhf(sv);\n  }\n  if(!active){discard_sink+=(double)v[j%B];continue;}\n  for(int b=0;b<B;b++)next[j*B+b]=.5f*h[j*B+b]+.5f*v[b];\n }\n memcpy(h,next,sizeof(next));return done;\n}\n\nstatic unsigned long long tick_seed=0;\nstatic uint64_t digest(uint64_t hsh,const float *h,int k){\n  hsh ^= (uint64_t)k; hsh*=1099511628211ull;\n  for(int i=0;i<D;i+=17){uint32_t bits;memcpy(&bits,&h[i],4);hsh ^= bits;hsh*=1099511628211ull;}\n  return hsh;\n}\nstatic float hazard_probability(const float h[D],int active_index){\n  // DEMO STATE-DEPENDENT HAZARD: current h after native F step, not the initial h or pre-sampled K.\n  double x=4.0*(double)h[active_index];\n  return (float)(1.0/(1.0+exp(-x)));\n}\nstatic int mask_contract(int q,int turn){\n float h[D],z[D],x[D],y[D];init_hz(h,z);\n memcpy(x,h,sizeof(x));memcpy(y,h,sizeof(y));\n unsigned long long a=do_step(x,z,q,turn,0),b=do_step(y,z,q,turn,1);\n int same=memcmp(x,y,sizeof(x))==0,untouched=1;\n for(int j=0;j<NB;j++)if(!selected(j,q,turn))for(int i=j*B;i<(j+1)*B;i++)\n  if(h[i]!=x[i])untouched=0;\n printf("MASK_CONTRACT early_equals_late=%s inactive_preserved=%s early_blocks=%llu late_blocks=%llu status=%s\\n",\n   same?"YES":"NO",untouched?"YES":"NO",a,b,(same&&untouched&&a==(unsigned long long)q&&b==NB)?"PASS":"FAIL");\n return same&&untouched&&a==(unsigned long long)q&&b==NB;\n}\nstatic int execute_turn(float h[D],float z[D],int q,int turn,int maxsteps,float *p_first,float *p_last,int *draws){\n int active_index=(turn%NB)*B;\n int k=0;*draws=0;\n for(int step=1;step<=maxsteps;step++){\n  unsigned long long blocks=do_step(h,z,q,turn,0);\n  if(blocks!=(unsigned long long)q)return -1;\n  float p=hazard_probability(h,active_index); // AFTER F(h) updated h\n  if(step==1)*p_first=p;\n  *p_last=p;\n  double u=(double)r32()/4294967296.0;(*draws)++;k=step;\n  if(u<(double)p)break;\n }\n return k;\n}\nstatic int control_pair(int q,int turn,int maxsteps){\n // Same post-F uniform draw 0.5, opposite state signs; fixed z=0, no pre-sampled K.\n if(q!=1||maxsteps!=8){puts("PAIR required_q=1 required_maxsteps=8 status=FAIL");return 3;}\n float p1[2]={0,0},plast[2]={0,0};int ks[2]={0,0};\n for(int sign=0;sign<2;sign++){\n  float h[D]={0},z[D]={0};h[(turn%NB)*B]=sign==0?1.0f:-1.0f;\n  for(int k=1;k<=maxsteps;k++){\n   if(do_step(h,z,q,turn,0)!=(unsigned long long)q)return 3;\n   float p=hazard_probability(h,(turn%NB)*B);\n   if(k==1)p1[sign]=p;\n   plast[sign]=p;\n   ks[sign]=k;\n   // forced controlled uniform draw for each AFTER-step hazard decision\n   if(.5f<p)break;\n  }\n }\n int ok=ks[0]==1&&ks[1]==8&&p1[0]>.5f&&p1[1]<.5f;\n printf("STATE_CAUSAL_PAIR same_draw=0.5 plus_K=%d minus_K=%d plus_p1=%.6f minus_p1=%.6f minus_p_last=%.6f post_step_only=YES status=%s\\n",\n  ks[0],ks[1],p1[0],p1[1],plast[1],ok?"PASS":"FAIL");\n return ok?0:4;\n}\nstatic int trace_run(int q,int turn,int maxsteps,uint32_t seed){\n float h[D],z[D];init_hz(h,z);prng=seed;\n uint64_t dh=1469598103934665603ull;unsigned long long ksum=0;int drawsum=0;\n char ks[256]={0};\n for(int e=0;e<16;e++){\n  for(int i=0;i<D;i++)z[i]=.012f*(float)(((i+e)%11)-5);\n  float a=0,b=0;int nd=0;\n  int k=execute_turn(h,z,q,turn,maxsteps,&a,&b,&nd);\n  if(k<1||k>maxsteps||nd!=k)return 5;\n  char tmp[16];snprintf(tmp,sizeof(tmp),"%s%d",e?",":"",k);strcat(ks,tmp);\n  dh=digest(dh,h,k);ksum+=k;drawsum+=nd;\n }\n printf("TRACE q=%d maxsteps=%d n_events=16 K_sequence=%s sumK=%llu draw_count=%d total_F_MAC=%llu digest=%016llx status=PASS\\n",\n  q,maxsteps,ks,ksum,drawsum,ksum*(unsigned long long)q*BM,(unsigned long long)dh);\n return 0;\n}\nstatic int benchmark(int q,int turn,int maxsteps,uint32_t seed,double seconds){\n float h[D],z[D];init_hz(h,z);prng=seed;\n unsigned long long n=0,sumk=0,blocks=0;unsigned int ks[9]={0};\n int drawsum=0,kmin=9,kmax=0;double p_first=0,p_last=0;\n double w0=clk(CLOCK_MONOTONIC),c0=clk(CLOCK_PROCESS_CPUTIME_ID);\n do{\n  for(int i=0;i<D;i++)z[i]=.012f*(float)(((i+(int)(n%11))%11)-5);\n  float p1=0,p2=0;int draws=0;\n  int k=execute_turn(h,z,q,turn,maxsteps,&p1,&p2,&draws);\n  if(k<1||k>maxsteps||draws!=k)return 5;\n  if(n==0)p_first=p1;\n  p_last=p2;ks[k]++;sumk+=k;drawsum+=draws;blocks+=q*k;\n  if(k<kmin)kmin=k;if(k>kmax)kmax=k;\n  n++;\n }while(clk(CLOCK_MONOTONIC)-w0<seconds && n<3000000ull);\n double wall=clk(CLOCK_MONOTONIC)-w0,cpu=clk(CLOCK_PROCESS_CPUTIME_ID)-c0;\n if(n==0||drawsum!=(int)sumk)return 6;\n uint64_t dh=digest(1469598103934665603ull,h,(int)(sumk&0xff));\n printf("BENCH q=%d maxsteps=%d events=%llu K_min=%d K_max=%d K_mean=%.5f hazard_calls=%d F_blocks=%llu total_F_MAC=%llu avg_wall_ms=%.6f avg_cpu_ms=%.6f first_p=%.6f last_p=%.6f h_digest=%016llx status=PASS\\n",\n  q,maxsteps,n,kmin,kmax,(double)sumk/n,drawsum,blocks,blocks*BM,wall*1000./n,cpu*1000./n,p_first,p_last,(unsigned long long)dh);\n return 0;\n}\n\n#define ENCODER_MAC 8192ull\n#define MEMORY_MAC 16384ull\n#define CONTROL_MAC 64ull\n#define HEAD_MAC 8192ull\n#define OTHER_MAC (ENCODER_MAC + MEMORY_MAC + CONTROL_MAC + HEAD_MAC)\n#define MEM_ROWS 64\n#define WORKSPACE (MEM_ROWS*D*sizeof(float))\nstatic void encode(float z[D],const float *h){\n for(int row=0;row<32;row++){\n  float s=0;for(int i=0;i<D;i++)s+=A2[0][row][i]*h[i];\n  z[row]=tanhf(s);\n }\n}\nstatic void scan_memory(float z[D],const float h[D],const float *mem){\n double sum=0;\n for(int row=0;row<MEM_ROWS;row++){\n  float s=0;for(int i=0;i<D;i++)s+=mem[row*D+i]*h[i];\n  sum+=(double)s;\n }\n z[32]=(float)(sum/1000000.0);\n}\nstatic void control64(float z[D],const float h[D]){\n float v=0;\n for(int row=0;row<8;row++)for(int col=0;col<8;col++)v+=h[row*B+col]*z[(row+col)%D];\n z[33]=(float)tanh(v);\n}\nstatic void head32(const float h[D]){\n float s=0;\n for(int row=0;row<32;row++){\n  float a=0;for(int i=0;i<D;i++)a+=A2[0][row][i]*h[i];s+=tanhf(a);\n }\n output_sink+=(double)s;\n}\nstatic int cycle(const char *mode,int q,int turn,unsigned long long cap,size_t workspace_cap,int tokens,double deadline_ms,uint32_t seed){\n int good_mode= !strcmp(mode,"OK")||!strcmp(mode,"SINGLE_STEP")||!strcmp(mode,"MAC_ONLY")||!strcmp(mode,"WORKSPACE")||!strcmp(mode,"TOKENS")||!strcmp(mode,"TIME_ZERO")||!strcmp(mode,"TIME_OVERRUN")||!strcmp(mode,"INVALID_Q");\n if(!good_mode)return 2;\n int is_overrun=!strcmp(mode,"TIME_OVERRUN");\n int admitted=q>=1&&q<=NB&&cap>=OTHER_MAC+(unsigned long long)q*BM&&workspace_cap>=WORKSPACE&&tokens>=1&&deadline_ms>0;\n double wall0=clk(CLOCK_MONOTONIC),cpu0=clk(CLOCK_PROCESS_CPUTIME_ID);\n float h[D],z[D],shadow[D];init_hz(h,z);\n uint64_t old_digest=digest(1469598103934665603ull,h,0);\n unsigned long long charged_mac=0;unsigned long long F_blocks=0;\n int K=0,F_calls=0,head_calls=0,token_used=0,workspace_allocated=0;\n int maxsteps=0;const char*status="BUDGET_ABORT";\n float *mem=NULL;\n if(admitted){\n  maxsteps=(int)((cap-OTHER_MAC)/((unsigned long long)q*BM));if(maxsteps>8)maxsteps=8;\n  if(maxsteps<1){admitted=0;goto out;}\n  mem=malloc(WORKSPACE);\n  if(!mem){fprintf(stderr,"WORKSPACE_ALLOC_FAILED\\n");return 5;}\n  for(int i=0;i<MEM_ROWS*D;i++)mem[i]=.0003f*(float)((i%31)-15);\n  workspace_allocated=(int)WORKSPACE;\n  initialize();\n  memcpy(shadow,h,sizeof(h));prng=seed;\n  encode(z,shadow);charged_mac+=ENCODER_MAC;\n  scan_memory(z,shadow,mem);charged_mac+=MEMORY_MAC;\n  control64(z,shadow);charged_mac+=CONTROL_MAC;\n  int active_index=(turn%NB)*B;\n  for(int i=0;i<maxsteps;i++){\n   if(do_step(shadow,z,q,turn,0)!=(unsigned long long)q){status="INVARIANT_FAIL";goto out;}\n   K++;F_calls++;F_blocks+=q;charged_mac+=(unsigned long long)q*BM;\n   double p=hazard_probability(shadow,active_index);\n   double u=(double)r32()/4294967296.0;\n   if(u<p)break;\n  }\n  if(is_overrun){struct timespec ts={0,25000000L};nanosleep(&ts,NULL);}\n  if((clk(CLOCK_MONOTONIC)-wall0)*1000.0>deadline_ms){status="ABSTAIN_DEADLINE";goto out;}\n  head32(shadow);charged_mac+=HEAD_MAC;head_calls++;token_used++;\n  memcpy(h,shadow,sizeof(h));status="COMMITTED";\n }\n out:\n if(mem)free(mem);\n uint64_t final_digest=digest(1469598103934665603ull,h,0);\n int state_changed=old_digest!=final_digest;\n int good=(charged_mac<=cap && workspace_allocated<=(int)workspace_cap && token_used<=tokens &&\n  (!strcmp(status,"COMMITTED") ? (admitted&&K>=1&&head_calls==1&&token_used==1&&state_changed) :\n    (head_calls==0&&token_used==0&&!state_changed)) &&\n  (!admitted ? (F_calls==0&&charged_mac==0) : (F_calls==K)));\n printf("CYCLE mode=%s status=%s q=%d maxK=%d K=%d F_calls=%d F_blocks=%llu MAC_cap=%llu MAC_charged=%llu encoder_MAC=%llu memory_MAC=%llu control_MAC=%llu head_MAC=%llu workspace_cap=%zu allocated_workspace=%d token_cap=%d tokens=%d head_calls=%d beta_unchanged=%s state_unchanged=%s wall_ms=%.3f cpu_ms=%.3f admission=%s contract=%s\\n",\n mode,status,q,maxsteps,K,F_calls,F_blocks,cap,charged_mac,ENCODER_MAC,MEMORY_MAC,CONTROL_MAC,HEAD_MAC,workspace_cap,workspace_allocated,tokens,token_used,head_calls,head_calls==0?"YES":"NO",!state_changed?"YES":"NO",\n (clk(CLOCK_MONOTONIC)-wall0)*1000.,(clk(CLOCK_PROCESS_CPUTIME_ID)-cpu0)*1000.,admitted?"YES":"NO",good?"PASS":"FAIL");\n return good?0:4;\n}\nint main(int argc,char **argv){\n if(argc!=9){fprintf(stderr,"usage fixture MODE q turn mac_cap workspace_cap token_cap deadline_ms seed\\n");return 2;}\n const char *mode=argv[1];int q=atoi(argv[2]),turn=atoi(argv[3]);\n unsigned long long cap=strtoull(argv[4],NULL,10);\n size_t ws=(size_t)strtoull(argv[5],NULL,10);\n int tok=atoi(argv[6]);double dl=atof(argv[7]);uint32_t seed=(uint32_t)strtoul(argv[8],NULL,10);\n if(turn<0||turn>=NB||!seed||dl<0||dl>10000)return 2;\n return cycle(mode,q,turn,cap,ws,tok,dl,seed);\n}\n'

def get_field(line,key):
    m=re.search(r'\b'+re.escape(key)+r'=([^\s]+)',line)
    if not m:raise RuntimeError('MISSING_FIELD '+key+' '+line[:140])
    return m[1]

def parse_int(path):
    try:return int(Path(path).read_text().strip())
    except (ValueError,OSError):return None

def telemetry():
    try:mem=int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])
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

def compile_native(where):
    cc=shutil.which('clang')
    if cc is None:raise RuntimeError('CLANG_NOT_FOUND')
    src=where/'v13_resource_cycle.c';exe=where/'v13_resource_cycle';src.write_text(C_SOURCE,encoding='utf-8')
    p=subprocess.run([cc,'-O3','-std=c11','-Wall','-Wextra',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=50)
    if p.returncode:raise RuntimeError('C_BUILD_FAILED '+p.stderr[-900:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def verify_background():
    exe=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not exe.is_file() or not os.access(exe,os.X_OK):raise RuntimeError('BACKGROUND_S5_NOT_FOUND')
    p=subprocess.run([str(exe),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=9)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('BACKGROUND_NATIVE_NOT_VERIFIED')
    return exe

def s5_worker(exe,stop,ready,results):
    vals=[];errors=[]
    try:
        while not stop.is_set():
            p=subprocess.run([str(exe),'rank','full','0.70'],capture_output=True,text=True,timeout=9)
            if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',p.stdout):raise RuntimeError('S5_EXEC_FAILED')
            m=re.search(r'estimated_F_GMAC_s=([\d.]+)',p.stdout)
            if not m:raise RuntimeError('GMAC_S_NOT_FOUND')
            vals.append(float(m[1]))
            if len(vals)==1:ready.put(os.getpid(),timeout=3)
    except BaseException as e:errors.append(str(e)[:200])
    try:results.put((os.getpid(),len(vals),statistics.mean(vals) if vals else 0.,min(vals) if vals else 0.,errors),timeout=3)
    except BaseException:pass

def hold_ram(mib,stop,ready):
    try:
        buf=bytearray(mib*MIB)
        for i in range(0,len(buf),4096):buf[i]=1
        ready.put(True,timeout=5)
        while not stop.wait(.12):
            for i in range(0,len(buf),262144):buf[i]^=1
    except BaseException:
        try:ready.put(False,timeout=2)
        except BaseException:pass

def fixture_case(exe,mode,q,turn,mac,ws,tokens,deadline,seed):
    p=subprocess.run([str(exe),mode,str(q),str(turn%8),str(mac),str(ws),str(tokens),str(deadline),str(seed)],capture_output=True,text=True,timeout=12)
    if p.returncode:raise RuntimeError('NATIVE_FAILED '+str(p.returncode)+' '+p.stdout[-400:]+' '+p.stderr[-220:])
    line=next((x for x in p.stdout.splitlines() if x.startswith('CYCLE ')),None)
    if not line or get_field(line,'contract')!='PASS':raise RuntimeError('NATIVE_CONTRACT_FAIL '+p.stdout[-400:])
    return line

MODES=('OK','SINGLE_STEP','MAC_ONLY','WORKSPACE','TOKENS','TIME_ZERO','TIME_OVERRUN','INVALID_Q')
EXPECT={'OK':'COMMITTED','SINGLE_STEP':'COMMITTED',
        'MAC_ONLY':'BUDGET_ABORT','WORKSPACE':'BUDGET_ABORT','TOKENS':'BUDGET_ABORT',
        'TIME_ZERO':'BUDGET_ABORT','TIME_OVERRUN':'ABSTAIN_DEADLINE','INVALID_Q':'BUDGET_ABORT'}

def configs(mode,q):
    cap=OTHER_MAC+8*q*BM;ws=WORKSPACE;tokens=1;deadline=5000
    if mode=='SINGLE_STEP':cap=OTHER_MAC+q*BM
    if mode=='MAC_ONLY':cap=q*BM
    if mode=='WORKSPACE':ws=WORKSPACE-1
    if mode=='TOKENS':tokens=0
    if mode=='TIME_ZERO':deadline=0
    if mode=='TIME_OVERRUN':deadline=2
    if mode=='INVALID_Q':q=0
    return q,cap,ws,tokens,deadline

def verify_case(line,mode,q,mac,workspace,tokens):
    state=get_field(line,'status');f_calls=int(get_field(line,'F_calls'))
    steps=int(get_field(line,'K'));charged=int(get_field(line,'MAC_charged'))
    head=int(get_field(line,'head_calls'));maxK=int(get_field(line,'maxK'))
    spent=int(get_field(line,'tokens'));alloc=int(get_field(line,'allocated_workspace'))
    if state!=EXPECT[mode]:raise RuntimeError('UNEXPECTED_STATUS mode='+mode+' '+line)
    if charged>mac or spent>tokens or alloc>workspace:raise RuntimeError('RESOURCE_CAP_OVERFLOW '+line)
    if int(get_field(line,'F_blocks'))!=q*steps or f_calls!=steps:raise RuntimeError('F_BLOCK_LEDGER '+line)
    if mode in ('OK','SINGLE_STEP'):
        if not (1<=steps<=maxK and head==1 and spent==1 and get_field(line,'state_unchanged')=='NO'):
            raise RuntimeError('ADMITTED_NO_COMMIT '+line)
        if mode=='SINGLE_STEP' and steps!=1:raise RuntimeError('UNEXPECTED_SECOND_STEP '+line)
    elif mode=='TIME_OVERRUN':
        if not (steps>=1 and head==0 and get_field(line,'state_unchanged')=='YES'):
            raise RuntimeError('DEADLINE_ABORT_MUST_NOT_COMMIT '+line)
    else:
        if not (f_calls==0 and head==0 and spent==0 and get_field(line,'state_unchanged')=='YES'):
            raise RuntimeError('DENIED_MODE_DID_WORK '+line)
    if charged != (OTHER_MAC-8192)+head*8192 + int(get_field(line,'F_blocks'))*BM and f_calls>0:
        raise RuntimeError('CYCLE_MAC_ACCOUNTING_ERROR '+line)
    return state,steps,float(get_field(line,'wall_ms'))

def single_stage(log,ctx,exe,bg,workers,smoke,inject_abort=False):
    label=f'S5x{workers}_RAM32';count=8 if smoke else 16
    cancel=ctx.Event();ready=ctx.Queue();result=ctx.Queue();ram_ready=ctx.Queue()
    sons=[];holder=None;timings=[];completed=0;denied=0;overrun=0;errors=0;reason=None;good=0
    start=time.monotonic()
    try:
        holder=ctx.Process(target=hold_ram,args=(32,cancel,ram_ready));holder.start()
        if ram_ready.get(timeout=9) is not True:raise RuntimeError('MEM_HOLDER_FAIL')
        for _ in range(workers):
            proc=ctx.Process(target=s5_worker,args=(bg,cancel,ready,result));proc.start();sons.append(proc)
        if len({ready.get(timeout=25) for _ in sons})!=workers:raise RuntimeError('NATIVE_S5_NOT_STARTED')
        log(f'STAGE_BEGIN stage={label} native_S5_workers={workers} touched_RAM_MiB=32 cases={count}')
        for i in range(count):
            if why:=safety(smoke):reason=why;break
            if inject_abort and i>=3:reason='INJECTED_SAFETY_ABORT_HOST_ONLY';break
            mode=MODES[i%8];q=1+(i%4)
            qq,mac,ws,tok,dl=configs(mode,q)
            line=fixture_case(exe,mode,qq,i,mac,ws,tok,dl,0x119f551+i+workers)
            status,K,wall=verify_case(line,mode,qq,mac,ws,tok)
            completed+=1;timings.append(wall)
            if status=='BUDGET_ABORT':denied+=1
            if status=='ABSTAIN_DEADLINE':overrun+=1
            log(f'CASE stage={label} rep={i//8+1} {line}')
        floor=3 if smoke else (24 if workers==2 else 30)
        while not reason and time.monotonic()-start<floor:
            if why:=safety(smoke):reason=why;break
            time.sleep(.15)
    except BaseException as e:
        errors+=1;log(f'STAGE_ERROR stage={label} {type(e).__name__}: {str(e)[:400]}')
    finally:
        cancel.set()
        for son in sons:
            son.join(5)
            if son.is_alive():son.kill();son.join(2)
        if holder:
            holder.join(3)
            if holder.is_alive():holder.kill();holder.join(2)
        for _ in sons:
            try:
                pid,runs,mean,mn,errs=result.get(timeout=2)
                log(f'S5_WORKER stage={label} pid={pid} native_runs={runs} mean_GMAC_s={mean:.5f} min_GMAC_s={mn:.5f} errors={errs}')
                if runs>=1 and not errs:good+=1
                else:errors+=1
            except queue.Empty:
                errors+=1;log(f'S5_WORKER stage={label} MISSING_REPORT')
        for item in (ready,result,ram_ready):item.cancel_join_thread();item.close()
    status='SAFETY_ABORT' if reason else ('COMPLETE' if completed==count and errors==0 and good==workers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={label} status={status} cases={completed}/{count} failures={errors} '
        f'budget_denials={denied} deadline_abstains={overrun} workers_ok={good}/{workers} '
        f'wall_median_ms={statistics.median(timings) if timings else None} '
        f'wall_max_ms={max(timings) if timings else None} safety_reason={reason or "-"}')
    log(f'STAGE_TELEMETRY stage={label} battery={telemetry()[0]} temp_deciC={telemetry()[1]} MemAvailable_kB={telemetry()[2]}')
    return status,completed,denied,overrun

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='Linux-only quick test, not for A52')
    ap.add_argument('--inject-host-abort',action='store_true',help='Only with --host-smoke')
    args=ap.parse_args()
    if args.inject_host_abort and not args.host_smoke:raise SystemExit('INJECTION_REQUIRES_HOST_SMOKE')
    root=Path.home();downloads=root/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=root
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f');report=downloads/f'UNO_A52_R41_S6_MULTI_RESOURCE_ADMISSION_V13_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- S6 FOUR RESOURCE GATES + NATIVE F CYCLE UNDER S5 LOAD '+VERSION)
            log('Isolated synthetic cycle: encoder 8192 MAC; memory scan 16384 MAC; control 64 MAC; head 8192 MAC; F 28672 MAC/block/step.')
            log('Resources: reserved aggregate MAC, 65536-byte native workspace segment, synthetic token quota, measured monotonic deadline check.')
            log('Admission checks all resources BEFORE encoder/F. Interrupted turns do not commit h or beta; negative TIME_OVERRUN tests no hard deadline guarantee.')
            log('Only 65536-byte explicit workspace allocation is tracked, NOT peak RSS/Android memory; no DSP, tokenizer, audio, IO, readback or licensed data.')
            log('Real native C256R32 FP32 F + synthetic ancillary kernels under 2/4 native S5 background workers and 32 MiB touched RAM.')
            log('LAB ONLY: no trained weights, production policy, owner authorization, native Android STOP, real OS actions, energy or hard real-time promise.')
            log('OWNER_APPROVED_PRECODE = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if why:=safety(args.host_smoke):log(f'RESULT SAFETY_SKIP {why}\nREPORT {report}');return 3
            bg=verify_background();log('VERIFIED_BACKGROUND_S5 '+str(bg))
            folder=root/'uno_a52_r41_s6_resource_admission_v13'/stamp;folder.mkdir(parents=True,exist_ok=False)
            exe,sha=compile_native(folder);log(f'COMPILED_NATIVE_CYCLE {exe} source_sha256={sha}')
            for mode in MODES:
                q=2
                qq,mac,ws,tok,dl=configs(mode,q)
                line=fixture_case(exe,mode,qq,1,mac,ws,tok,dl,6543)
                verify_case(line,mode,qq,mac,ws,tok)
            log('SELFTEST_PASS modes=8 admitted=2 denied=5 deadline_negative=1')
            ctx=mp.get_context('fork')
            a=single_stage(log,ctx,exe,bg,2,args.host_smoke,args.inject_host_abort)
            if a[0]!='COMPLETE':log(f'RESULT {a[0]} stage=S5x2 partial_cases={a[1]}');return 3
            b=single_stage(log,ctx,exe,bg,4,args.host_smoke)
            if b[0]!='COMPLETE':log(f'RESULT {b[0]} stage=S5x4 partial_cases={b[1]}');return 3
            log(f'RESULT COMPLETE_SYNTHETIC_FULL_CYCLE_RESOURCE_LEDGER stages=2/2 cases={a[1]+b[1]} denied={a[2]+b[2]} deliberate_deadline_abstains={a[3]+b[3]}')
            log('LIMIT: counted MAC excludes uncounted scalar operations and Android costs; 65536-byte workspace != peak RSS; deadline is detection not guaranteed upper latency.')
            log('LIMIT: credit is pre-reserved for permitted K but the synthetic ancillary heads/data are not trained UNO perception or memories.')
            return 0
        except BaseException as e:
            log(f'RESULT ERROR {type(e).__name__}: {str(e)[:600]}');log('TRACE '+traceback.format_exc()[-900:]);return 2
        finally:log('REPORT '+str(report))

if __name__=='__main__':sys.exit(main())
