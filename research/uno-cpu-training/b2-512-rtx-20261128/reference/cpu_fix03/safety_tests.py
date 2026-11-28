"""Fault injection: no real corpus training and no hardware sensor claims."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import psutil
import guard
import supervise as sup
from boundary import save_boundary, load_boundary, previous, verified_bytes
from train001_backend import checkpoint, restore

class SafetyTests(unittest.TestCase):
    def log(self, path, value="48.25", offset=0, identifier="/amdcpu/0/temperature/2",
            name="Core (Tctl/Tdie)", partial=""):
        now=time.time()
        stamp=datetime.datetime.fromtimestamp(now+offset).strftime("%m/%d/%Y %H:%M:%S")
        path.write_text(f',{identifier},/gpu-amd/0/temperature/4\nTime,"{name}","GPU"\n{stamp},{value},40\n'+partial,encoding="utf-8")
        return now

    def test_csv_exact_id_locale_and_partial(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv"
            now=self.log(p,partial="11/26/2026 12:00")
            self.assertEqual(guard.read_log(p,now),48.25)

    def test_invalid_or_stale_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.csv"
            for kwargs in ({"value":"nan"},{"value":"inf"},{"value":""},{"value":"0"},
                           {"offset":-20},{"offset":20},{"identifier":"/gpu-amd/0/temperature/2"},
                           {"name":"GPU Core"}):
                with self.subTest(kwargs=kwargs):
                    now=self.log(p,**kwargs)
                    with self.assertRaises((ValueError,RuntimeError)):
                        guard.read_log(p,now)
            now=self.log(p)
            os.utime(p,(now-20,now-20))
            with self.assertRaisesRegex(RuntimeError,"stale"):
                guard.read_log(p,now)

    def test_thresholds_and_disk(self):
        ok={"rss_mib":100,"available_mib":2000,"system_cpu_pct":30}
        for sample, temp in ((dict(ok,rss_mib=4096),50),(dict(ok,available_mib=1536),50),
                             (dict(ok,system_cpu_pct=95),50),(ok,85)):
            with patch("guard.resources",return_value=sample),patch("guard.cpu_package_celsius",return_value=temp):
                with self.assertRaises(RuntimeError):
                    guard.admit()
        with patch("guard.resources",return_value=ok),patch("guard.cpu_package_celsius",return_value=50):
            self.assertEqual(guard.admit()["cpu_package_c"],50)
        with patch("guard.psutil.disk_usage",return_value=type("Disk",(),{"free":guard.MIN_DISK-1})()):
            with self.assertRaisesRegex(RuntimeError,"DISK_STOP"):
                guard.disk_admit(Path.cwd())

    def test_global_lock_across_output_directories(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LOCALAPPDATA":d}):
            with sup.machine_lock():
                p=subprocess.run([sys.executable,"-c","from supervise import machine_lock; exec('with machine_lock(): print(1)')"],
                    capture_output=True,text=True,timeout=10)
                self.assertNotEqual(p.returncode,0)
                self.assertIn("UNO_BUSY",p.stderr)
            with sup.machine_lock():
                pass

    def test_supervisor_fault_kills_worker(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LOCALAPPDATA":d}):
            target=Path(d)/"finished"
            count=0
            def fake(process=None):
                nonlocal count
                count+=1
                if count>=3:
                    raise RuntimeError("HOT_TEST")
            command=[sys.executable,"-c",f"import sys,time; sys.stdin.buffer.read(1); time.sleep(4); open({str(target)!r},'w').close()"]
            with self.assertRaisesRegex(RuntimeError,"HOT_TEST"):
                sup.supervise(command,[Path(d)],fake)
            self.assertFalse(target.exists())

    def test_worker_loses_heartbeat(self):
        p=subprocess.Popen([sys.executable,"-c","from supervise import heartbeat; import time; heartbeat(); time.sleep(20)"],stdin=subprocess.PIPE,bufsize=0)
        try:
            sup.send_lease(p.stdin.fileno())
            self.assertEqual(p.wait(timeout=9),75)
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
            p.stdin.close()

    def test_normal_supervised_exit(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LOCALAPPDATA":d}):
            result=sup.supervise([sys.executable,"-c","from supervise import heartbeat; heartbeat()"],[Path(d)],lambda p=None:None)
            self.assertEqual(result,0)

    def test_stale_and_future_heartbeat(self):
        import struct
        for stamp in (time.monotonic_ns()-sup.LEASE_NS-1_000_000,
                      time.monotonic_ns()+10_000_000_000):
            rd,wr=os.pipe()
            try:
                os.write(wr,struct.pack("<Q",stamp))
                with self.assertRaisesRegex(RuntimeError,"stale or future"):
                    sup.read_lease(rd)
            finally:
                os.close(wr);os.close(rd)

    def test_nonblocking_heartbeat_full_pipe(self):
        rd,wr=os.pipe()
        try:
            os.set_blocking(wr,False)
            failed=False
            for _ in range(1024):
                try:
                    n=os.write(wr,b"x"*4096)
                    if n!=4096:
                        failed=True
                        break
                except OSError:
                    failed=True
                    break
            self.assertTrue(failed,"pipe did not reach capacity")
            # Fill any residual space in units of eight bytes.
            for _ in range(512):
                try:
                    sup.send_lease(wr)
                except (OSError,RuntimeError):
                    break
            else:
                self.fail("full pipe did not reject heartbeat")
        finally:
            os.close(wr);os.close(rd)

    def test_monitor_timeout_stops_worker(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LOCALAPPDATA":d}):
            marker=Path(d)/"finished"
            calls=0
            def fake(process=None):
                nonlocal calls
                calls+=1
                if calls>=2:
                    time.sleep(10)
            command=[sys.executable,"-c",f"import time;from supervise import heartbeat;heartbeat();time.sleep(8);open({str(marker)!r},'w').close()"]
            start=time.monotonic()
            with self.assertRaisesRegex(RuntimeError,"telemetry check timed out"):
                sup.supervise(command,[Path(d)],fake)
            self.assertLess(time.monotonic()-start,7)
            self.assertFalse(marker.exists())

    def test_outer_deadline_stops_hung_worker(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LOCALAPPDATA":d}):
            command=[sys.executable,"-c","import time;from supervise import heartbeat;heartbeat();time.sleep(30)"]
            start=time.monotonic()
            with self.assertRaisesRegex(RuntimeError,"TIME_STOP"):
                sup.supervise(command,[Path(d)],lambda p=None:None,max_seconds=.6)
            self.assertLess(time.monotonic()-start,5)

    def test_lhm_requires_unique_process_and_fresh_instance(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"LibreHardwareMonitor.exe"
            info={"name":source.name,"exe":str(source),"create_time":time.time()}
            proc=SimpleNamespace(info=info)
            with patch("guard.psutil.process_iter",return_value=[proc,proc]):
                with self.assertRaisesRegex(RuntimeError,"exactly one"):
                    guard.log_source()
            with patch("guard.psutil.process_iter",return_value=[proc]):
                self.assertEqual(guard.log_source(),(source.parent,info["create_time"]))
            log=Path(d)/"sample.csv"
            now=self.log(log)
            with self.assertRaisesRegex(RuntimeError,"predates"):
                guard.read_log(log,now,not_before=now+2)

    def test_backup_link_and_copy_fallback(self):
        import boundary
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"latest.uno"
            checkpoint(p,{"step":1})
            inode=p.stat().st_ino
            save_boundary(lambda q:checkpoint(q,{"step":2}),p)
            self.assertEqual(restore(previous(p))["step"],1)
            self.assertEqual(restore(p)["step"],2)
            # Copy fallback for filesystems without hardlinks.
            with patch("boundary.os.link",side_effect=OSError("not supported")):
                save_boundary(lambda q:checkpoint(q,{"step":3}),p)
            self.assertEqual(restore(previous(p))["step"],2)
            self.assertEqual(restore(p)["step"],3)
            boundary.verify_file(p)

    @unittest.skipUnless(os.name=="nt","requires actual Windows")
    def test_windows_job_close_terminates_member(self):
        p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"])
        j=None
        try:
            j=sup.Job(p.pid)
            j.close()
            p.wait(timeout=10)
            self.assertNotEqual(p.returncode,0)
        finally:
            if j:j.close()
            if p.poll() is None:p.kill();p.wait(timeout=10)

    def test_backup_corruption_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"latest.uno"
            checkpoint(p,{"step":1})
            save_boundary(lambda path:checkpoint(path,{"step":2}),p)
            self.assertEqual(restore(p)["step"],2)
            self.assertEqual(restore(previous(p))["step"],1)
            p.write_bytes(b"corrupt")
            self.assertEqual(load_boundary(restore,p,quarantine=True)["step"],1)
            self.assertFalse(p.exists())
            self.assertEqual(len(list(Path(d).glob("latest.corrupt-*.uno"))),1)
            self.assertEqual(restore(previous(p))["step"],1)

    def test_kill_during_actual_atomic_commit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"latest.uno"
            marker=Path(d)/"inside-replace"
            checkpoint(p,{"step":1})
            code=f"""
import os,time
from pathlib import Path
from boundary import save_boundary
from train001_backend import checkpoint
real=os.replace
def stop(src,dst):
    if Path(dst).name=='latest.uno':
        Path({str(marker)!r}).touch()
        time.sleep(120)
    real(src,dst)
os.replace=stop
save_boundary(lambda p:checkpoint(p,{{'step':2}}),Path({str(p)!r}))
"""
            child=subprocess.Popen([sys.executable,"-c",code])
            try:
                deadline=time.monotonic()+30
                while not marker.exists() and child.poll() is None and time.monotonic()<deadline:
                    time.sleep(.05)
                self.assertTrue(marker.exists(),"did not reach actual replacement")
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=10)
            self.assertEqual(restore(p)["step"],1)
            self.assertEqual(restore(previous(p))["step"],1)

if __name__=="__main__":
    unittest.main(verbosity=2)
