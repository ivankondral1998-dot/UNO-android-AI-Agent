"""Guarded entry point; worker cannot start until supervisor admission."""
import argparse
import contextlib
import ctypes
import os
from pathlib import Path
import subprocess
import struct
import queue
import sys
import tempfile
import threading
import time
import psutil
from guard import admit, disk_admit, MAX_RSS, MIB

ROOT = Path(__file__).resolve().parent

@contextlib.contextmanager
def machine_lock():
    # All copies under the same Windows user share one lock.
    directory = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "UNO_CPU_TRAINING"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "training.lock").open("a+b") as f:
        if f.seek(0, 2) == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("UNO_BUSY: another guarded run is active") from exc
        yield

class Job:
    """Windows kill-on-close job. No training before successful assignment."""
    def __init__(self, pid):
        self.handle = None
        if os.name != "nt":
            return
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", w.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", w.DWORD),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", w.DWORD),
                        ("SchedulingClass", w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in
                        ("ReadOperationCount","WriteOperationCount","OtherOperationCount",
                         "ReadTransferCount","WriteTransferCount","OtherTransferCount")]
        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        k.SetInformationJobObject.restype = w.BOOL
        k.QueryInformationJobObject.argtypes = [w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
        k.QueryInformationJobObject.restype = w.BOOL
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.AssignProcessToJobObject.restype = w.BOOL
        k.CloseHandle.argtypes = [w.HANDLE]
        k.CloseHandle.restype = w.BOOL
        self.k = k
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = Extended()
            # Kernel commit budget (not equivalent to RSS) plus existing kill-on-close.
            info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0200
            info.JobMemoryLimit = MAX_RSS * MIB
            if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            observed = Extended()
            if not k.QueryInformationJobObject(self.handle,9,ctypes.byref(observed),ctypes.sizeof(observed),None):
                raise ctypes.WinError(ctypes.get_last_error())
            if ((observed.BasicLimitInformation.LimitFlags & 0x2200) != 0x2200
                    or observed.JobMemoryLimit != MAX_RSS*MIB):
                raise RuntimeError("JOB_LIMIT_NOT_CONFIRMED")
            proc = k.OpenProcess(0x0100 | 0x0001, False, pid)
            if not proc:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not k.AssignProcessToJobObject(self.handle, proc):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                k.CloseHandle(proc)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None

def terminate_tree(proc):
    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except psutil.NoSuchProcess:
        pass
    proc.wait(timeout=10)

LEASE_NS = 5_000_000_000

def send_lease(fd):
    # Python >=3.12 supports nonblocking Windows pipes; fail if unsupported.
    data = struct.pack("<Q", time.monotonic_ns())
    try:
        count = os.write(fd, data)
    except BlockingIOError as exc:
        raise RuntimeError("MONITOR_STOP: heartbeat pipe full") from exc
    if count != len(data):
        raise RuntimeError("MONITOR_STOP: incomplete heartbeat")

def read_lease(fd):
    data = bytearray()
    while len(data) < 8:
        chunk = os.read(fd, 8-len(data))
        if not chunk:
            raise RuntimeError("MONITOR_STOP: heartbeat EOF")
        data.extend(chunk)
    stamp = struct.unpack("<Q", data)[0]
    age = time.monotonic_ns()-stamp
    if not 0 <= age <= LEASE_NS:
        raise RuntimeError("MONITOR_STOP: stale or future heartbeat")
    return stamp

def bounded_check(fn, timeout=2.5):
    result = queue.Queue(maxsize=1)
    def call():
        try:
            result.put((True,fn()))
        except BaseException as exc:
            result.put((False,exc))
    threading.Thread(target=call,daemon=True).start()
    try:
        ok,value = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise RuntimeError("MONITOR_STOP: telemetry check timed out") from exc
    if not ok:
        raise value
    return value

def supervise(command, paths, admission=admit, max_seconds=None):
    def check(active):
        stats = admission(psutil.Process()) if active else admission()
        for path in paths:
            disk_admit(path)
        return stats
    with machine_lock():
        bounded_check(lambda:check(False))
        deadline = None if max_seconds is None else time.monotonic()+max_seconds
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, bufsize=0, cwd=ROOT)
        job = None
        try:
            job = Job(proc.pid)
            os.set_blocking(proc.stdin.fileno(),False)
            send_lease(proc.stdin.fileno())
            last_report = 0.
            while proc.poll() is None:
                if deadline is not None and time.monotonic() >= deadline:
                    raise RuntimeError("TIME_STOP: outer run deadline reached")
                # Includes supervisor, worker and worker descendants.
                try:
                    stats = bounded_check(lambda:check(True))
                    if deadline is not None and time.monotonic() >= deadline:
                        raise RuntimeError("TIME_STOP: outer run deadline reached")
                    if proc.poll() is None:
                        send_lease(proc.stdin.fileno())
                    now = time.monotonic()
                    if stats is not None and now - last_report >= 5:
                        import json
                        print(json.dumps({"monitor":stats}),flush=True)
                        last_report = now
                except BrokenPipeError:
                    # Worker has closed the pipe. Stop it if it has not exited.
                    if proc.poll() is None:
                        proc.wait(timeout=2)
                    break
                time.sleep(.25)
            return proc.wait(timeout=10)
        except BaseException:
            if job:
                job.close()
            if proc.poll() is None:
                terminate_tree(proc)
            raise
        finally:
            if job:
                job.close()
            proc.stdin.close()

def heartbeat():
    fd = sys.stdin.fileno()
    try:
        last = [read_lease(fd)]
    except (OSError,RuntimeError):
        raise SystemExit("SUPERVISOR_REQUIRED")
    def read_heartbeat():
        try:
            while True:
                last[0] = read_lease(fd)
        except (RuntimeError,OSError):
            os._exit(75)
    def deadline():
        while True:
            if time.monotonic_ns() - last[0] > LEASE_NS:
                os._exit(75)
            time.sleep(.2)
    threading.Thread(target=read_heartbeat, daemon=True).start()
    threading.Thread(target=deadline, daemon=True).start()


def worker(mode, args):
    heartbeat()
    import guard
    guard.MANAGED = True
    if mode == "train":
        # Set before importing PyTorch/BLAS (including their initialization).
        thread_parser = argparse.ArgumentParser(add_help=False)
        thread_parser.add_argument("--threads", type=int, default=1)
        options, _ = thread_parser.parse_known_args(args)
        if not 1 <= options.threads <= 12:
            raise ValueError("choose 1–12 CPU threads")
        for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[name] = str(options.threads)
        os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
        os.environ["KMP_BLOCKTIME"] = "0"
        if args and args[0] in {"train", "resume"}:
            from thermal import ThermalPacer
            ThermalPacer().ready("before_torch_import")
        import train
        sys.argv = ["train.py", *args]
        train.main()
    elif mode in {"acceptance", "safety_tests", "efficiency_tests", "audit_tests"}:
        import runpy
        sys.argv = [mode + ".py", *args]
        runpy.run_path(str(ROOT / (mode + ".py")), run_name="__main__")
    else:
        raise SystemExit("unknown worker mode")

def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--worker":
        worker(args[1], args[2:])
        return
    if not args or args[0] not in {"train","acceptance","safety_tests","efficiency_tests","audit_tests"}:
        raise SystemExit("usage: supervise.py train|acceptance|safety_tests|efficiency_tests|audit_tests ...")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output", type=Path, default=Path("uno_cpu_run"))
    parser.add_argument("--export", type=Path)
    parser.add_argument("--seconds",type=int,default=1800)
    known, _ = parser.parse_known_args(args[1:])
    if not 1 <= known.seconds <= 1800:
        raise SystemExit("invalid run time budget")
    paths = [ROOT, Path(tempfile.gettempdir()), known.output]
    if known.export:
        paths.append(known.export)
    try:
        # The existing loop budget is augmented by bounded startup/final-save time.
        # Full validation is separately monitored and not silently truncated.
        max_seconds = (known.seconds+60 if args[0]=="train" and len(args)>1
                       and args[1] in {"train","resume"} else
                       300 if args[0]!="train" or (len(args)>1 and args[1]=="check") else None)
        raise SystemExit(supervise([sys.executable,"-B",str(Path(__file__).resolve()),"--worker",*args], paths,
                                   max_seconds=max_seconds))
    except (RuntimeError, OSError, ValueError, psutil.Error) as exc:
        raise SystemExit(f"SAFE_STOP: {exc}")
    except KeyboardInterrupt:
        raise SystemExit("SAFE_STOP: interrupted; resume from last saved boundary")

if __name__ == "__main__":
    main()
