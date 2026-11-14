#!/usr/bin/env python3
"""UNOVYRA R4.1 precode experiment. Real ARM native S5 load during directed STOP/COMMIT races.
No production UNO, Android dispatch, real P learning or owner authentication.
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
import sqlite3
import subprocess
import sys
import time
import traceback

VERSION = 'UNO_R41_A52_S5_STOP_PRECOMMIT_RACE_STRESS_V2'
MiB = 1024 * 1024
SAFETY_BATTERY_MIN = 40
SAFETY_BATTERY_TEMP_MAX = 375  # deciC: battery sensor, NOT die temperature
SAFETY_MEMAVAILABLE_MIN = 400000  # kB


def readint(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


def memavail():
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        pass
    return None


def telemetry():
    return (readint('/sys/class/power_supply/battery/capacity'),
            readint('/sys/class/power_supply/battery/temp'), memavail())


def safety(allow_missing):
    b, t, m = telemetry()
    if not allow_missing and (b is None or t is None or not 150 <= t <= 800 or m is None):
        return 'MISSING_OR_INVALID_BATTERY_OR_MEMORY_SENSOR'
    if b is not None and b < SAFETY_BATTERY_MIN:
        return 'BATTERY_BELOW_40_PERCENT'
    if t is not None and 150 <= t <= 800 and t >= SAFETY_BATTERY_TEMP_MAX:
        return 'BATTERY_SENSOR_GE_37_5_C'
    if m is not None and m < SAFETY_MEMAVAILABLE_MIN:
        return 'MEMAVAILABLE_BELOW_400000_KB'
    return None


def dbopen(db):
    con = sqlite3.connect(str(db), timeout=3.0, isolation_level=None)
    con.execute('PRAGMA busy_timeout=3000')
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=FULL')
    return con


def dbinit(db):
    con = dbopen(db)
    try:
        con.execute('CREATE TABLE state (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, stopped INTEGER NOT NULL)')
        con.execute('INSERT INTO state VALUES(1,1,0)')
        for table in ('receipts', 'memory', 'plasticity'):
            con.execute('CREATE TABLE ' + table + '(ticket TEXT PRIMARY KEY)')
    finally:
        con.close()


def dbread(db):
    con = dbopen(db)
    try:
        state = tuple(con.execute('SELECT epoch,stopped FROM state WHERE id=1').fetchone())
        rows = [set(r[0] for r in con.execute('SELECT ticket FROM ' + t))
                for t in ('receipts', 'memory', 'plasticity')]
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        return {'state': state, 'rows': len(rows[0]),
                'atomic': rows[0] == rows[1] == rows[2], 'integrity': integrity}
    finally:
        con.close()


def controller(db, mode, work, stop, intent):
    """One SQLite writer. Deliberate barriers expose distinct STOP-check/COMMIT orderings."""
    c = None
    try:
        c = dbopen(db)
        c.execute('BEGIN IMMEDIATE')
        current = c.execute('SELECT epoch,stopped FROM state WHERE id=1').fetchone()
        if current != (1, 0):
            raise RuntimeError('controller_invalid_start_state')
        for table in ('receipts', 'memory', 'plasticity'):
            c.execute('INSERT INTO ' + table + ' VALUES (?)', ('single_synthetic_receipt',))
        precheck_ns = None
        if mode in ('NAIVE_POST_CHECK', 'RECHECK_POST_CHECK', 'COMMIT_FIRST'):
            if intent.value:
                raise RuntimeError('intent_set_before_precheck')
            precheck_ns = time.monotonic_ns()
        if mode == 'COMMIT_FIRST':
            commit_begin = time.monotonic_ns()
            c.execute('COMMIT')
            commit_done = time.monotonic_ns()
            work.send(('COMMIT_READY', precheck_ns, commit_begin, commit_done))
        else:
            work.send(('TX_STAGED', precheck_ns, time.monotonic_ns()))
            if not work.poll(8.0):
                raise TimeoutError('release_barrier_timeout')
            if work.recv() != ('RELEASE',):
                raise RuntimeError('bad_barrier_release')
            # Intent is a shared-memory STOP request set in the test parent BEFORE RELEASE.
            # A post-check recheck reduces the window but cannot prove its elimination.
            if mode in ('PRE_GATE', 'RECHECK_POST_CHECK') and intent.value:
                decision = 'ROLLBACK_STOP_INTENT'
                lastcheck = time.monotonic_ns()
                c.execute('ROLLBACK')
                commit_begin = commit_done = None
            else:
                decision = 'COMMIT'
                lastcheck = precheck_ns if mode == 'NAIVE_POST_CHECK' else time.monotonic_ns()
                commit_begin = time.monotonic_ns()
                c.execute('COMMIT')
                commit_done = time.monotonic_ns()
            work.send(('TX_DONE', decision, lastcheck, commit_begin, commit_done))
        # STOP is received through independent IPC; durable latch is a separate SQLite commit.
        if not stop.poll(8.0):
            raise TimeoutError('stop_ipc_timeout')
        item = stop.recv()
        if not (len(item) == 2 and item[0] == 'STOP'):
            raise RuntimeError('bad_stop_ipc')
        recv_ns = time.monotonic_ns()
        c.execute('BEGIN IMMEDIATE')
        c.execute('UPDATE state SET epoch=2, stopped=1 WHERE id=1')
        c.execute('COMMIT')
        latch_ns = time.monotonic_ns()
        stop.send(('STOP_ACK', item[1], recv_ns, latch_ns))
    except BaseException as ex:
        try:
            if c is not None and c.in_transaction:
                c.execute('ROLLBACK')
            work.send(('CONTROLLER_ERROR', type(ex).__name__, str(ex)[:120]))
        except (OSError, BrokenPipeError):
            pass
    finally:
        if c is not None:
            c.close()
        work.close()
        stop.close()


def resident_holder(mib, stop_event, ready):
    try:
        block = bytearray(mib * MiB)
        for i in range(0, len(block), 4096):
            block[i] = i // 4096 & 255
        ready.put(('READY', os.getpid(), mib), timeout=3)
        while not stop_event.wait(0.2):
            for i in range(0, len(block), 4096 * 64):
                block[i] ^= 1
    except BaseException as ex:
        try:
            ready.put(('ERROR', str(ex)[:100]), timeout=1)
        except Exception:
            pass


def native_s5_worker(binary, stop_event, outcomes):
    runs, values, errors = 0, [], []
    while not stop_event.is_set():
        try:
            p = subprocess.run([binary, 'rank', 'full', '1.0'],
                               capture_output=True, text=True, timeout=4.0)
            if p.returncode != 0 or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS', p.stdout):
                errors.append('S5_invalid:' + (p.stdout + p.stderr)[-130:])
                break
            m = re.search(r'estimated_F_GMAC_s=([0-9.]+)', p.stdout)
            if not m:
                errors.append('S5_no_throughput')
                break
            values.append(float(m.group(1)))
            runs += 1
        except BaseException as ex:
            errors.append(type(ex).__name__ + ':' + str(ex)[:100])
            break
    try:
        outcomes.put((os.getpid(), runs, min(values) if values else None,
                      sum(values)/len(values) if values else None, errors), timeout=2)
    except Exception:
        pass


def check_binary(log):
    folder = Path.home() / 'uno_a52_r41_operator_lab'
    exe = folder / 'uno_r41_s5_operator'
    if not (exe.is_file() and os.access(exe, os.X_OK)):
        source = folder / 'uno_r41_s5_operator.c'
        if not source.is_file():
            raise FileNotFoundError('Missing native S5: first run UNO_A52_R41_F_OPERATOR_BENCH.sh')
        p = subprocess.run(['clang', '-O3', '-fno-fast-math', '-std=c11', str(source), '-lm', '-o', str(exe)],
                           text=True, capture_output=True, timeout=40)
        if p.returncode:
            raise RuntimeError('native_clang_failed: ' + p.stderr[-200:])
        log('NATIVE_REBUILT_FROM_PREVIOUS_LAB_SOURCE')
    p = subprocess.run([str(exe), 'rank', 'prefix2', '0.3'],
                       text=True, capture_output=True, timeout=4)
    if p.returncode or not re.search(r'FIXED_MASK_CONTRACT[^\n]*status=PASS', p.stdout):
        raise RuntimeError('native_S5_validation_failed')
    return str(exe)


def recv(conn, expected, timeout=6.0):
    if not conn.poll(timeout):
        raise TimeoutError('IPC_no_reply_' + expected)
    msg = conn.recv()
    if msg[0] == 'CONTROLLER_ERROR':
        raise RuntimeError(str(msg))
    if msg[0] != expected:
        raise RuntimeError('IPC_expected_' + expected + '_got_' + str(msg))
    return msg


def run_case(ctx, db, mode, log, kill_before_latch=False):
    dbinit(db)
    work_parent, work_child = ctx.Pipe()
    ctrl_parent, ctrl_child = ctx.Pipe()
    intent = ctx.RawValue('i', 0)
    p = ctx.Process(target=controller, args=(str(db), mode, work_child, ctrl_child, intent))
    p.start()
    work_child.close(); ctrl_child.close()
    requested = None
    try:
        if mode == 'COMMIT_FIRST':
            msg = recv(work_parent, 'COMMIT_READY')
            committed_ns = msg[3]
            requested = time.monotonic_ns()
            intent.value = 1
            ctrl_parent.send(('STOP', requested))
            tx_result = 'COMMIT_BEFORE_STOP'
        else:
            ready = recv(work_parent, 'TX_STAGED')
            requested = time.monotonic_ns()
            intent.value = 1
            ctrl_parent.send(('STOP', requested))
            if kill_before_latch:
                # Controller is intentionally held IN AN OPEN TRANSACTION.
                # Kill before it can persist the STOP. Volatile intent is NOT durable.
                p.kill()
                p.join(timeout=3)
                if p.is_alive():
                    raise RuntimeError('crash_child_not_terminated')
                observed = dbread(db)
                finding = observed['state'] == (1, 0) and observed['rows'] == 0 and observed['integrity'] == 'ok'
                return {'mode': 'CRASH_BEFORE_LATCH', 'status': 'RACE_FINDING_VOLATILE_STOP_LOST' if finding else 'UNEXPECTED',
                        'ack_ms': None, 'gap_ms': None, 'committed_after_request': 0, 'data': observed,
                        'expected': finding}
            # Coordinated release intentionally places STOP in the last-check/COMMIT gap.
            work_parent.send(('RELEASE',))
            outcome = recv(work_parent, 'TX_DONE')
            tx_result, checked_ns, begin_ns, committed_ns = outcome[1:]
        ack = recv(ctrl_parent, 'STOP_ACK')
        now = time.monotonic_ns()
        if ack[1] != requested:
            raise RuntimeError('STOP_ACK_timestamp_mismatch')
        received_ns, latched_ns = ack[2:]
        p.join(timeout=2)
        if p.is_alive():
            raise RuntimeError('controller_stuck_after_stop')
        data = dbread(db)
        committed_after_request = int(committed_ns is not None and committed_ns > requested)
        committed_after_ack = int(committed_ns is not None and committed_ns > now)
        expected_rows = 0 if mode in ('PRE_GATE', 'RECHECK_POST_CHECK') else 1
        expected = (data['state'] == (2, 1) and data['rows'] == expected_rows
                    and data['atomic'] and data['integrity'] == 'ok' and not committed_after_ack)
        status = ('OBSERVED_COMMIT_AFTER_STOP_REQUEST' if mode == 'NAIVE_POST_CHECK' and committed_after_request else
                  'GUARDED_ROLLBACK' if mode in ('PRE_GATE', 'RECHECK_POST_CHECK') and data['rows'] == 0 else
                  'PRIOR_COMMIT_RETAINED' if mode == 'COMMIT_FIRST' and committed_ns < requested else 'UNEXPECTED')
        if not expected or status == 'UNEXPECTED':
            expected = False
            status = 'FAIL_INVARIANT'
        return {'mode': mode, 'status': status, 'expected': expected,
                'ack_ms': (now-requested)/1e6,
                'receive_ms': (received_ns-requested)/1e6,
                'latch_ms': (latched_ns-requested)/1e6,
                'gap_ms': (committed_ns-requested)/1e6 if committed_ns else None,
                'committed_after_request': committed_after_request,
                'data': data, 'commit_before_stop': mode == 'COMMIT_FIRST' and committed_ns < requested,
                'decision': tx_result}
    finally:
        if p.is_alive():
            p.kill()
            p.join(timeout=2)
        work_parent.close(); ctrl_parent.close()


def fmt(v):
    return '-' if v is None else '%.3f' % v


def percent_nearest(nums, q):
    if not nums:
        return None
    values = sorted(nums)
    import math
    return values[max(0, math.ceil(q/100 * len(values))-1)]


def stress_stage(name, nworkers, memory_mib, seconds, repetitions, binary, home, ctx, log, quick):
    stop_event = ctx.Event()
    result_q, ready_q = ctx.Queue(), ctx.Queue()
    workers = []
    holder = None
    started = time.monotonic()
    findings, guarded_fails, results = 0, 0, []
    try:
        if memory_mib:
            holder = ctx.Process(target=resident_holder, args=(memory_mib, stop_event, ready_q))
            holder.start()
            info = ready_q.get(timeout=5)
            if info[0] != 'READY':
                raise RuntimeError('memory_holder_failed_' + str(info))
            log('RAM_PRESSURE_STAGE allocated_touched_MiB=%d pid=%d' % (memory_mib, info[1]))
        for _ in range(nworkers):
            p = ctx.Process(target=native_s5_worker, args=(binary, stop_event, result_q))
            p.start(); workers.append(p)
        log('STAGE_BEGIN name=%s native_S5_workers=%d held_ram_MiB=%d min_duration_s=%d' %
            (name, nworkers, memory_mib, seconds))
        # S5 jobs are active for ALL trials. There is NO zero-worker phase.
        modes = ('PRE_GATE', 'NAIVE_POST_CHECK', 'RECHECK_POST_CHECK', 'COMMIT_FIRST')
        case_no = 0
        for rep in range(1, repetitions+1):
            for mode in modes:
                issue = safety(quick)
                if issue:
                    raise RuntimeError('SAFETY_ABORT_' + issue)
                case_no += 1
                db = home / ('%s_%03d_%s.sqlite3' % (name, case_no, mode))
                out = run_case(ctx, db, mode, log)
                results.append(out)
                if out['status'] == 'OBSERVED_COMMIT_AFTER_STOP_REQUEST':
                    findings += 1
                if not out['expected']:
                    guarded_fails += 1
                log('CASE stage=%s rep=%d mode=%s status=%s ack_ms=%s commit_minus_request_ms=%s rows=%d stopped=%d atomic=%s' %
                    (name, rep, mode, out['status'], fmt(out['ack_ms']), fmt(out['gap_ms']),
                     out['data']['rows'], out['data']['state'][1], out['data']['atomic']))
                # Short spacing varies actual scheduling under continuous S5 pressure.
                time.sleep((case_no % 3) * 0.004)
        issue = safety(quick)
        if issue:
            raise RuntimeError('SAFETY_ABORT_' + issue)
        crash = run_case(ctx, home / (name + '_CRASH_BEFORE_STOP_LATCH.sqlite3'),
                         'PRE_GATE', log, kill_before_latch=True)
        results.append(crash)
        if not crash['expected']:
            guarded_fails += 1
        log('CRASH_FINDING stage=%s status=%s rows=%d persisted_stop=%d crash_rollback=%s' %
            (name, crash['status'], crash['data']['rows'], crash['data']['state'][1], crash['data']['integrity']))
        while time.monotonic() < started+seconds:
            issue = safety(quick)
            if issue:
                raise RuntimeError('SAFETY_ABORT_' + issue)
            time.sleep(0.2)
        acks = [x['ack_ms'] for x in results if x.get('ack_ms') is not None]
        latch = [x.get('latch_ms') for x in results if x.get('latch_ms') is not None]
        log('STOP_TIMING stage=%s samples=%d ack_median_ms=%s ack_p95_nearest_rank_ms=%s ack_max_ms=%s latch_max_ms=%s' %
            (name, len(acks), fmt(percent_nearest(acks,50)),fmt(percent_nearest(acks,95)),fmt(max(acks)),fmt(max(latch))))
        log('PROTOCOL_OBSERVATIONS stage=%s cases=%d exposed_post_check_commits=%d strict_user_request_stop_NOT_PROVEN=YES volatile_crash_stop_lost=%s invariant_failures=%d' %
            (name,len(results),findings,crash['status']=='RACE_FINDING_VOLATILE_STOP_LOST',guarded_fails))
    finally:
        stop_event.set()
        for p in workers:
            p.join(timeout=2.5)
            if p.is_alive():
                p.kill();p.join(timeout=1)
        if holder is not None:
            holder.join(timeout=2)
            if holder.is_alive():
                holder.kill();holder.join(timeout=1)
        found=[]
        for _ in workers:
            try:
                found.append(result_q.get(timeout=1.0))
            except queue.Empty:
                log('S5_WORKER_MISSING_RESULT stage='+name)
                guarded_fails += 1
        for pid,runs,mn,avg,errs in found:
            log('S5_WORKER stage=%s pid=%d native_runs=%d min_GMAC_s=%s mean_GMAC_s=%s errors=%s' %
                (name,pid,runs,mn,avg,errs))
            if runs < 1 or errs:
                guarded_fails += 1
        result_q.cancel_join_thread();result_q.close()
        ready_q.cancel_join_thread();ready_q.close()
    if guarded_fails:
        log('STAGE_FAIL name=%s failures=%d' % (name,guarded_fails))
        return False, findings
    log('STAGE_COMPLETE name=%s expected_fixture_behaviors=PASS observed_vulnerable_window=%d' % (name,findings))
    return True, findings


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument('--quick', action='store_true', help='Smoke test on developer Linux; NOT the A52 stress result')
    a=arg.parse_args()
    dest = Path.home()/'storage'/'downloads'
    if not dest.is_dir() or not os.access(dest,os.W_OK):
        dest=Path.home()
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report = dest/('UNO_A52_R41_STOP_PRECOMMIT_NATIVE_STRESS_'+stamp+'.txt')
    f=report.open('x',encoding='utf-8')
    def log(s):
        print(s,flush=True)
        f.write(s+'\n');f.flush()
    try:
        log('UNO / UNOVYRA -- NATIVE S5 LOADED STOP / PRECOMMIT RACE + CRASH LAB '+VERSION)
        log('Actual native C256R32 FP32 S5 computes on Android CPU; Python orchestrates IPC/SQLite and timestamps.')
        log('No idle phase: 2 S5 workers / 32 MiB, then 4 S5 workers / 64 MiB for ALL directed race cases.')
        log('TEST: STOP before precommit gate; STOP after last check before COMMIT; final recheck; COMMIT before STOP; crash before durable STOP latch.')
        log('WARNING: deliberately vulnerable NAIVE_POST_CHECK mode is a NEGATIVE CONTROL; finding is expected, NOT proof production UNO is broken.')
        log('No Android actions, permission changes, user authentication, training, model weights, or real user STOP. OWNER_APPROVED_PRECODE = FALSE')
        log('SAFETY: battery>=40%, battery sensor<37.5C, MemAvailable>=400000 kB; Ctrl+C terminates test workers.')
        b,t,m=telemetry();log('PRECHECK battery=%s temp_deciC=%s memavailable_kB=%s' % (b,t,m))
        issue=safety(a.quick)
        if issue:
            log('RESULT SAFETY_SKIP '+issue)
            return 3
        exe=check_binary(log)
        log('VERIFIED_NATIVE_BINARY '+exe)
        root=Path.home()/'uno_a52_r41_stop_precommit_stress_lab'/stamp
        root.mkdir(parents=True,exist_ok=False,mode=0o700)
        ctx=mp.get_context('fork')
        plans=[('S5x2_RAM32',2,32,4,2),('S5x4_RAM64',4,64,5,2)] if a.quick else [
            ('S5x2_RAM32',2,32,14,5),('S5x4_RAM64',4,64,18,5)]
        ok_all=True; total_findings=0
        for name,n,ram,duration,reps in plans:
            issue=safety(a.quick)
            if issue:
                log('RESULT SAFETY_ABORT '+issue)
                return 3
            ok,count=stress_stage(name,n,ram,duration,reps,exe,root,ctx,log,a.quick)
            ok_all=ok_all and ok
            total_findings += count
            b,t,m=telemetry()
            log('STAGE_TELEMETRY stage=%s battery=%s temp_deciC=%s MemAvailable_kB=%s' % (name,b,t,m))
            if not ok:
                break
        log('RESULT '+('PASS_WITH_REPRODUCED_RACE_AND_CRASH_GAPS' if ok_all else 'FAIL_INVARIANT')+
            ' intentionally_vulnerable_commits_after_stop_request='+str(total_findings))
        log('UNRESOLVED strict user STOP request-to-commit guarantee; durable external stop intent across pre-latch controller crash.')
        log('LIMIT This tests deliberately staged interleavings under real ARM S5 compute, NOT probabilistic discovery of all races, Android control or a STOP SLA.')
        log('REPORT '+str(report))
        return 0 if ok_all else 2
    except KeyboardInterrupt:
        log('RESULT USER_INTERRUPTED')
        log('REPORT '+str(report))
        return 130
    except BaseException as ex:
        log('RESULT ERROR '+type(ex).__name__+' '+str(ex)[:220])
        log('TRACE '+traceback.format_exc().splitlines()[-1])
        log('REPORT '+str(report))
        return 2
    finally:
        f.close()

if __name__=='__main__':
    sys.exit(main())
