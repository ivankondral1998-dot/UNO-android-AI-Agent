#!/usr/bin/env python3
"""UNO R4.1 A52 PRECODE: actual native S5 load + SQLite single writer + STOP race stress.
This is an intentionally bounded *experiment*, not UNO production code.
OWNER_APPROVED_PRECODE = FALSE.
"""
from __future__ import annotations
import argparse
import datetime as dt
import multiprocessing as mp
import os
from pathlib import Path
import queue
import re
import signal
import sqlite3
import subprocess
import sys
import time
import traceback

VERSION = 'UNO_R41_A52_S5_STOP_CONCURRENCY_STRESS_V1'
MIB = 1024 * 1024
BATTERY_MIN = 40
BATTERY_TEMP_MAX = 375  # 37.5 C, battery sensor only
MEMAVAIL_MIN_KB = 400000


def nint(p):
    try: return int(Path(p).read_text().strip())
    except (OSError, ValueError): return None


def avail_kb():
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'): return int(line.split()[1])
    except (OSError, ValueError, IndexError): pass
    return None


def telemetry():
    return (nint('/sys/class/power_supply/battery/capacity'),
            nint('/sys/class/power_supply/battery/temp'), avail_kb())


def safety(strict=False):
    b, t, m = telemetry()
    if strict and (b is None or t is None or not 150 <= t <= 800 or m is None):
        return 'required_safety_telemetry_missing_or_invalid'
    if b is not None and b < BATTERY_MIN: return 'battery_below_40_percent'
    if t is not None and 150 <= t <= 800 and t >= BATTERY_TEMP_MAX: return 'battery_sensor_ge_37_5_C'
    if m is not None and m < MEMAVAIL_MIN_KB: return 'MemAvailable_below_400000_kB'
    return None


def open_db(db):
    con = sqlite3.connect(str(db), isolation_level=None, timeout=3.0)
    con.execute('PRAGMA busy_timeout=3000')
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=FULL')
    return con


def init_db(db):
    c = open_db(db)
    try:
        c.execute('CREATE TABLE trials(id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, stopped INTEGER NOT NULL)')
        c.execute('CREATE TABLE receipts(ticket TEXT PRIMARY KEY, trial INTEGER NOT NULL)')
        c.execute('CREATE TABLE used(ticket TEXT PRIMARY KEY)')
        c.execute('CREATE TABLE p_steps(ticket TEXT PRIMARY KEY)')
        c.execute('CREATE TABLE memory(ticket TEXT PRIMARY KEY)')
    finally: c.close()


def child_controller(db, ctrl, jobs):
    c = None
    history = {}
    try:
        c = open_db(db)
        while True:
            # High-priority control lane, independently of bounded data queue.
            if ctrl.poll(0):
                msg = ctrl.recv()
                cmd = msg[0]
                if cmd == 'START':
                    tid = msg[1]
                    c.execute('INSERT INTO trials(id,epoch,stopped) VALUES(?,1,0)', (tid,))
                    history[tid] = []
                    ctrl.send(('STARTED', tid, time.monotonic_ns()))
                elif cmd == 'STOP':
                    tid, sent = msg[1:3]
                    recv = time.monotonic_ns()
                    c.execute('BEGIN IMMEDIATE')
                    try:
                        c.execute('UPDATE trials SET stopped=1, epoch=epoch+1 WHERE id=? AND stopped=0', (tid,))
                        c.execute('COMMIT')
                    except BaseException:
                        if c.in_transaction: c.execute('ROLLBACK')
                        raise
                    latch = time.monotonic_ns()
                    ctrl.send(('STOP_ACK', tid, sent, recv, latch))
                elif cmd == 'QUERY':
                    tid = msg[1]
                    state = c.execute('SELECT epoch,stopped FROM trials WHERE id=?', (tid,)).fetchone()
                    tickets = [r[0] for r in c.execute('SELECT ticket FROM receipts WHERE trial=?', (tid,))]
                    credit = len(tickets)
                    other = [sum(c.execute('SELECT 1 FROM '+tbl+' WHERE ticket=?', (ticket,)).fetchone() is not None
                                 for ticket in tickets) for tbl in ('used','p_steps','memory')]
                    ctrl.send(('QUERY_OK', tid, state, credit, other, tuple(history.get(tid, ()))))
                elif cmd == 'CLOSE':
                    ctrl.send(('CLOSED',)); return
                else: raise RuntimeError('bad_control_message_'+str(cmd))
                continue
            if not jobs.poll(0.005):
                continue
            try:
                job = jobs.recv()
            except EOFError:
                return
            if not isinstance(job, tuple) or len(job) != 3 or job[0] != 'TICKET':
                raise RuntimeError('unexpected_data_message')
            _, tid, ticket = job
            # All state-changing database ops, including synthetic P credit, use one writer.
            c.execute('BEGIN IMMEDIATE')
            try:
                state = c.execute('SELECT epoch,stopped FROM trials WHERE id=?', (tid,)).fetchone()
                if state is None or state[0] != 1 or state[1] != 0:
                    c.execute('ROLLBACK'); continue
                if c.execute('SELECT 1 FROM used WHERE ticket=?', (ticket,)).fetchone():
                    c.execute('ROLLBACK'); continue
                c.execute('INSERT INTO receipts VALUES (?,?)', (ticket, tid))
                for tbl in ('used','p_steps','memory'):
                    c.execute('INSERT INTO '+tbl+' VALUES (?)', (ticket,))
                # Last cooperative priority probe: a later STOP can still race with COMMIT.
                if ctrl.poll(0):
                    c.execute('ROLLBACK'); continue
                c.execute('COMMIT')
                history.setdefault(tid, []).append(time.monotonic_ns())
            except BaseException:
                if c.in_transaction: c.execute('ROLLBACK')
                raise
    except BaseException as ex:
        try: ctrl.send(('CHILD_ERROR', type(ex).__name__, str(ex)[:160]))
        except (OSError, BrokenPipeError): pass
    finally:
        if c is not None: c.close()
        ctrl.close()


def memory_hold(mib, quit_event, ready):
    try:
        buf = bytearray(mib * MIB)
        for i in range(0, len(buf), 4096): buf[i] = (i // 4096) & 255
        ready.put(('READY', os.getpid(), mib), timeout=2)
        while not quit_event.wait(0.15):
            # touch a small number of pages so memory remains resident
            for i in range(0, len(buf), 4096 * 128): buf[i] ^= 1
    except BaseException as e:
        try: ready.put(('ERROR', str(e)[:160]), timeout=1)
        except Exception: pass


def s5_worker(binary, quit_event, result_queue):
    trials = 0
    gmac = []
    problems = []
    while not quit_event.is_set():
        try:
            run = subprocess.run([binary, 'rank', 'full', '3.0'],
                                 capture_output=True, text=True, timeout=6.0)
            if run.returncode != 0 or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS', run.stdout) or 'MEASURE events=' not in run.stdout:
                problems.append('exit='+str(run.returncode)+' '+(run.stderr or run.stdout)[-100:])
                break
            found = re.search(r'estimated_F_GMAC_s=([0-9.]+)', run.stdout)
            if found: gmac.append(float(found.group(1)))
            trials += 1
        except BaseException as e:
            problems.append(type(e).__name__+':'+str(e)[:100]);break
    try: result_queue.put((os.getpid(), trials, min(gmac) if gmac else None,
                          sum(gmac)/len(gmac) if gmac else None, problems), timeout=3)
    except Exception: pass


def binary_on_device(log):
    lab = Path.home() / 'uno_a52_r41_operator_lab'
    exe = lab / 'uno_r41_s5_operator'
    if exe.is_file() and os.access(exe, os.X_OK):
        return str(exe)
    src = lab / 'uno_r41_s5_operator.c'
    if src.is_file():
        log('BUILD native S5 from prior experiment source='+str(src))
        try:
            p = subprocess.run(['clang','-std=c11','-O3','-fno-fast-math',str(src),'-lm','-o',str(exe)],
                               capture_output=True,text=True,timeout=35)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise RuntimeError('cannot_build_native_S5_'+str(e))
        if p.returncode: raise RuntimeError('clang_failed: '+p.stderr[-300:])
        return str(exe)
    raise RuntimeError('Native S5 benchmark not found. Run existing UNO_A52_R41_F_OPERATOR_BENCH.sh first; it creates '+str(src))


def req(ch, m, expected, timeout=8.0):
    ch.send(m)
    if not ch.poll(timeout): raise RuntimeError('controller_timeout_'+str(expected))
    reply = ch.recv()
    if reply[0] == 'CHILD_ERROR': raise RuntimeError(str(reply))
    if reply[0] != expected: raise RuntimeError('unexpected_reply_'+str(reply))
    return reply


def percentile(values, pct):
    xs = sorted(values)
    if not xs: return 0
    return xs[max(0, int((len(xs) * pct + 99) // 100) - 1)]


def stage(name, workers, hold_mib, seconds, ctx, binary, home, log, serial, strict_safety):
    db = home / (name+'.sqlite3')
    init_db(db)
    job_reader, job_writer = ctx.Pipe(duplex=False)
    parent, child = ctx.Pipe(duplex=True)
    proc = ctx.Process(target=child_controller, args=(str(db), child, job_reader), name='UNO_LAB_CONTROLLER')
    quit_event = ctx.Event()
    results = ctx.Queue()
    mem_ready = ctx.Queue()
    mem_proc = None
    burns = []
    proc.start(); child.close(); job_reader.close()
    try:
        if hold_mib:
            mem_proc = ctx.Process(target=memory_hold, args=(hold_mib, quit_event, mem_ready))
            mem_proc.start()
            msg = mem_ready.get(timeout=5.0)
            if msg[0] != 'READY': raise RuntimeError('memory_holder_'+str(msg))
            log('MEMORY_PRESSURE allocated_touched_MiB=%d pid=%d' % (hold_mib,msg[1]))
        for _ in range(workers):
            p=ctx.Process(target=s5_worker,args=(binary,quit_event,results))
            p.start();burns.append(p)
        log('STAGE_BEGIN name=%s s5_workers=%d resident_MiB=%d min_duration_s=%d' %
            (name,workers,hold_mib,seconds))
        started=time.monotonic()
        ack=[];receive=[];latch=[]; window=0; pre=0; post_ack=0; poststop_changes=0; anomalies=[]
        trials=0; submissions=0
        until=started + seconds
        target_trials = max(8, round(seconds * 3))
        while time.monotonic() < until and trials < target_trials:
            cycle_begin = time.monotonic()
            stop_reason=safety(strict_safety)
            if stop_reason:
                log('SAFETY_ABORT stage=%s reason=%s' % (name,stop_reason))
                raise RuntimeError('SAFETY_ABORT_'+stop_reason)
            tid=serial+trials
            req(parent,('START',tid),'STARTED')
            # A full queue of concurrent work is intended: STOP must bypass the data queue.
            for i in range(32):
                job_writer.send(('TICKET',tid,'t%06d_%04d' % (tid,i)))
                submissions += 1
            # Deliberately vary interleaving so STOP can arrive during SQLite COMMIT.
            time.sleep((trials % 7) * 0.00029)
            stop_sent=time.monotonic_ns()
            reply=req(parent,('STOP',tid,stop_sent),'STOP_ACK')
            t_ack=time.monotonic_ns()
            _,got_id,sent_ts,recv_ts,latch_ts=reply
            if got_id!=tid or sent_ts!=stop_sent:raise RuntimeError('wrong_stop_ACK')
            ack.append((t_ack-stop_sent)/1e6)
            receive.append((recv_ts-stop_sent)/1e6)
            latch.append((latch_ts-stop_sent)/1e6)
            # Verify post-STOP new work cannot advance this trial's synthetic P / receipts.
            before=req(parent,('QUERY',tid),'QUERY_OK')
            _,_,state,credits,other,events=before
            if state != (2,1): anomalies.append('not_stopped_'+str(tid))
            if any(x != credits for x in other): anomalies.append('atomicity_'+str(tid))
            pre+=credits
            window+=sum(stop_sent < t <= latch_ts for t in events)
            post_ack+=sum(t > t_ack for t in events)
            for x in range(4):
                job_writer.send(('TICKET',tid,'late_%06d_%d' % (tid,x)))
            # Let the old queued tickets drain while next trial is prepared.
            time.sleep(0.012)
            after=req(parent,('QUERY',tid),'QUERY_OK')
            if after[3] != credits:
                poststop_changes += 1
                anomalies.append('post_stop_commit_'+str(tid))
            if after[2] != (2,1): anomalies.append('stop_not_durable_'+str(tid))
            trials+=1
            if trials % 20 == 0:
                b,t,m=telemetry()
                log('PROGRESS stage=%s trials=%d ack_max_ms=%.3f race_window_commits=%d battery=%s temp_deciC=%s avail_kB=%s' %
                    (name,trials,max(ack),window,b,t,m))
            # Spread STOP races over the entire native S5 load interval.
            time.sleep(max(0.0, seconds / target_trials - (time.monotonic() - cycle_begin)))
        while time.monotonic() < until:
            why = safety(strict_safety)
            if why: raise RuntimeError('SAFETY_ABORT_'+why)
            time.sleep(0.20)
        # Ensure final latched trial remains intact after the controller is force-killed.
        proc.kill();proc.join(timeout=3)
        if proc.is_alive(): raise RuntimeError('controller_not_terminated')
        con = open_db(db)
        try:
            integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
            total=con.execute('SELECT count(*) FROM receipts').fetchone()[0]
            n_p=con.execute('SELECT count(*) FROM p_steps').fetchone()[0]
            n_mem=con.execute('SELECT count(*) FROM memory').fetchone()[0]
            n_used=con.execute('SELECT count(*) FROM used').fetchone()[0]
            last=con.execute('SELECT epoch,stopped FROM trials WHERE id=?',(serial+trials-1,)).fetchone()
            ticket_sets=[{r[0] for r in con.execute('SELECT ticket FROM '+table)} for table in ('receipts','used','p_steps','memory')]
            ticket_sets_match=all(ts==ticket_sets[0] for ts in ticket_sets)
        finally:con.close()
        if not (integrity=='ok' and total==n_p==n_mem==n_used and ticket_sets_match and last==(2,1)):
            anomalies.append('crash_recovery_integrity_or_atomicity')
        # Check that real S5 native processes actually computed and validated.
        quit_event.set()
        for p in burns:
            p.join(timeout=4.7)
            if p.is_alive():
                p.kill();p.join(timeout=2)
                anomalies.append('S5_worker_forced_kill_'+str(p.pid))
        got_reports=[]
        for _ in burns:
            try:
                got_reports.append(results.get(timeout=1.5))
            except queue.Empty:
                anomalies.append('S5_worker_missing_report')
        for pid, runs, mn, avg, problems in got_reports:
            log('S5_WORKER pid=%d native_3s_runs=%d min_GMAC_s=%s mean_GMAC_s=%s errors=%s' %
                (pid,runs,mn,avg,problems))
            if runs < 1 or problems:
                anomalies.append('S5_native_execution_problem_'+str(pid))
        if post_ack:
            anomalies.append('commit_after_STOP_ACK_'+str(post_ack))
        log('STOP_STATS stage=%s trials=%d submitted=%d committed_pre_or_race=%d '
            'ack_p50_ms=%.3f ack_p95_nearest_rank_ms=%.3f ack_max_ms=%.3f '
            'receive_max_ms=%.3f latch_max_ms=%.3f '
            'COMMIT_DONE_AFTER_STOP_REQUEST_BEFORE_LATCH=%d '
            'COMMIT_DONE_AFTER_ACK=%d post_stop_count_change=%d db_integrity=%s atomic_counts=%d/%d/%d/%d' %
            (name,trials,submissions,pre,percentile(ack,50),percentile(ack,95),max(ack),
             max(receive),max(latch),window,post_ack,poststop_changes,integrity,total,n_p,n_mem,n_used))
        if anomalies:
            log('STAGE_FAIL stage=%s anomalous=%s' % (name,','.join(anomalies[:15])))
            return False, window
        log('STAGE_PASS stage=%s synthetic_post_latch_commits=0 persisted_stop_after_crash=YES '
            'stop_request_race_window=%d (not_a_proven_strict_STOP_policy)' % (name,window))
        return True, window
    finally:
        quit_event.set()
        for p in burns:
            p.join(timeout=4.5)
            if p.is_alive():p.kill();p.join(timeout=2)
        if mem_proc is not None:
            mem_proc.join(timeout=2)
            if mem_proc.is_alive():mem_proc.kill();mem_proc.join(timeout=1)
        if proc.is_alive():
            try:req(parent,('CLOSE',),'CLOSED',timeout=1)
            except (OSError,EOFError,RuntimeError):pass
            proc.join(timeout=1)
            if proc.is_alive():proc.kill();proc.join(timeout=1)
        parent.close();job_writer.close()
        results.cancel_join_thread();results.close()
        mem_ready.cancel_join_thread();mem_ready.close()


def main():
    p=argparse.ArgumentParser(description='Bounded S5 + STOP concurrency stress (NOT production)')
    p.add_argument('--quick',action='store_true',help='Local smoke test only; not a stress result')
    args=p.parse_args()
    downloads=Path.home()/'storage'/'downloads'
    if not downloads.is_dir() or not os.access(downloads,os.W_OK):downloads=Path.home()
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report=downloads/('UNO_A52_S5_STOP_CONCURRENCY_STRESS_R41_'+stamp+'.txt')
    fp=report.open('x',encoding='utf-8')
    def log(s):
        print(s,flush=True)
        fp.write(s+'\n');fp.flush()
    try:
        log('UNO / UNOVYRA R4.1 -- REAL NATIVE S5 UNDER STOP+SQLITE CONCURRENCY '+VERSION)
        log('Experimental C256R32 native FP32 S5 + parallel CPU load, 32-ticket queue, one SQLite writer, STOP priority lane, memory pressure, crash-readback.')
        log('NOT: true Android STOP, user auth, Android actions, real P weights, hard real-time guarantee, production code.')
        log('Strict distinction: STOP sent != STOP received != STOP latched; commits in between are RACE_WINDOW observations, not automatic protocol violations.')
        log('SAFETY: battery>=40%; battery temp<37.5C; MemAvailable>=400000 kB; max four native S5 processes + 64 MiB holder.')
        log('OWNER_APPROVED_PRECODE = FALSE')
        b,t,m=telemetry();log('PRECHECK battery=%s temp_deciC=%s MemAvailable_kB=%s' % (b,t,m))
        strict_safety=not args.quick
        why=safety(strict_safety)
        if why:
            log('RESULT SKIPPED_SAFETY '+why);return 3
        binary=binary_on_device(log)
        log('NATIVE_BINARY '+binary)
        home=Path.home()/'uno_a52_r41_s5_stop_concurrency_lab'/stamp
        home.mkdir(parents=True,exist_ok=False,mode=0o700)
        ctx=mp.get_context('fork')
        configs=[('IDLE',0,0,2),('S5x2_RAM32',2,32,4),('S5x4_RAM64',4,64,5)] if args.quick else [
            ('IDLE',0,0,8),('S5x2_RAM32',2,32,20),('S5x4_RAM64',4,64,28)]
        good=True
        total_race_windows=0
        for i,(name,cores,mib,dur) in enumerate(configs):
            if safety(strict_safety):
                log('RESULT ABORT_SAFETY before_stage='+name+' reason='+str(safety(strict_safety)))
                return 3
            ok, race_count=stage(name,cores,mib,dur,ctx,binary,home,log,(i+1)*100000,strict_safety)
            total_race_windows+=race_count
            good=good and ok
            b,t,m=telemetry();log('STAGE_TELEMETRY name=%s battery=%s temp_deciC=%s MemAvailable_kB=%s' % (name,b,t,m))
            if not ok:break
        result='FAIL_INVARIANT' if not good else ('PASS_WITH_STOP_REQUEST_RACE_WINDOW_FINDINGS' if total_race_windows else 'PASS_NO_RACE_WINDOW_OBSERVED')
        log('RESULT '+result+' stop_request_window_commits='+str(total_race_windows))
        log('NOT_CLEARED: no strict guarantee that the first user STOP request precedes all subsequent durable commits.')
        log('LIMIT: no power-cycle durability, no real OS dispatch, no model trained; high CPU work is synthetic C256R32 S5 with repeatable fake weights.')
        log('LIMIT: 32 queued per trial, timing distribution limited to one run; scheduled CPU/core affinity, SoC die temperature, joules not measured.')
        log('REPORT '+str(report))
        return 0 if good else 2
    except KeyboardInterrupt:
        log('RESULT STOPPED_BY_USER')
        log('REPORT '+str(report))
        return 130
    except BaseException as ex:
        log('RESULT ERROR '+type(ex).__name__+' '+str(ex)[:240])
        log('TRACE '+traceback.format_exc().splitlines()[-1])
        log('REPORT '+str(report))
        return 2
    finally:fp.close()


if __name__=='__main__':sys.exit(main())
