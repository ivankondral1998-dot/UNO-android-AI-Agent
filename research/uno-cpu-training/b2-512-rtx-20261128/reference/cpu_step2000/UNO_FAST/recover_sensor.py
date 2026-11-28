"""FIX05 recovery launcher: retry only a transient invalid temperature sample.
Existing supervisor remains in charge; no worker runs while recovering telemetry.
Use only with an existing FIX05 checkpoint and the same training arguments.
"""
import argparse
import math
from pathlib import Path
import subprocess
import sys
import time

INVALID = 'LHM: no valid CPU Package/Tctl/Tdie sample'
MAX_RESTARTS = 12
RECOVERY_SECONDS = 10


def run_child(command):
    safe_stop = exception = None
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', bufsize=1) as child:
        try:
            for line in child.stdout:
                print(line, end='', flush=True)
                s = line.strip()
                if s.startswith('SAFE_STOP: '):
                    safe_stop = s[len('SAFE_STOP: '):]
                if s.startswith('RuntimeError: '):
                    exception = s[len('RuntimeError: '):]
            return child.wait(), safe_stop if safe_stop is not None else exception
        except KeyboardInterrupt:
            # Don't abandon an active guarded subprocess or start another one.
            child.wait()
            raise


def recover(sample, deadline, clock=time.monotonic, sleep=time.sleep):
    end = min(deadline, clock() + RECOVERY_SECONDS)
    while clock() < end:
        try:
            stats = sample()  # unchanged full guard, not cached CSV data
        except RuntimeError as exc:
            if str(exc) != INVALID:
                raise
        else:
            if clock() >= end:
                break
            return stats
        sleep(min(.5, max(0., end-clock())))
    raise RuntimeError('RECOVERY_STOP: no valid telemetry within recovery budget')


def loop(command, seconds, sample, run=run_child, clock=time.monotonic,
         sleep=time.sleep, report=print):
    deadline = clock() + seconds
    for attempt in range(MAX_RESTARTS + 1):
        remaining = math.floor(deadline-clock())
        if remaining < 1:
            return 1
        code, reason = run([*command, '--seconds', str(remaining)])
        if code == 0:
            return 0
        if reason != INVALID or attempt == MAX_RESTARTS:
            return code
        report('SENSOR_RECOVERY: worker exited; waiting for valid telemetry', flush=True)
        recover(sample, deadline, clock, sleep)
        report('SENSOR_RECOVERY: valid telemetry; resuming saved checkpoint', flush=True)
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--steps', type=int, default=2000)
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--seconds', type=int, default=600)
    p.add_argument('--warmup', type=int, choices=(16,1000), default=16)
    p.add_argument('--backend', choices=('flat','analytic','autograd'), default='flat')
    p.add_argument('--peak-lr', type=float, choices=(2e-4,4e-4,8e-4), default=2e-4)
    a = p.parse_args()
    if not (1 <= a.seconds <= 1800 and 1 <= a.steps <= 55225 and 1 <= a.threads <= 12):
        p.error('invalid resource budget')
    root = Path.cwd()
    if not (root/'supervise.py').is_file() or not (root/'guard.py').is_file():
        p.error('run in existing FIX05 directory')
    if not (a.output/'latest.uno').is_file():
        p.error('existing checkpoint required')
    from guard import admit
    cmd = [sys.executable, '-B', str(root/'supervise.py'), 'train', 'resume',
           '--corpus', str(a.corpus.resolve()), '--output', str(a.output.resolve()),
           '--steps', str(a.steps), '--threads', str(a.threads), '--warmup', str(a.warmup),
           '--backend', a.backend, '--peak-lr', str(a.peak_lr)]
    try:
        return loop(cmd, a.seconds, admit)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f'SAFE_STOP: {exc}', file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
