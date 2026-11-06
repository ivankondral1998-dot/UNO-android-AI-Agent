#!/usr/bin/env python3
"""UNO R4.1 §4/§11 PRECODE S4 semantic versus exact-evidence boundary lab.
No real owner data, real Android permissions or model training.
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
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_SEMANTIC_EXACT_BOUNDARY_V16'
MIB=1048576
M=128
MODEL_A=hashlib.sha256(b'synthetic-memory-model-A').hexdigest()
MODEL_B=hashlib.sha256(b'synthetic-memory-model-B').hexdigest()
MODES=(
    'SINGLE_SEMANTIC_CONTEXT', 'C02_OPPOSITE_VALUES_COLLIDE',
    'EMPTY_ELIGIBLE_SET_ZERO', 'STABLE_LARGE_LOGITS', 'FP16_PAYLOAD_ROUNDTRIP',
    'MODEL_MISMATCH_QUARANTINE', 'BOOT_MISMATCH_QUARANTINE',
    'CONSENT_REVOKE_DENIES', 'PAYLOAD_INTEGRITY_UNKNOWN',
    'DECLARATION_NOT_EVIDENCE', 'HYPOTHESIS_NOT_EVIDENCE',
    'CONFLICT_NOT_RESOLVED_BY_SUMMARY', 'STALE_SLOT_GENERATION_UNKNOWN',
    'EXACT_RAW_BYTES_SEPARATE', 'MISSING_RAW_NOT_RECONSTRUCTED',
    'K1_EXACT_TRUNCATION', 'SAME_UID_SEMANTIC_POISON_NEGATIVE',
    'RECORD_ORDER_INVARIANCE',
)
C_SOURCE=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define M 128
#define D 256
#define R 32
#define B 32
#define MAX_RECORDS 16
#define F_MAC_PER_BLOCK (2*D*R+B*R)
static float A[2][R][D],C[2][R][D],W[2][B][R];
static uint32_t rng=0x71f38a4cu;
static uint32_t x32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static float randw(void){return ((float)(x32()%20001)/10000.f-1.f)*.003f;}
static void weights(void){
 for(int j=0;j<2;j++){
  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A[j][r][i]=randw();C[j][r][i]=randw();}
  for(int b=0;b<B;b++)for(int r=0;r<R;r++)W[j][b][r]=randw();
 }
}
static uint16_t read16(FILE *f){unsigned char b[2];if(fread(b,1,2,f)!=2){fprintf(stderr,"SHORT_HALF\n");exit(3);}return (uint16_t)b[0]|(uint16_t)b[1]<<8;}
static float half_to_float(uint16_t h){
 unsigned sign=(h>>15)&1,exp=(h>>10)&31,mant=h&1023;
 if(exp==31)return mant?NAN:(sign?-INFINITY:INFINITY);
 float v;
 if(exp==0)v=ldexpf((float)mant,-24);
 else v=ldexpf((float)(mant+1024),(int)exp-25);
 return sign?-v:v;
}
static unsigned long long fnv64(const float *v,int n){
 unsigned long long h=1469598103934665603ull;
 const unsigned char *p=(const unsigned char *)v;
 for(int i=0;i<n*(int)sizeof(float);i++){h^=p[i];h*=1099511628211ull;}
 return h;
}
int main(int argc,char **argv){
 if(argc!=2)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 unsigned char head[8];
 if(fread(head,1,8,f)!=8||memcmp(head,"S416",4)!=0){fclose(f);return 3;}
 int n=(int)head[4];if(n<0||n>MAX_RECORDS||head[5]!=1||head[6]||head[7]){fclose(f);return 3;}
 float T,q[M],z0[M],key[MAX_RECORDS][M],val[MAX_RECORDS][M];
 if(fread(&T,4,1,f)!=1||!isfinite(T)||T<=0){fclose(f);return 3;}
 if(fread(q,4,M,f)!=(size_t)M||fread(z0,4,M,f)!=(size_t)M){fclose(f);return 3;}
 for(int i=0;i<M;i++)if(!isfinite(q[i])||!isfinite(z0[i])){fclose(f);return 3;}
 for(int j=0;j<n;j++)for(int i=0;i<M;i++){key[j][i]=half_to_float(read16(f));if(!isfinite(key[j][i])){fclose(f);return 3;}}
 for(int j=0;j<n;j++)for(int i=0;i<M;i++){val[j][i]=half_to_float(read16(f));if(!isfinite(val[j][i])){fclose(f);return 3;}}
 if(fgetc(f)!=EOF){fclose(f);return 3;}fclose(f);
 float r[M]={0},z[M];double logits[MAX_RECORDS],max_logit=-INFINITY,denom=0.;
 for(int j=0;j<n;j++){
  double dot=0;for(int i=0;i<M;i++)dot+=(double)q[i]*(double)key[j][i];
  logits[j]=dot/(sqrt((double)M)*(double)T);
  if(!isfinite(logits[j]))return 3;
  if(logits[j]>max_logit)max_logit=logits[j];
 }
 for(int j=0;j<n;j++){logits[j]=exp(logits[j]-max_logit);denom+=logits[j];}
 if(n&&(!isfinite(denom)||denom<=0))return 3;
 for(int j=0;j<n;j++)for(int i=0;i<M;i++)r[i]+=(float)((logits[j]/denom)*(double)val[j][i]);
 for(int i=0;i<M;i++){z[i]=tanhf(z0[i]+r[i]);if(!isfinite(z[i]))return 3;}
 // Execute the same synthetic shared C256R32 F-family shape used by preceding labs.
 weights();float h[D],zz[D],next[D],aa[R],cc[R];
 for(int i=0;i<D;i++){h[i]=i<M?z[i]:0.f;zz[i]=i<M?z0[i]:0.f;}
 for(int j=0;j<2;j++){
  memcpy(next,h,sizeof(h));
  for(int rr=0;rr<R;rr++){
   float sa=0,sc=0;
   for(int i=0;i<D;i++){sa+=A[j][rr][i]*h[i];sc+=C[j][rr][i]*zz[i];}
   aa[rr]=sa;cc[rr]=sc;
  }
  for(int b=0;b<B;b++){
   float s=0;for(int rr=0;rr<R;rr++)s+=W[j][b][rr]*tanhf(aa[rr]+cc[rr]);
   next[j*B+b]=.7f*h[j*B+b]+.3f*tanhf(s);
  }
  memcpy(h,next,sizeof(h));
 }
 printf("NATIVE_SEMANTIC records=%d memory_dot_products=%d F_blocks=2 F_MAC=%d ",n,n*M,2*F_MAC_PER_BLOCK);
 printf("r0=%.9g r1=%.9g z0=%.9g state_digest=%016llx status=PASS\n",r[0],r[1],z[0],fnv64(h,D));
 printf("R=");for(int i=0;i<M;i++)printf(i==M-1?"%.9g\n":"%.9g,",r[i]);
 return 0;
}
'''

def number(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try:m=int(next(s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')).split()[1])
    except (OSError,StopIteration,ValueError,IndexError):m=None
    return number('/sys/class/power_supply/battery/capacity'),number('/sys/class/power_supply/battery/temp'),m

def safety(host):
    if host:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100<=t<=800:return 'SAFETY_TELEMETRY_UNAVAILABLE'
    if b<40:return 'SAFETY_BATTERY_BELOW_40_PERCENT'
    if t>=375:return 'SAFETY_BATTERY_TEMP_GE_37_5C'
    if m<400000:return 'SAFETY_MEMAVAILABLE_LT_400000_KB'
    return None

def native_s5():
    p=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_NOT_FOUND '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=12)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):raise RuntimeError('NATIVE_S5_PRECHECK_FAILED '+r.stdout[-200:])
    return p

def s5_worker(binary,stop,ready,out):
    values=[];errors=[]
    try:
        while not stop.is_set():
            x=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=12)
            if x.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',x.stdout):raise RuntimeError('NATIVE_S5_WORKER_FAILED')
            v=re.search(r'estimated_F_GMAC_s=([0-9.]+)',x.stdout)
            if v is None:raise RuntimeError('NATIVE_S5_METRICS_MISSING')
            values.append(float(v[1]))
            if len(values)==1:ready.put(os.getpid(),timeout=4)
    except BaseException as e:errors.append(str(e)[:150])
    try:out.put((os.getpid(),len(values),statistics.mean(values) if values else 0.,min(values) if values else 0.,errors),timeout=5)
    except BaseException:pass

def ram_worker(stop,ready):
    try:
        b=bytearray(32*MIB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(True,timeout=4)
        while not stop.wait(.15):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException:
        try:ready.put(False,timeout=3)
        except BaseException:pass

def compile_native(root):
    src=root/'v16_semantic.c';exe=root/'v16_semantic'
    src.write_text(C_SOURCE,encoding='utf-8')
    run=subprocess.run(['clang','-std=c11','-O2',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=45)
    if run.returncode:raise RuntimeError('NATIVE_CLANG_FAILED '+run.stderr[-600:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def conn(path):
    c=sqlite3.connect(str(path),timeout=6,isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL');c.execute('PRAGMA busy_timeout=5000')
    return c

def half_vec(data):return struct.pack('<128e',*data)
def unpack_half(data):return list(struct.unpack('<128e',data))
def vec(first=0.,second=0.):
    out=[0.]*M;out[0]=float(first);out[1]=float(second);return out

def add(c,slot,kind='VERIFIED_COMPLETION',raw=b'verified-source',key=None,val=None,model=MODEL_A,boot=1,consent=1,gen=1,source_gen=1,expiry=10_000,scope='owner',trusted=1):
    if key is None:key=vec(0.)
    if val is None:val=vec(0.5)
    kb=half_vec(key);vb=half_vec(val)
    c.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
       (slot,gen,gen,kind,raw,hashlib.sha256(raw).digest(),kb,vb,model,boot,consent,source_gen,expiry,scope,trusted,17,77,42,1))

def db_init(path):
    c=conn(path)
    c.execute('CREATE TABLE records(slot INTEGER PRIMARY KEY, generation INTEGER NOT NULL, expected_generation INTEGER NOT NULL, kind TEXT NOT NULL, raw BLOB NOT NULL, raw_sha BLOB NOT NULL, key_fp16 BLOB NOT NULL, value_fp16 BLOB NOT NULL, model TEXT NOT NULL, boot INTEGER NOT NULL, consent INTEGER NOT NULL, source_generation INTEGER NOT NULL, expiry INTEGER NOT NULL, scope TEXT NOT NULL, trusted_source INTEGER NOT NULL, source_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, time_scope INTEGER NOT NULL, raw_available INTEGER NOT NULL)')
    return c

def evaluate_store(c,requested_model=MODEL_A,boot=1,consent=1,scope='owner',now=100):
    # Scan ALL known rows, not top-k; any corrupt accessible row fails closed.
    rows=c.execute('SELECT slot,generation,expected_generation,kind,raw,raw_sha,key_fp16,value_fp16,model,boot,consent,source_generation,expiry,scope,trusted_source,source_id,subject_id,time_scope,raw_available FROM records ORDER BY slot,generation').fetchall()
    if consent!=1:return 'DENIED',[],len(rows),[]
    allow=[];meta=[]
    for row in rows:
        (slot,gen,expected,kind,raw,sha,k,v,model,b,ce,source_gen,expiry,sc,trusted,source_id,subject,t_scope,raw_available)=row
        if sc!=scope or ce!=consent or model!=requested_model or b!=boot or expiry<=now:continue
        if gen!=expected or not isinstance(raw,bytes) or len(raw)>4096 or hashlib.sha256(raw).digest()!=sha or len(k)!=256 or len(v)!=256 or source_gen<=0:
            return 'UNKNOWN',[],len(rows),[]
        try:keys=unpack_half(k);vals=unpack_half(v)
        except (ValueError,struct.error,OverflowError):return 'UNKNOWN',[],len(rows),[]
        if not all(math.isfinite(x) for x in keys+vals):return 'UNKNOWN',[],len(rows),[]
        allow.append((slot,keys,vals));meta.append((slot,kind,raw,trusted,subject,t_scope,raw_available))
    return 'SUMMARY_ONLY',allow,len(rows),meta

def exact_query(c,k,requested_scope='owner',consent=1,now=100):
    # Minimal exact fixture with full scan; this is NOT a protected-source signature verifier.
    if consent!=1:return 'DENIED',[],0
    rows=c.execute('SELECT slot,raw,raw_sha,raw_available,scope,expiry,kind,subject_id,time_scope FROM records ORDER BY slot').fetchall()
    matches=[];claim_values={}
    for slot,raw,sha,available,scope,expiry,kind,subject,t_scope in rows:
        if scope!=requested_scope or expiry<=now:continue
        if not available or not isinstance(raw,bytes) or hashlib.sha256(raw).digest()!=sha:
            return 'UNKNOWN',[],len(rows)
        matches.append((slot,raw))
        if kind=='VERIFIED_COMPLETION':claim_values.setdefault((subject,t_scope),set()).add(raw)
    if len(matches)>k:return 'TRUNCATED',matches[:k],len(rows)
    if any(len(values)>1 for values in claim_values.values()):return 'CONFLICT',matches,len(rows)
    return 'COMPLETE',matches,len(rows)

def python_reference(q,z0,eligible,T=1.0):
    logits=[sum(q[i]*it[1][i] for i in range(M))/(math.sqrt(M)*T) for it in eligible]
    if logits:
        mm=max(logits);weights=[math.exp(x-mm) for x in logits];total=sum(weights)
        rr=[sum((weights[j]/total)*item[2][i] for j,item in enumerate(eligible)) for i in range(M)]
    else:rr=[0.]*M
    return rr,[math.tanh(z0[i]+rr[i]) for i in range(M)]

def native_eval(exe,folder,eligible,q,z0,T=1.0):
    if not 0<len(q)==len(z0)==M or not all(math.isfinite(x) for x in q+z0):raise ValueError('INVALID_QUERY_VECTOR')
    if len(eligible)>16:raise ValueError('OVER_LIMIT')
    file=folder/'semantic_half.bin'
    with file.open('wb') as f:
        f.write(b'S416'+bytes([len(eligible),1,0,0]));f.write(struct.pack('<f',T))
        f.write(struct.pack('<128f',*q));f.write(struct.pack('<128f',*z0))
        for _slot,k,v in eligible:f.write(half_vec(k))
        for _slot,k,v in eligible:f.write(half_vec(v))
    p=subprocess.run([str(exe),str(file)],capture_output=True,text=True,timeout=15)
    if p.returncode or 'status=PASS' not in p.stdout:raise RuntimeError('NATIVE_SEMANTIC_FAILED '+p.stderr[-400:]+p.stdout[-150:])
    lines=p.stdout.strip().splitlines()
    if len(lines)!=2 or not lines[1].startswith('R='):raise RuntimeError('NATIVE_OUTPUT_FORMAT')
    got=[float(x) for x in lines[1][2:].split(',')]
    if len(got)!=M:raise RuntimeError('NATIVE_OUTPUT_LENGTH')
    ref,_=python_reference(q,z0,eligible,T)
    maximum=max(abs(a-b) for a,b in zip(got,ref))
    if maximum>1e-4 or not all(math.isfinite(x) for x in got):raise RuntimeError('NATIVE_PYTHON_DIVERGENCE '+str(maximum))
    match=re.search(r'F_MAC=(\d+)\b.*state_digest=([0-9a-f]{16})',lines[0])
    if not match or int(match[1])!=34816:raise RuntimeError('F_MAC_ACCOUNT_MISMATCH '+lines[0])
    return got,match[2],maximum,lines[0]

def case_run(mode,folder,exe):
    folder.mkdir(parents=True,exist_ok=False)
    c=db_init(folder/'semantic.sqlite3');negative=False
    q=vec();z0=vec(.25,-.3)
    try:
        if mode in ('C02_OPPOSITE_VALUES_COLLIDE','CONFLICT_NOT_RESOLVED_BY_SUMMARY','RECORD_ORDER_INVARIANCE'):
            # Identical keys; opposite values and independent source identities.
            add(c,2,raw=b'source-A-true',val=vec(1.,.25))
            add(c,1,raw=b'source-B-false',val=vec(-1.,-.25))
        elif mode=='STABLE_LARGE_LOGITS':
            add(c,1,key=vec(100.),val=vec(.75));add(c,2,key=vec(-100.),val=vec(-.75));q=vec(100.)
        elif mode=='K1_EXACT_TRUNCATION':
            for i in range(1,5):add(c,i,raw=('source-%d'%i).encode(),val=vec(i/8.))
        else:add(c,1)
        if mode=='EMPTY_ELIGIBLE_SET_ZERO':c.execute('DELETE FROM records')
        elif mode=='MODEL_MISMATCH_QUARANTINE':c.execute('UPDATE records SET model=?',(MODEL_B,))
        elif mode=='BOOT_MISMATCH_QUARANTINE':c.execute('UPDATE records SET boot=2')
        elif mode=='CONSENT_REVOKE_DENIES':pass
        elif mode=='PAYLOAD_INTEGRITY_UNKNOWN':c.execute('UPDATE records SET raw=? WHERE slot=1',(b'CORRUPTED',))
        elif mode=='DECLARATION_NOT_EVIDENCE':c.execute("UPDATE records SET kind='USER_DECLARATION' WHERE slot=1")
        elif mode=='HYPOTHESIS_NOT_EVIDENCE':c.execute("UPDATE records SET kind='HYPOTHESIS' WHERE slot=1")
        elif mode=='STALE_SLOT_GENERATION_UNKNOWN':c.execute('UPDATE records SET expected_generation=2 WHERE slot=1')
        elif mode=='FP16_PAYLOAD_ROUNDTRIP':c.execute('UPDATE records SET value_fp16=? WHERE slot=1',(half_vec(vec(.3333)),))
        elif mode=='EXACT_RAW_BYTES_SEPARATE':c.execute('UPDATE records SET raw=?,raw_sha=? WHERE slot=1',(b'\x00exact\xffbytes',hashlib.sha256(b'\x00exact\xffbytes').digest()))
        elif mode=='MISSING_RAW_NOT_RECONSTRUCTED':c.execute('UPDATE records SET raw=?,raw_sha=?,raw_available=0 WHERE slot=1',(b'',hashlib.sha256(b'').digest()))
        elif mode=='SAME_UID_SEMANTIC_POISON_NEGATIVE':
            forged=b'forged-same-UID'
            c.execute('UPDATE records SET raw=?,raw_sha=?,value_fp16=? WHERE slot=1',(forged,hashlib.sha256(forged).digest(),half_vec(vec(-.875))))
            negative=True
        status,eligible,scanned,meta=evaluate_store(c,consent=0 if mode=='CONSENT_REVOKE_DENIES' else 1)
        # Never use arbitrary memory as authoritative Evidence, even if its label is VERIFIED_COMPLETION.
        if mode=='CONSENT_REVOKE_DENIES':
            ok=status=='DENIED' and not eligible
            detail='consent_denied_before_native_memory_read=YES'
        elif mode in ('PAYLOAD_INTEGRITY_UNKNOWN','STALE_SLOT_GENERATION_UNKNOWN'):
            ok=status=='UNKNOWN' and not eligible
            detail='corrupt_or_stale_record_unavailable=YES'
        else:
            if status!='SUMMARY_ONLY':raise RuntimeError('SEMANTIC_STATUS_INCORRECT '+status)
            r,digest,err,_header_text=native_eval(exe,folder,eligible,q,z0)
            if mode=='SINGLE_SEMANTIC_CONTEXT':ok=len(eligible)==1 and abs(r[0]-.5)<1e-5
            elif mode=='C02_OPPOSITE_VALUES_COLLIDE':ok=len(eligible)==2 and abs(r[0])<1e-6 and abs(r[1])<1e-6 and len({x[2] for x in meta})==2
            elif mode=='EMPTY_ELIGIBLE_SET_ZERO':
                z_match=re.search(r'\bz0=([-+0-9.eE]+)\b',_header_text)
                ok=len(eligible)==0 and r==[0.]*M and z_match is not None and abs(float(z_match[1])-math.tanh(z0[0]))<1e-6
            elif mode=='STABLE_LARGE_LOGITS':ok=len(eligible)==2 and abs(r[0]-.75)<1e-4
            elif mode=='FP16_PAYLOAD_ROUNDTRIP':
                quantized=unpack_half(half_vec(vec(.3333)))[0]
                ok=abs(r[0]-quantized)<1e-6 and abs(quantized-.3333)>1e-7 and len(half_vec(vec(.3333)))==256
            elif mode in ('MODEL_MISMATCH_QUARANTINE','BOOT_MISMATCH_QUARANTINE'):
                ok=len(eligible)==0 and all(x==0 for x in r)
            elif mode=='DECLARATION_NOT_EVIDENCE':ok=meta[0][1]=='USER_DECLARATION' and not any(kind=='VERIFIED_COMPLETION' and trust for _,kind,_,trust,_,_,_ in meta)
            elif mode=='HYPOTHESIS_NOT_EVIDENCE':ok=meta[0][1]=='HYPOTHESIS' and not any(kind=='VERIFIED_COMPLETION' and trust for _,kind,_,trust,_,_,_ in meta)
            elif mode=='CONFLICT_NOT_RESOLVED_BY_SUMMARY':
                exact_state,exact_refs,full_scan=exact_query(c,k=4)
                ok=len(eligible)==2 and abs(r[0])<1e-6 and status=='SUMMARY_ONLY' and meta[0][4:6]==meta[1][4:6] and exact_state=='CONFLICT' and full_scan==2
            elif mode=='EXACT_RAW_BYTES_SEPARATE':
                exact_state,exact_refs,full_scan=exact_query(c,k=1)
                ok=exact_state=='COMPLETE' and exact_refs==[(1,b'\x00exact\xffbytes')] and status=='SUMMARY_ONLY' and b'\x00exact\xffbytes' not in folder.joinpath('semantic_half.bin').read_bytes()
            elif mode=='MISSING_RAW_NOT_RECONSTRUCTED':
                exact_state,exact_refs,full_scan=exact_query(c,k=1)
                ok=meta[0][2]==b'' and meta[0][-1]==0 and exact_state=='UNKNOWN' and not exact_refs and status=='SUMMARY_ONLY' and abs(r[0]-.5)<1e-5
            elif mode=='K1_EXACT_TRUNCATION':
                exact_state,exact_refs,full_scan=exact_query(c,k=1)
                ok=len(eligible)==4 and scanned==4 and exact_state=='TRUNCATED' and len(exact_refs)==1 and full_scan==4 and status=='SUMMARY_ONLY'
            elif mode=='SAME_UID_SEMANTIC_POISON_NEGATIVE':ok=negative and len(eligible)==1 and abs(r[0]+.875)<1e-5 and meta[0][2]==b'forged-same-UID'
            elif mode=='RECORD_ORDER_INVARIANCE':
                # DB insertion order is 2,1; canonical scan is slot 1,2. Same result after reverse-insertion.
                before=[p[0] for p in eligible]
                temp=folder/'second';temp.mkdir();other=temp/'test.sqlite3';c2=db_init(other)
                try:
                    add(c2,1,raw=b'source-B-false',val=vec(-1.,-.25))
                    add(c2,2,raw=b'source-A-true',val=vec(1.,.25))
                    s2,e2,scan2,m2=evaluate_store(c2)
                    r2,d2,e2err,_hdr2=native_eval(exe,temp,e2,q,z0)
                    ok=s2==status and before==[1,2] and d2==digest and len(e2)==2 and max(abs(a-b) for a,b in zip(r,r2))<1e-6
                finally:c2.close()
            else:ok=False
            detail=f'semantic_status={status} eligible={len(eligible)} indexed_scan={scanned} r0={r[0]:.6g} native_F_MAC=34816 python_native_absmax={err:.2g}'
            if mode in ('C02_OPPOSITE_VALUES_COLLIDE','CONFLICT_NOT_RESOLVED_BY_SUMMARY'):detail+=' provenance_not_invertible=YES'
            if mode=='SAME_UID_SEMANTIC_POISON_NEGATIVE':detail+=' same_UID_forged_digest_accepted=YES'
            if mode=='K1_EXACT_TRUNCATION':detail+=' exact_k1_status=TRUNCATED'
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
        return bool(ok and integrity=='ok'),detail,integrity,negative
    finally:c.close()

def stage(log,ctx,binary,exe,root,nworkers,host,inject_abort=False):
    tag=f'S5x{nworkers}_RAM32';expected=len(MODES)*(1 if host else 2)
    stop=ctx.Event();wready=ctx.Queue();wout=ctx.Queue();rready=ctx.Queue()
    workers=[];holder=None;failures=0;completed=0;negative_found=0;worker_ok=0;mslist=[];reason=None
    start=time.monotonic()
    try:
        holder=ctx.Process(target=ram_worker,args=(stop,rready));holder.start()
        if rready.get(timeout=12) is not True:raise RuntimeError('RAM_HOLDER_FAILED')
        for _ in range(nworkers):
            w=ctx.Process(target=s5_worker,args=(binary,stop,wready,wout));w.start();workers.append(w)
        if len({wready.get(timeout=25) for _ in workers})!=nworkers:raise RuntimeError('NATIVE_BACKGROUND_START_FAILED')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={tag} workers={nworkers}')
        log(f'STAGE_BEGIN stage={tag} cases={expected} modes={len(MODES)} RAM_MiB=32')
        for rep in range(1,2 if host else 3):
            for idx,mode in enumerate(MODES):
                if why:=safety(host):reason=why;break
                if inject_abort and completed>=4:reason='INJECTED_HOST_ABORT';break
                start_case=time.monotonic()
                ok,detail,integrity,negative=case_run(mode,root/tag/f'{rep:02d}_{idx:02d}_{mode}',exe)
                duration=(time.monotonic()-start_case)*1000
                completed+=1;mslist.append(duration)
                if not ok:failures+=1
                if ok and negative:negative_found+=1
                log(f'CASE stage={tag} rep={rep} mode={mode} status={"PASS_EXPECTED_NEGATIVE" if ok and negative else "PASS" if ok else "FAIL"} '
                    f'{detail} sqlite_integrity={integrity} elapsed_ms={duration:.3f}')
            if reason:break
        floor=2 if host else (24 if nworkers==2 else 30)
        while not reason and time.monotonic()-start<floor:
            if why:=safety(host):reason=why;break
            time.sleep(.15)
    except BaseException as exc:
        failures+=1;log(f'STAGE_ERROR stage={tag} exception={type(exc).__name__} detail={str(exc)[:300]}')
    finally:
        stop.set()
        for w in workers:
            w.join(5)
            if w.is_alive():w.kill();w.join(3)
        if holder:
            holder.join(4)
            if holder.is_alive():holder.kill();holder.join(3)
        for _ in workers:
            try:
                pid,runs,mean,lowest,errs=wout.get(timeout=3)
                log(f'S5_WORKER stage={tag} pid={pid} native_runs={runs} mean_GMAC_s={mean:.6f} min_GMAC_s={lowest:.6f} errors={errs}')
                if runs>0 and not errs:worker_ok+=1
                else:failures+=1
            except queue.Empty:failures+=1;log(f'S5_WORKER stage={tag} REPORT_MISSING')
        for q in (wready,wout,rready):q.cancel_join_thread();q.close()
    label='SAFETY_ABORT' if reason else ('COMPLETE' if completed==expected and not failures and worker_ok==nworkers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={tag} status={label} cases={completed}/{expected} failures={failures} negative_findings={negative_found} workers_ok={worker_ok}/{nworkers} case_max_ms={max(mslist) if mslist else None} safety_reason={reason or "-"}')
    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={tag} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return label,completed,negative_found

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='developer Linux mode only')
    ap.add_argument('--inject-host-abort',action='store_true',help='developer Linux mode only')
    args=ap.parse_args()
    if args.inject_host_abort and not args.host_smoke:raise SystemExit('HOST_ONLY_INJECTION')
    home=Path.home();out=home/'storage'/'downloads'
    if not out.is_dir() or not os.access(out,os.W_OK):out=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=out/f'UNO_A52_R41_S4_SEMANTIC_EXACT_BOUNDARY_V16_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(s):print(s,flush=True);f.write(s+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- NATIVE S5 SEMANTIC MEMORY / EXACT EVIDENCE BOUNDARY '+VERSION)
            log('R4.1 S4/C02: softmax memory produces SUMMARY_ONLY; opposite values can cancel and provenance cannot be reconstructed from r.')
            log('SQLite synthetic raw+SHA and FP16 m=128 vectors; query and native C S4 scan + C256R32 synthetic F; independent Python numerical oracle.')
            log('Live 2/4 native S5 background workers + 32MiB RAM per stage. Same UID can forge source and checksum: intentional NEGATIVE control.')
            log('NO trained model, real private data, protected L, Android auth, Binder, OS actions, real P learning, production code, energy guarantee or power loss.')
            log('SAFETY battery>=40%, battery temp<37.5C, MemAvailable>=400000 kB; abort is NOT COMPLETE.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if why:=safety(args.host_smoke):log('RESULT SAFETY_SKIP '+why);return 3
            bg=native_s5();log('VERIFIED_BACKGROUND_S5 '+str(bg))
            root=home/'uno_a52_r41_s4_semantic_exact_v16'/stamp;root.mkdir(parents=True,exist_ok=False)
            exe,sha=compile_native(root);log(f'COMPILED_NATIVE_SEMANTIC {exe} source_sha256={sha}')
            selftest=root/'selftest';selftest.mkdir()
            result,dig,err,_hdr=native_eval(exe,selftest,[(1,vec(0.),vec(.5))],vec(),vec(.25,-.3))
            if abs(result[0]-.5)>1e-5 or err>1e-5:raise RuntimeError('SEMANTIC_NATIVE_SELFTEST_FAIL')
            log(f'SELFTEST_PASS native_fp16=YES python_oracle=YES synthetic_F_MAC=34816 state_digest={dig}')
            ctx=mp.get_context('fork')
            s1=stage(log,ctx,bg,exe,root,1 if args.host_smoke else 2,args.host_smoke,args.inject_host_abort)
            if s1[0]!='COMPLETE':log(f'RESULT {s1[0]} cases={s1[1]}');return 3
            s2=stage(log,ctx,bg,exe,root,2 if args.host_smoke else 4,args.host_smoke)
            if s2[0]!='COMPLETE':log(f'RESULT {s2[0]} cases={s2[1]}');return 3
            log(f'RESULT COMPLETE_SYNTHETIC_SEMANTIC_EXACT_BOUNDARY stages=2/2 cases={s1[1]+s2[1]} expected_negative_findings={s1[2]+s2[2]}')
            log('LIMIT: source trust is not enforced by same-UID SQLite; no exact proof from summary, semantic quality or Android trust boundary.')
            return 0
        except BaseException as exc:
            log(f'RESULT ERROR {type(exc).__name__}: {str(exc)[:250]}')
            log('TRACE '+traceback.format_exc()[-1200:]);return 2
        finally:log('REPORT '+str(report))
if __name__=='__main__':sys.exit(main())
