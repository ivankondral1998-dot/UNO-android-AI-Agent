"""Fail-closed local telemetry for LibreHardwareMonitor 0.9.6 CSV."""
import csv
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
import psutil

MIB = 1024 * 1024
MAX_AGE = 5.0
MAX_TEMP = 85.0
MAX_RSS = 4096
MIN_AVAILABLE = 1536
MAX_CPU = 95.0
MIN_DISK = 512 * MIB
SENSOR = re.compile(r"^/(amd|intel)cpu/\d+/temperature/\d+$")
NAMES = {"CPU Package", "Core (Tctl/Tdie)", "CPU (Tctl/Tdie)"}
FILE_PATTERN = re.compile(r"LibreHardwareMonitorLog-\d{4}-\d{2}-\d{2}(?:-\d+)?\.csv$")
MAX_LINE = 128 * 1024

def log_source():
    # Require exactly one identifiable live instance, not merely one directory.
    found = []
    for proc in psutil.process_iter(["name", "exe", "create_time"]):
        try:
            if (proc.info["name"] or "").casefold() == "librehardwaremonitor.exe":
                if not proc.info["exe"] or proc.info["create_time"] is None:
                    raise RuntimeError("LHM: unreadable running instance")
                found.append((Path(proc.info["exe"]).resolve().parent,proc.info["create_time"]))
        except psutil.NoSuchProcess:
            continue
    if len(found) != 1:
        raise RuntimeError("LHM: exactly one readable running LibreHardwareMonitor instance required")
    return found[0]


def read_log(path, now=None, not_before=None):
    now = time.time() if now is None else now
    with path.open("rb") as f:
        st = os.fstat(f.fileno())
        if not -1 <= now - st.st_mtime <= MAX_AGE:
            raise RuntimeError("LHM: stale or future log modification time")
        if not_before is not None and st.st_mtime < not_before:
            raise RuntimeError("LHM: file predates running process")
        headers = [f.readline(MAX_LINE + 1) for _ in range(2)]
        if any(len(h) > MAX_LINE or not h.endswith(b"\n") for h in headers):
            raise RuntimeError("LHM: invalid log headers")
        data_start = f.tell()
        start = max(data_start, st.st_size - 2 * MAX_LINE)
        f.seek(start)
        tail = f.read(2 * MAX_LINE)
    # Ignore an incomplete final row; never use an incomplete first row.
    if start > data_start:
        tail = tail.partition(b"\n")[2]
    lines = tail.split(b"\n")
    if len(lines) < 2:
        raise RuntimeError("LHM: no complete sample")
    raw = lines[-2]
    if len(raw) > MAX_LINE:
        raise RuntimeError("LHM: oversized sample")
    def row(b):
        return next(csv.reader([b.decode("utf-8-sig").rstrip("\r")], strict=True))
    ids, names, values = row(headers[0]), row(headers[1]), row(raw)
    if not (len(ids) == len(names) == len(values) and ids[0] == "" and names[0] == "Time"):
        raise RuntimeError("LHM: invalid CSV shape")
    if len(ids) != len(set(ids)):
        raise RuntimeError("LHM: duplicate sensor identifiers")
    stamp = datetime.strptime(values[0], "%m/%d/%Y %H:%M:%S").timestamp()
    if not -1 <= now - stamp <= MAX_AGE:
        raise RuntimeError("LHM: stale or future sample timestamp")
    if not_before is not None and stamp < math.floor(not_before):
        raise RuntimeError("LHM: sample predates running process")
    selected = [float(values[i]) for i in range(1, len(ids))
                if SENSOR.fullmatch(ids[i]) and names[i] in NAMES]
    if not selected or not all(math.isfinite(v) and 5 < v < 115 for v in selected):
        raise RuntimeError("LHM: no valid CPU Package/Tctl/Tdie sample")
    return max(selected)

def cpu_package_celsius():
    directory, started = log_source()
    candidates = []
    for path in directory.glob("LibreHardwareMonitorLog-*.csv"):
        if FILE_PATTERN.fullmatch(path.name) and path.is_file():
            candidates.append((path.stat().st_mtime_ns, path.name, path))
    if not candidates:
        raise RuntimeError("LHM: enable Log Sensors, interval 1 second")
    return read_log(max(candidates)[2], not_before=started)

def resources(process=None):
    machine = psutil.virtual_memory()
    process = process or psutil.Process()
    rss = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            rss += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return {"rss_mib": rss / MIB,
            "available_mib": machine.available / MIB,
            "system_cpu_pct": psutil.cpu_percent(interval=.1)}

def disk_admit(path):
    path = Path(path).resolve()
    while not path.exists():
        if path.parent == path:
            raise RuntimeError('DISK_STOP: inaccessible volume')
        path = path.parent
    if psutil.disk_usage(str(path)).free < MIN_DISK:
        raise RuntimeError("DISK_STOP: less than 512 MiB available")

def admit(process=None):
    result = resources() if process is None else resources(process)
    if result["rss_mib"] >= MAX_RSS or result["available_mib"] <= MIN_AVAILABLE:
        raise RuntimeError(f"memory stop: {result}")
    result["cpu_package_c"] = cpu_package_celsius()
    if result["cpu_package_c"] >= MAX_TEMP or result["system_cpu_pct"] >= MAX_CPU:
        raise RuntimeError(f"CPU resource stop: {result}")
    return result
