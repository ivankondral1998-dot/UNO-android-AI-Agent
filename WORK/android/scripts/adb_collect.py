#!/usr/bin/env python3
"""Offline, read-only Android measurement capture for the owner's own UNO debug APK.
No network, root, destructive test, permissions mutation, or GitHub Actions.
Optional --restart-uno only force-stops/restarts this package, never other apps.
"""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

PKG = "org.unovyra.uno.scaffold"
JSON_ALLOWED = re.compile(r"^(probe_latest\.json|uno_lab_report_[0-9]+\.json)$")


def run(adb, args, timeout=25):
    try:
        return subprocess.run([adb, *args], capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, b"", b"timeout")


def save(dst, cmd, proc):
    dst.write_bytes(proc.stdout)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "size": len(proc.stdout),
        "sha256": hashlib.sha256(proc.stdout).hexdigest(),
        "stderr": proc.stderr.decode("utf-8", "replace")[:700],
    }


def select_authorized_serial(raw: bytes, requested: str | None = None) -> str:
    """Never silently select a different phone when multiple USB/ADB devices are attached."""
    devices = {}
    for line in raw.decode("utf-8", "replace").splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0] != "List" and fields[0] != "*":
            devices[fields[0]] = fields[1]
    authorized = [key for key, state in devices.items() if state == "device"]
    if requested is not None:
        if requested not in authorized:
            raise RuntimeError("Requested ADB serial is not connected and authorized")
        return requested
    if len(authorized) != 1:
        raise RuntimeError(f"Expected exactly one authorized ADB device, found {len(authorized)}; specify --serial")
    return authorized[0]


def collect(out, serial=None, restart=False, expected_model=None):
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb not found. Install Android Platform Tools first.")
    devices = run(adb, ["devices", "-l"])
    if devices.returncode:
        raise RuntimeError("ADB device enumeration failed")
    selected = select_authorized_serial(devices.stdout, serial)
    common = ["-s", selected]
    model_probe = run(adb, common + ["shell", "getprop", "ro.product.model"])
    model = model_probe.stdout.decode("utf-8", "replace").strip()
    if model_probe.returncode != 0 or not model:
        raise RuntimeError("Cannot confirm selected Android device identity")
    if expected_model and model.casefold() != expected_model.casefold():
        raise RuntimeError("Selected Android device model differs from --expect-model")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = out / f"UNO_A52_LAB_{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": "UNO_LAB_ADB_CAPTURE_1", "utc": stamp,
                "package": PKG, "serial_recorded": bool(serial),
                "restart_own_package": restart, "device_model": model,
                "model_gate_applied": bool(expected_model), "records": {}}
    cmds = {
        "android_version.txt": ["shell", "getprop", "ro.build.version.release"],
        "android_api.txt": ["shell", "getprop", "ro.build.version.sdk"],
        "model.txt": ["shell", "getprop", "ro.product.model"],
        "package.txt": ["shell", "dumpsys", "package", PKG],
        "meminfo.txt": ["shell", "dumpsys", "meminfo", PKG],
        "procstats.txt": ["shell", "dumpsys", "procstats", "--hours", "1", PKG],
        "gfxinfo_framestats.txt": ["shell", "dumpsys", "gfxinfo", PKG, "framestats"],
        "battery.txt": ["shell", "dumpsys", "battery"],
        "thermalservice.txt": ["shell", "dumpsys", "thermalservice"],
        "power.txt": ["shell", "dumpsys", "power"],
        "disk.txt": ["shell", "df", "/data"],
    }
    if restart:
        # Explicit lab mode. This intentionally kills UNO only to exercise Activity recovery.
        cmds["uno_force_stop.txt"] = ["shell", "am", "force-stop", PKG]
        cmds["uno_restart.txt"] = ["shell", "am", "start", "-n", PKG+"/.UnoActivity"]
    for filename, cmd in cmds.items():
        proc = run(adb, common+cmd)
        manifest["records"][filename] = save(dest/filename, cmd, proc)
    pid = run(adb, common+["shell", "pidof", PKG])
    pidtxt = pid.stdout.decode("ascii", "ignore").strip()
    if re.fullmatch(r"[0-9]+", pidtxt):
        cmd = ["logcat", "-d", "-t", "2500", f"--pid={pidtxt}"]
        manifest["records"]["uno_logcat.txt"] = save(dest/"uno_logcat.txt", cmd, run(adb,common+cmd))
    listed = run(adb,common+["shell","run-as",PKG,"ls","files/diagnostics"])
    manifest["records"]["lab_files_index.txt"] = save(dest/"lab_files_index.txt", ["run-as",PKG,"ls"],listed)
    if listed.returncode == 0:
        for name in listed.stdout.decode("utf-8","replace").splitlines():
            if not JSON_ALLOWED.fullmatch(name):
                continue
            cmd=["exec-out","run-as",PKG,"cat",f"files/diagnostics/{name}"]
            proc=run(adb,common+cmd)
            if proc.returncode==0:
                manifest["records"][name] = save(dest/name,cmd,proc)
                try:
                    payload=json.loads(proc.stdout)
                    manifest["records"][name]["schema"] = payload.get("schema")
                except (json.JSONDecodeError,UnicodeDecodeError):
                    manifest["records"][name]["json_valid"] = False
            else:
                manifest["records"][name] = {"returncode":proc.returncode,"stderr":proc.stderr.decode("utf-8","replace")[:300]}
    # This manifest intentionally excludes PII from logcat; user should review before sharing.
    (dest/"MANIFEST.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Saved {len(manifest['records'])} records to {dest}")
    print("Privacy: inspect logcat, power/package outputs before sharing; no upload performed.")
    return dest


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="uno_lab_results",type=pathlib.Path)
    ap.add_argument("--serial",help="ADB device serial if multiple devices")
    ap.add_argument("--restart-uno",action="store_true",help="Explicitly force-stop/restart ONLY UNO")
    ap.add_argument("--expect-model",help="Abort if ro.product.model differs (for example SM-A525F)")
    args=ap.parse_args()
    try:
        collect(args.out,args.serial,args.restart_uno,args.expect_model)
    except Exception as e:
        print("ABORT:",e,file=sys.stderr)
        sys.exit(2)
