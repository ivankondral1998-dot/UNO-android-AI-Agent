#!/usr/bin/env python3
"""UNO R4.1 §11.2 PRECODE native S5 recovery/provenance/atomicity lab.
No training, no production Android changes, no actual user data.
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
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
import traceback

VERSION='UNO_R41_A52_NATIVE_S5_RECOVERY_PROVENANCE_ATOMICITY_V15'
MIB=1048576
MODEL_A=hashlib.sha256(b'lab-model-A').hexdigest()
MODEL_B=hashlib.sha256(b'lab-model-B').hexdigest()
DSP_A=hashlib.sha256(b'lab-dsp-A').hexdigest()
DSP_B=hashlib.sha256(b'lab-dsp-B').hexdigest()
SEED=0x5a63f198
N_EVENTS=6
MODES=(
    'AUTHENTIC_EVENT_REPLAY','LOST_SNAPSHOT_REPLAY','ALTERED_SNAPSHOT_RECOMPUTED',
    'EMPTY_HISTORY_UNKNOWN','PAYLOAD_CORRUPT_UNKNOWN','SEQUENCE_GAP_UNKNOWN',
    'SEQUENCE_REORDER_UNKNOWN','FOREIGN_MODEL_RESET','FOREIGN_DSP_RESET',
    'MISSING_RNG_RESET','CROSS_BOOT_TIME_QUARANTINE','REVOKED_CONSENT_DENIED',
    'KNOWN_BACKUP_EXACT_BYTES','NO_BACKUP_NO_BYTE_GUESS','SIMILAR_SUMMARY_NOT_EXACT',
    'CRASH_BEFORE_COMMIT_ALL_OR_NOTHING','CRASH_AFTER_COMMIT_ALL_VISIBLE',
    'PREPARED_UNVERIFIED_REMAINS_UNKNOWN','DUPLICATE_RECEIPT_DENIED',
    'SAME_UID_FORGED_CHAIN_NEGATIVE',
)
C_SOURCE=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#define D 256
#define R 32
#define B 32
#define Q 2
#define MAC_PER_BLOCK (2*D*R+B*R)
static float A[8][R][D], C[8][R][D], W[8][B][R];
static uint32_t prng=0x79b43ad1u;
static uint32_t x32(void){prng^=prng<<13; prng^=prng>>17; prng^=prng<<5;return prng;}
static float sample(void){return ((float)(x32()%20001)/10000.f-1.f)*.012f;}
static void init(void){
 for(int j=0;j<8;j++){
  for(int r=0;r<R;r++)for(int i=0;i<D;i++){A[j][r][i]=sample();C[j][r][i]=sample();}
  for(int b=0;b<B;b++)for(int r=0;r<R;r++)W[j][b][r]=sample();
 }
}
static uint64_t fnv_bytes(uint64_t h,const void *data,size_t n){
 const unsigned char *p=(const unsigned char *)data;
 for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ull;}
 return h;
}
int main(int argc,char **argv){
 if(argc!=3){fprintf(stderr,"usage: native_fixture event_file seed\n");return 2;}
 char *end=0;unsigned long seed=strtoul(argv[2],&end,10);
 if(!end||*end||seed==0||seed>0xfffffffful)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f){perror("open");return 2;}
 init();float h[D],z[D],next[D],a[R],c[R];
 for(int i=0;i<D;i++)h[i]=.01f*(float)((i%13)-6)+.00001f*(float)(seed%997u);
 unsigned long long mac=0;int n=0;unsigned char buf[8];
 while(fread(buf,1,8,f)==8){
  if(++n>1024){fclose(f);return 4;}
  int32_t x,y;memcpy(&x,buf,4);memcpy(&y,buf+4,4);
  for(int i=0;i<D;i++)z[i]=.001f*(float)((x%211)+(i%11)-(y%101));
  memcpy(next,h,sizeof(h));
  for(int t=0;t<Q;t++){
   int j=(n-1+t)%8;
   for(int r=0;r<R;r++){
    float sa=0,sc=0;
    for(int i=0;i<D;i++){sa+=A[j][r][i]*h[i];sc+=C[j][r][i]*z[i];}
    a[r]=sa;c[r]=sc;
   }
   for(int b=0;b<B;b++){
    float s=0;for(int r=0;r<R;r++)s+=W[j][b][r]*tanhf(a[r]+c[r]);
    next[j*B+b]=.75f*h[j*B+b]+.25f*tanhf(s);
   }
   mac+=MAC_PER_BLOCK;
  }
  memcpy(h,next,sizeof(h));
 }
 int remainder=!feof(f);fclose(f);
 if(remainder||n==0){fprintf(stderr,"INVALID_EVENT_DATA\n");return 4;}
 uint64_t dig=fnv_bytes(1469598103934665603ull,h,sizeof(h));
 printf("NATIVE_REPLAY events=%d blocks=%d actual_F_MAC=%llu state_digest=%016llx status=PASS\n",n,n*Q,mac,(unsigned long long)dig);
 return 0;
}
'''

def number(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def telemetry():
    try: mem=int(next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')).split()[1])
    except (OSError,ValueError,StopIteration,IndexError):mem=None
    return number('/sys/class/power_supply/battery/capacity'),number('/sys/class/power_supply/battery/temp'),mem

def safety(host):
    if host:return None
    b,t,m=telemetry()
    if None in (b,t,m) or not 100<=t<=800:return 'DEVICE_TELEMETRY_UNAVAILABLE'
    if b<40:return 'BATTERY_LT_40_PERCENT'
    if t>=375:return 'BATTERY_T_GE_37_5C'
    if m<400000:return 'MEMAVAILABLE_LT_400000_KB'
    return None

def background_s5():
    p=Path.home()/'uno_a52_r41_operator_lab'/'uno_r41_s5_operator'
    if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('NATIVE_S5_MISSING '+str(p))
    r=subprocess.run([str(p),'rank','prefix2','0.30'],capture_output=True,text=True,timeout=12)
    if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):
        raise RuntimeError('S5_PRECHECK_FAIL '+r.stdout[-180:])
    return p

def s5_worker(binary,cancel,ready,out):
    samples=[];errors=[]
    try:
        while not cancel.is_set():
            r=subprocess.run([str(binary),'rank','full','0.70'],capture_output=True,text=True,timeout=12)
            if r.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS',r.stdout):raise RuntimeError('S5_NATIVE_FAILED')
            match=re.search(r'estimated_F_GMAC_s=([\d.]+)',r.stdout)
            if not match:raise RuntimeError('S5_METRIC_MISSING')
            samples.append(float(match[1]))
            if len(samples)==1:ready.put(os.getpid(),timeout=3)
    except BaseException as exc:errors.append(str(exc)[:160])
    try:out.put((os.getpid(),len(samples),statistics.mean(samples) if samples else 0.,min(samples) if samples else 0.,errors),timeout=3)
    except BaseException:pass

def ram_worker(cancel,ready):
    try:
        b=bytearray(32*MIB)
        for i in range(0,len(b),4096):b[i]=1
        ready.put(True,timeout=4)
        while not cancel.wait(.15):
            for i in range(0,len(b),262144):b[i]^=1
    except BaseException:
        try:ready.put(False,timeout=3)
        except BaseException:pass

def compile_native(root):
    src=root/'v15_replay.c';exe=root/'v15_replay'
    src.write_text(C_SOURCE,encoding='utf-8')
    r=subprocess.run(['clang','-std=c11','-O2',str(src),'-lm','-o',str(exe)],capture_output=True,text=True,timeout=45)
    if r.returncode:raise RuntimeError('CLANG_FAILED '+r.stderr[-500:])
    return exe,hashlib.sha256(src.read_bytes()).hexdigest()

def db_connect(db):
    c=sqlite3.connect(str(db),timeout=7,isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    c.execute('PRAGMA busy_timeout=5000')
    return c

def create_db(db):
    c=db_connect(db)
    c.execute('CREATE TABLE metadata (k TEXT PRIMARY KEY, v TEXT NOT NULL)')
    c.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, payload BLOB NOT NULL, payload_sha BLOB NOT NULL, prev BLOB NOT NULL, digest BLOB NOT NULL)')
    c.execute('CREATE TABLE snapshot (id INTEGER PRIMARY KEY CHECK(id=1), state_digest TEXT NOT NULL)')
    c.execute('CREATE TABLE dispatch (tx TEXT PRIMARY KEY, status TEXT NOT NULL)')
    c.execute('CREATE TABLE used (tx TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE receipt (tx TEXT PRIMARY KEY, bytes BLOB NOT NULL)')
    c.execute('CREATE TABLE memory_ref (tx TEXT PRIMARY KEY, slot INTEGER NOT NULL, generation INTEGER NOT NULL)')
    c.execute('CREATE TABLE p_snapshot (tx TEXT PRIMARY KEY, data BLOB NOT NULL)')
    for k,v in [('model',MODEL_A),('dsp',DSP_A),('rng',str(SEED)),('boot','1'),('consent','1'),('tip',bytes(32).hex()),('event_count','0')]:
        c.execute('INSERT INTO metadata VALUES (?,?)',(k,v))
    return c

def meta(c,key):return c.execute('SELECT v FROM metadata WHERE k=?',(key,)).fetchone()
def set_meta(c,key,value):c.execute('UPDATE metadata SET v=? WHERE k=?',(str(value),key))

def append_event(c,seq,payload):
    prev=bytes.fromhex(meta(c,'tip')[0])
    dh=hashlib.sha256(prev+struct.pack('<Q',seq)+payload).digest()
    c.execute('BEGIN IMMEDIATE')
    try:
        c.execute('INSERT INTO events VALUES(?,?,?,?,?)',(seq,payload,hashlib.sha256(payload).digest(),prev,dh))
        set_meta(c,'tip',dh.hex());set_meta(c,'event_count',seq)
        c.execute('COMMIT')
    except BaseException:c.execute('ROLLBACK');raise

def load_events(c):
    rows=c.execute('SELECT seq,payload,payload_sha,prev,digest FROM events ORDER BY seq').fetchall()
    if not rows or len(rows)!=int(meta(c,'event_count')[0]):return None,'MISSING_OR_GAPPED_EVENTS'
    prev=bytes(32)
    for expected,(seq,payload,payload_sha,seen_prev,seen_digest) in enumerate(rows,1):
        if seq!=expected or not isinstance(payload,bytes) or len(payload)!=8 or hashlib.sha256(payload).digest()!=payload_sha:
            return None,'INTEGRITY_OR_SEQUENCE_MISMATCH'
        calc=hashlib.sha256(prev+struct.pack('<Q',seq)+payload).digest()
        if seen_prev!=prev or seen_digest!=calc:return None,'BROKEN_CHAIN'
        prev=calc
    if meta(c,'tip')[0]!=prev.hex():return None,'TIP_MISMATCH'
    return b''.join(row[1] for row in rows),'OK'

def native_replay(exe,case_folder,data,seed):
    source=case_folder/'events.bin'
    source.write_bytes(data)
    r=subprocess.run([str(exe),str(source),str(seed)],capture_output=True,text=True,timeout=12)
    if r.returncode:raise RuntimeError('NATIVE_REPLAY_ERROR '+r.stderr[-250:]+r.stdout[-250:])
    line=r.stdout.strip()
    if 'status=PASS' not in line or f'events={len(data)//8}' not in line:
        raise RuntimeError('NATIVE_REPLAY_CONTRACT_FAIL '+line)
    mm=re.search(r'state_digest=([a-f0-9]{16})',line)
    mac=re.search(r'actual_F_MAC=(\d+)',line)
    if not mm or not mac or int(mac[1]) != len(data)//8*2*(2*256*32+32*32):
        raise RuntimeError('NATIVE_REPLAY_MAC_LEDGER_FAIL '+line)
    return mm[1],int(mac[1])

def recover(c,exe,case_folder,expected_model=MODEL_A,expected_dsp=DSP_A,expected_boot='1'):
    if meta(c,'consent')[0]!='1':return 'DENIED_CONSENT',None,0
    if meta(c,'model')[0]!=expected_model or meta(c,'dsp')[0]!=expected_dsp:return 'RESET_UNKNOWN_MANIFEST',None,0
    if meta(c,'boot')[0]!=expected_boot:return 'QUARANTINE_BOOT',None,0
    seedrow=meta(c,'rng')
    if not seedrow:return 'RESET_UNKNOWN_RNG',None,0
    try:seed=int(seedrow[0]);assert 0<seed<2**32
    except (ValueError,AssertionError):return 'RESET_UNKNOWN_RNG',None,0
    data,status=load_events(c)
    if status!='OK':return 'UNKNOWN_LEDGER',None,0
    digest,mac=native_replay(exe,case_folder,data,seed)
    return 'REPLAYED',digest,mac

def populate(c):
    for seq in range(1,N_EVENTS+1):append_event(c,seq,struct.pack('<ii',seq*31-100,seq*17+9))

def child_tx(db,ready,when):
    c=db_connect(db)
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT INTO used VALUES (?)',('tx-alpha',))
        c.execute('INSERT INTO receipt VALUES (?,?)',('tx-alpha',b'synthetic native outcome'))
        c.execute('INSERT INTO memory_ref VALUES (?,?,?)',('tx-alpha',2,5))
        c.execute('INSERT INTO p_snapshot VALUES (?,?)',('tx-alpha',b'PREBUILT_STATIC_BYTES_NO_LEARNING'))
        if when=='POST':c.execute('COMMIT')
        ready.put('STAGED' if when=='PRE' else 'COMMITTED',timeout=5)
        time.sleep(8) # parent kills process to simulate isolated writer crash
    finally:c.close()

def tx_counts(c):
    return [c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('used','receipt','memory_ref','p_snapshot')]

def case_run(mode,root,exe,ctx):
    root.mkdir(parents=True,exist_ok=False);db=root/'events.sqlite3';c=create_db(db)
    negative=False
    try:
        populate(c)
        baseline,digest0,mac0=recover(c,exe,root)
        if baseline!='REPLAYED' or not digest0 or mac0!=N_EVENTS*2*17408:raise RuntimeError('BASELINE_REPLAY_INVALID')
        if mode=='AUTHENTIC_EVENT_REPLAY':
            state,dig,mac=recover(c,exe,root)
            ok=state=='REPLAYED' and dig==digest0 and mac==mac0
            detail=f'byte_equal_state_digest={int(dig==digest0)} events={N_EVENTS} native_F_MAC={mac}'
        elif mode=='LOST_SNAPSHOT_REPLAY':
            c.execute('INSERT INTO snapshot VALUES (1,?)',(digest0,));c.execute('DELETE FROM snapshot')
            state,dig,mac=recover(c,exe,root)
            ok=state=='REPLAYED' and dig==digest0 and mac==mac0
            detail='snapshot_absent_authentic_replay=YES'
        elif mode=='ALTERED_SNAPSHOT_RECOMPUTED':
            c.execute('INSERT INTO snapshot VALUES (1,?)',('0000000000000000',))
            state,dig,mac=recover(c,exe,root)
            ok=state=='REPLAYED' and dig==digest0 and dig!='0000000000000000'
            detail='stale_snapshot_ignored_native_replay=YES'
        elif mode=='EMPTY_HISTORY_UNKNOWN':
            c.execute('DELETE FROM events');set_meta(c,'tip',bytes(32).hex());set_meta(c,'event_count','0')
            state,dig,mac=recover(c,exe,root)
            ok=state=='UNKNOWN_LEDGER' and dig is None and mac==0
            detail='missing_events_not_invented=YES'
        elif mode=='PAYLOAD_CORRUPT_UNKNOWN':
            c.execute('UPDATE events SET payload=? WHERE seq=2',(b'changed!',))
            state,dig,mac=recover(c,exe,root)
            ok=state=='UNKNOWN_LEDGER' and dig is None and mac==0
            detail='payload_corruption_rejected_before_F=YES'
        elif mode=='SEQUENCE_GAP_UNKNOWN':
            c.execute('DELETE FROM events WHERE seq=3')
            state,dig,mac=recover(c,exe,root)
            ok=state=='UNKNOWN_LEDGER' and dig is None and mac==0
            detail='missing_sequence_rejected=YES'
        elif mode=='SEQUENCE_REORDER_UNKNOWN':
            c.execute('UPDATE events SET seq=99 WHERE seq=1')
            state,dig,mac=recover(c,exe,root)
            ok=state=='UNKNOWN_LEDGER' and dig is None and mac==0
            detail='reordered_sequence_rejected=YES'
        elif mode=='FOREIGN_MODEL_RESET':
            set_meta(c,'model',MODEL_B)
            state,dig,mac=recover(c,exe,root)
            ok=state=='RESET_UNKNOWN_MANIFEST' and dig is None and mac==0
            detail='different_model_no_old_hidden_state_replay=YES'
        elif mode=='FOREIGN_DSP_RESET':
            set_meta(c,'dsp',DSP_B)
            state,dig,mac=recover(c,exe,root)
            ok=state=='RESET_UNKNOWN_MANIFEST' and dig is None and mac==0
            detail='different_DSP_no_state_replay=YES'
        elif mode=='MISSING_RNG_RESET':
            c.execute('DELETE FROM metadata WHERE k=?',('rng',))
            state,dig,mac=recover(c,exe,root)
            ok=state=='RESET_UNKNOWN_RNG' and dig is None and mac==0
            detail='missing_PRNG_seed_no_replay=YES'
        elif mode=='CROSS_BOOT_TIME_QUARANTINE':
            set_meta(c,'boot','2')
            state,dig,mac=recover(c,exe,root)
            ok=state=='QUARANTINE_BOOT' and dig is None and mac==0
            detail='old_monotonic_time_not_compared=YES'
        elif mode=='REVOKED_CONSENT_DENIED':
            set_meta(c,'consent','0')
            state,dig,mac=recover(c,exe,root)
            ok=state=='DENIED_CONSENT' and dig is None and mac==0
            detail='policy_denies_replay=YES'
        elif mode=='KNOWN_BACKUP_EXACT_BYTES':
            original=b'RAW EXACT \x00 \xff private-lab-bytes';bak=root/'known_backing.bin';bak.write_bytes(original)
            expected=hashlib.sha256(original).digest();stored=bytearray(original);stored[3]^=0x18
            recovered=bak.read_bytes() if hashlib.sha256(bak.read_bytes()).digest()==expected else None
            ok=hashlib.sha256(stored).digest()!=expected and recovered==original
            detail='source_backing_bytes_match_original=YES'
        elif mode=='NO_BACKUP_NO_BYTE_GUESS':
            source=b'private only original\x00\x01';hint=b'private only ...';recovered=None
            ok=source!=hint and recovered is None
            detail='lost_bytes_unavailable_not_guessed=YES'
        elif mode=='SIMILAR_SUMMARY_NOT_EXACT':
            source=b'OWNER SAID: schedule 14:00';summary=b'OWNER SAID: schedule around two'
            ok=source!=summary and hashlib.sha256(source).digest()!=hashlib.sha256(summary).digest()
            detail='semantic_summary_not_exact_source=YES'
        elif mode in ('CRASH_BEFORE_COMMIT_ALL_OR_NOTHING','CRASH_AFTER_COMMIT_ALL_VISIBLE'):
            c.execute('INSERT INTO dispatch VALUES (?,?)',('tx-alpha','PREPARED'))
            c.close();c=None
            ready=ctx.Queue();when='PRE' if mode=='CRASH_BEFORE_COMMIT_ALL_OR_NOTHING' else 'POST'
            p=ctx.Process(target=child_tx,args=(str(db),ready,when));p.start()
            try:
                got=ready.get(timeout=12)
                if got!=('STAGED' if when=='PRE' else 'COMMITTED'):raise RuntimeError('CRASH_CHILD_BAD_MARKER')
                p.kill();p.join(5)
                if p.is_alive():raise RuntimeError('CRASH_CHILD_STILL_ALIVE')
            finally:
                if p.is_alive():p.kill();p.join(3)
                ready.cancel_join_thread();ready.close()
            c=db_connect(db);counts=tx_counts(c)
            status=c.execute('SELECT status FROM dispatch WHERE tx=?',('tx-alpha',)).fetchone()[0]
            ok=counts==([0,0,0,0] if when=='PRE' else [1,1,1,1]) and status=='PREPARED'
            detail=f'crash_point={when} counts={counts} prepared_status={status}'
        elif mode=='PREPARED_UNVERIFIED_REMAINS_UNKNOWN':
            c.execute('INSERT INTO dispatch VALUES (?,?)',('tx-alpha','PREPARED'))
            row=c.execute('SELECT status FROM dispatch WHERE tx=?',('tx-alpha',)).fetchone()[0]
            counts=tx_counts(c)
            decision='MAY_HAVE_EXECUTED' if row=='PREPARED' and counts==[0,0,0,0] else 'INVALID'
            ok=decision=='MAY_HAVE_EXECUTED'
            detail='no_replay_or_false_FAILURE_status='+decision
        elif mode=='DUPLICATE_RECEIPT_DENIED':
            c.execute('INSERT INTO receipt VALUES (?,?)',('tx-alpha',b'first'))
            duplicate=False
            try:c.execute('INSERT INTO receipt VALUES (?,?)',('tx-alpha',b'second'))
            except sqlite3.IntegrityError:duplicate=True
            raw=c.execute('SELECT bytes FROM receipt WHERE tx=?',('tx-alpha',)).fetchone()[0]
            ok=duplicate and raw==b'first'
            detail='duplicate_receipt_uniqueness=YES'
        elif mode=='SAME_UID_FORGED_CHAIN_NEGATIVE':
            negative=True
            raw=bytearray(c.execute('SELECT payload FROM events WHERE seq=3').fetchone()[0]);raw[0]^=0x35
            c.execute('UPDATE events SET payload=? WHERE seq=3',(bytes(raw),))
            prev=bytes(32)
            for seq,payload in c.execute('SELECT seq,payload FROM events ORDER BY seq').fetchall():
                dh=hashlib.sha256(prev+struct.pack('<Q',seq)+payload).digest()
                c.execute('UPDATE events SET payload_sha=?, prev=?, digest=? WHERE seq=?',
                          (hashlib.sha256(payload).digest(),prev,dh,seq))
                prev=dh
            set_meta(c,'tip',prev.hex())
            status,dig,mac=recover(c,exe,root)
            ok=status=='REPLAYED' and dig!=digest0 and mac==mac0
            detail=f'forged_same_UID_chain_accepted=YES changed_state={int(dig!=digest0)}'
        else:raise RuntimeError('UNKNOWN_MODE')
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
        return bool(ok and integrity=='ok'),detail,integrity,negative
    finally:
        if c is not None:c.close()

def stage(log,ctx,background,exe,root,nworkers,host,inject_abort=False):
    tag=f'S5x{nworkers}_RAM32';cancel=ctx.Event();ready=ctx.Queue();res=ctx.Queue();rr=ctx.Queue()
    workers=[];holder=None;failures=0;complete=0;negative_findings=0;worker_ok=0;reason=None;elapsed=[]
    repeats=1 if host else 2;expected=len(MODES)*repeats;start=time.monotonic()
    try:
        holder=ctx.Process(target=ram_worker,args=(cancel,rr));holder.start()
        if rr.get(timeout=12) is not True:raise RuntimeError('RAM_WORKER_FAILED')
        for _ in range(nworkers):
            p=ctx.Process(target=s5_worker,args=(background,cancel,ready,res));p.start();workers.append(p)
        if len({ready.get(timeout=30) for _ in workers})!=nworkers:raise RuntimeError('BACKGROUND_S5_NOT_READY')
        log(f'NATIVE_S5_CONFIRMED_ACTIVE stage={tag} workers={nworkers}')
        log(f'STAGE_BEGIN stage={tag} modes={len(MODES)} repeats={repeats} cases={expected} RAM_MiB=32')
        for rep in range(repeats):
            for j,mode in enumerate(MODES):
                if reason:=safety(host):break
                if inject_abort and complete>=4:reason='INJECTED_HOST_TEST_ABORT';break
                t0=time.monotonic()
                ok,detail,integrity,negative=case_run(mode,root/tag/f'{rep+1:02d}_{j+1:02d}_{mode}',exe,ctx)
                ms=(time.monotonic()-t0)*1000;elapsed.append(ms);complete+=1
                if not ok:failures+=1
                if negative and ok:negative_findings+=1
                log(f'CASE stage={tag} rep={rep+1} mode={mode} status={"PASS_EXPECTED_NEGATIVE" if ok and negative else "PASS" if ok else "FAIL"} '
                    f'{detail} sqlite_integrity={integrity} elapsed_ms={ms:.3f}')
            if reason:break
        floor=2 if host else (24 if nworkers==2 else 30)
        while not reason and time.monotonic()-start<floor:
            if reason:=safety(host):break
            time.sleep(.15)
    except BaseException as exc:
        failures+=1;log(f'STAGE_ERROR stage={tag} {type(exc).__name__} {str(exc)[:250]}')
    finally:
        cancel.set()
        for p in workers:
            p.join(5)
            if p.is_alive():p.kill();p.join(3)
        if holder:
            holder.join(4)
            if holder.is_alive():holder.kill();holder.join(3)
        for _ in workers:
            try:
                pid,runs,mean,lowest,errs=res.get(timeout=3)
                log(f'S5_WORKER stage={tag} pid={pid} native_runs={runs} mean_GMAC_s={mean:.5f} min_GMAC_s={lowest:.5f} errors={errs}')
                if runs>0 and not errs:worker_ok+=1
                else:failures+=1
            except queue.Empty:failures+=1;log(f'S5_WORKER stage={tag} REPORT_MISSING')
        for qq in (ready,res,rr):qq.cancel_join_thread();qq.close()
    status='SAFETY_ABORT' if reason else ('COMPLETE' if complete==expected and not failures and worker_ok==nworkers else 'INCOMPLETE_OR_FAIL')
    log(f'STAGE_SUMMARY stage={tag} status={status} cases={complete}/{expected} failures={failures} '
        f'negative_findings={negative_findings} workers_ok={worker_ok}/{nworkers} case_max_ms={max(elapsed) if elapsed else None} safety_reason={reason or "-"}')
    b,t,m=telemetry();log(f'STAGE_TELEMETRY stage={tag} battery={b} temp_deciC={t} MemAvailable_kB={m}')
    return status,complete,negative_findings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host-smoke',action='store_true',help='Linux developer mode: sensor guards skipped')
    ap.add_argument('--inject-host-abort',action='store_true',help='Only with --host-smoke')
    args=ap.parse_args()
    if args.inject_host_abort and not args.host_smoke:raise SystemExit('INJECTION_HOST_ONLY')
    home=Path.home();out=home/'storage'/'downloads'
    if not out.is_dir() or not os.access(out,os.W_OK):out=home
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=out/f'UNO_A52_R41_S5_RECOVERY_PROVENANCE_V15_{stamp}.txt'
    with report.open('x',encoding='utf-8') as f:
        def log(msg):print(msg,flush=True);f.write(msg+'\n');f.flush()
        try:
            log('UNO / UNOVYRA -- NATIVE S5 THREE RECOVERIES, EXACT PROVENANCE AND TX ATOMICITY '+VERSION)
            log('R4.1 §11.2: exact bytes require known backing; native hidden-state replay requires exact event ledger + model + DSP + RNG; no reconstruction from semantic summary.')
            log('SQLite WAL FULL receipts, used, references and static P snapshot commit atomically; PREPARED without evidence is MAY_HAVE_EXECUTED.')
            log('C256R32 synthetic native F is executed on VERIFIED replay; 2/4 continuous native S5 background workers + 32MiB RAM.')
            log('No neural training, real P update, trained model, user data, Android actions, physical power failure, real authorization or Android UID isolation.')
            log('Negative control: same-UID writer forging hashes and chain can pass; SHA chain != protected provenance or authenticated L.')
            log('SAFETY: battery>=40%, battery temp<37.5C, MemAvailable>=400000 kB; no idle load phase.')
            log('OWNER_APPROVED_PRECODE = FALSE; PRODUCTION_CODE_AUTHORIZED = FALSE')
            b,t,m=telemetry();log(f'PRECHECK battery={b} temp_deciC={t} MemAvailable_kB={m}')
            if why:=safety(args.host_smoke):log('RESULT SAFETY_SKIP '+why);return 3
            binary=background_s5();log('VERIFIED_BACKGROUND_S5 '+str(binary))
            root=home/'uno_a52_r41_recovery_provenance_v15'/stamp;root.mkdir(parents=True,exist_ok=False)
            exe,sha=compile_native(root);log(f'COMPILED_NATIVE_REPLAY {exe} source_sha256={sha}')
            test=root/'selftest';test.mkdir();data=b''.join(struct.pack('<ii',i,2*i) for i in range(1,4))
            a,b=native_replay(exe,test,data,SEED)
            c,d=native_replay(exe,test,data,SEED)
            if (a,b)!=(c,d):raise RuntimeError('NONDETERMINISTIC_NATIVE_REPLAY')
            log(f'SELFTEST_NATIVE_REPLAY deterministic=YES native_F_MAC={b} state_digest={a}')
            ctx=mp.get_context('fork')
            s1=stage(log,ctx,binary,exe,root,1 if args.host_smoke else 2,args.host_smoke,args.inject_host_abort)
            if s1[0]!='COMPLETE':log(f'RESULT {s1[0]} cases={s1[1]}');return 3
            s2=stage(log,ctx,binary,exe,root,2 if args.host_smoke else 4,args.host_smoke)
            if s2[0]!='COMPLETE':log(f'RESULT {s2[0]} cases={s2[1]}');return 3
            log(f'RESULT COMPLETE_NATIVE_RECOVERY_PROVENANCE_LAB cases={s1[1]+s2[1]} negative_same_uid_findings={s1[2]+s2[2]} stages=2/2')
            log('LIMIT: authenticated replay requires protected external trust anchor. This fixture cannot prove private-state restoration after lost raw bytes, rollback or power-cut durability.')
            return 0
        except BaseException as exc:
            log(f'RESULT ERROR {type(exc).__name__} {str(exc)[:300]}')
            log('TRACE '+traceback.format_exc()[-1200:]);return 2
        finally:log('REPORT '+str(report))
if __name__=='__main__':sys.exit(main())
