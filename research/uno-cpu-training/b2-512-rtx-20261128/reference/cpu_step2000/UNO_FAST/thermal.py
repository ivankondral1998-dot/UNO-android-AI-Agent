"""Cooperative CPU pacing; never overrides guard.admit or the supervisor.

All waits are bounded, and every poll performs the original hard admission.
No device power settings, process suspension or sensor emulation in production.
"""
import json
import math
import time
from guard import admit, MAX_TEMP

PAUSE_C = 70.0
RESUME_C = 62.0
MIN_IDLE = 0.0
IDLE_RATIO = 0.0
MAX_WAIT = 40.0
POLL = 0.5

class ThermalPacer:
    def __init__(self, sample=admit, clock=time.monotonic, sleep=time.sleep, report=None):
        self.sample, self.clock, self.sleep = sample, clock, sleep
        self.report = report or (lambda event: print(json.dumps(event), flush=True))
        self.cooling = False
        self.idle_until = 0.0

    def after_work(self, started):
        now = self.clock()
        self.idle_until = max(self.idle_until, now + max(MIN_IDLE, IDLE_RATIO * max(0., now-started)))

    def ready(self, phase, deadline=None):
        """Return False only on caller's wall budget. Hard failures always raise."""
        end = self.clock() + MAX_WAIT
        announced = False
        while True:
            stats = self.sample()
            temp = stats['cpu_package_c']
            if not math.isfinite(temp) or not 5 < temp < MAX_TEMP:
                raise RuntimeError(f'THERMAL_STOP: invalid or hard-limit temperature {temp}')
            now = self.clock()
            if temp >= PAUSE_C:
                self.cooling = True
            elif self.cooling and temp <= RESUME_C:
                self.cooling = False
            if deadline is not None and now >= deadline:
                return False
            if now >= end:
                raise RuntimeError(f'THERMAL_STOP: cooling timeout in {phase}; last saved boundary retained')
            if not self.cooling and now >= self.idle_until:
                if announced:
                    self.report({'thermal':'RESUME','phase':phase,'cpu_package_c':temp})
                return True
            if not announced:
                self.report({'thermal':'PAUSE','phase':phase,'cpu_package_c':temp,
                             'reason':'temperature' if self.cooling else 'duty_cycle'})
                announced = True
            remaining = min(end, deadline if deadline is not None else end) - now
            self.sleep(min(POLL, remaining))
