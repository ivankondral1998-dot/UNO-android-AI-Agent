package org.unovyra.uno

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import android.os.PowerManager
import android.os.SystemClock
import org.json.JSONArray
import org.json.JSONObject
import org.unovyra.uno.core.ProbeMath
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

/** WP-01: read-only hardware diagnostic. No privileged action, no network, no model weights. */
object DeviceProbe {
    private fun memoryInfo(context: Context): JSONObject {
        val self = Debug.MemoryInfo().also(Debug::getMemoryInfo)
        val total = ActivityManager.MemoryInfo()
        (context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(total)
        val heap = Runtime.getRuntime()
        return JSONObject()
            .put("self_pss_kib", self.totalPss)
            .put("self_private_dirty_kib", self.totalPrivateDirty)
            .put("system_avail_mem_bytes", total.availMem)
            .put("system_total_mem_bytes", total.totalMem)
            .put("system_low_memory", total.lowMemory)
            .put("java_heap_used_bytes", heap.totalMemory() - heap.freeMemory())
            .put("java_heap_max_bytes", heap.maxMemory())
    }
    private fun battery(context: Context): JSONObject {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL,-1) ?: -1
        val scale = intent?.getIntExtra(BatteryManager.EXTRA_SCALE,-1) ?: -1
        val status = intent?.getIntExtra(BatteryManager.EXTRA_STATUS,-1) ?: -1
        return JSONObject()
            .put("level_percent", if(level >= 0 && scale > 0) 100.0*level/scale else JSONObject.NULL)
            .put("charging_status_code", status)
            .put("level_raw",level).put("scale_raw",scale)
    }
    fun snapshot(context: Context): JSONObject {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val thermal = if(Build.VERSION.SDK_INT >= 29) pm.currentThermalStatus else -1
        return JSONObject()
            .put("schema", "UNO_DEVICE_PROBE_1")
            .put("record_kind", "READ_ONLY_OBSERVATION_NOT_NATIVE_READBACK")
            .put("model_loaded", false).put("os_actions_enabled", false)
            .put("wall_time_ms", System.currentTimeMillis())
            .put("elapsed_realtime_nanos", SystemClock.elapsedRealtimeNanos())
            .put("sdk",Build.VERSION.SDK_INT)
            .put("manufacturer",Build.MANUFACTURER).put("model", Build.MODEL)
            .put("abis",JSONArray(Build.SUPPORTED_ABIS.toList()))
            .put("battery",battery(context))
            .put("memory",memoryInfo(context))
            .put("thermal_status_code",thermal)
            .put("power_save_mode",pm.isPowerSaveMode)
    }

    /** Fixed workload, finite memory; approximate arithmetic throughput, NOT a neural quality test. */
    fun benchmark(rounds: Int = 24, n: Int = 64): JSONObject {
        require(rounds in 1..48 && n in 8..64)
        val left=FloatArray(n*n) { ((it*13)%53-26)*.001f }
        val right=FloatArray(n*n) { ((it*17)%47-23)*.001f }
        val result=FloatArray(n*n)
        val samples=ArrayList<Long>(rounds)
        var checksum = 0.0
        for (run in 0 until rounds) {
            val started=SystemClock.elapsedRealtimeNanos()
            for (i in 0 until n) for (j in 0 until n) {
                var v=0f
                for(k in 0 until n) v+=left[i*n+k]*right[k*n+j]
                result[i*n+j]=v
            }
            val dt=SystemClock.elapsedRealtimeNanos()-started
            samples.add(dt)
            checksum+=result[(run*97)%(n*n)].toDouble()
        }
        val stats=ProbeMath.summarize(samples)
        return JSONObject()
            .put("schema","UNO_CPU_PROBE_1")
            .put("workload","naive_fp32_matmul_loop_not_optimized")
            .put("matrix_n",n).put("rounds",rounds)
            .put("mac_per_round",n*n*n)
            .put("sample_nanos",JSONArray(samples))
            .put("p50_nanos",stats.p50Nanos)
            .put("p95_nanos",stats.p95Nanos)
            .put("p99_nanos",stats.p99Nanos)
            .put("min_nanos",stats.minNanos)
            .put("max_nanos",stats.maxNanos)
            .put("checksum",checksum)
            .put("not_measured",JSONArray(listOf("joules","neural_quality","native_kernels","device_throttling_causality")))
    }

    /**
     * Immutable provenance copy for an explicitly consented UNO memory observation.
     * Content-addressed file name, no overwrite of any existing diagnostic.
     * Unlike persist(latest), future diagnostics cannot invalidate the stored hash.
     */
    fun persistImmutable(context: Context, json: JSONObject): File {
        val bytes = json.toString(2).toByteArray(Charsets.UTF_8)
        require(bytes.isNotEmpty() && bytes.size <= 65_536) { "DIAGNOSTIC_BOUNDS" }
        val sha = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        val dir = File(context.filesDir, "diagnostics")
        check(dir.isDirectory || dir.mkdirs()) { "DIAGNOSTICS_DIRECTORY_UNAVAILABLE" }
        val target = File(dir, "observation-$sha.json")
        if (target.exists()) {
            check(target.isFile && target.length() == bytes.size.toLong() &&
                target.readBytes().contentEquals(bytes)) {
                "DIAGNOSTIC_EXISTING_HASH_MISMATCH"
            }
            return target
        }
        val temp = File.createTempFile("observation-", ".part", dir)
        try {
            FileOutputStream(temp).use { output ->
                output.write(bytes)
                output.fd.sync()
            }
            if (target.exists()) {
                check(target.isFile && target.length() == bytes.size.toLong() &&
                    target.readBytes().contentEquals(bytes)) {
                    "DIAGNOSTIC_RACE_COLLISION"
                }
                return target
            }
            check(temp.renameTo(target)) { "DIAGNOSTIC_IMMUTABLE_RENAME_FAILED" }
            check(target.isFile && target.length() == bytes.size.toLong()) {
                "DIAGNOSTIC_IMMUTABLE_WRITE_FAILED"
            }
            return target
        } finally {
            // Only our own temporary file. Never delete the source or any prior report.
            if (temp.exists()) temp.delete()
        }
    }

    /** Diagnostic-only app-private file; no SAF/network provider. Failure is reported to UI. */
    fun persist(context:Context, json:JSONObject):File {
        val dir=File(context.filesDir,"diagnostics")
        check(dir.isDirectory || dir.mkdirs()) { "DIAGNOSTICS_DIRECTORY_UNAVAILABLE" }
        val target=File(dir,"probe_latest.json")
        val tmp=File(dir,"probe_latest.tmp")
        FileOutputStream(tmp).use { out ->
            out.write(json.toString(2).toByteArray(Charsets.UTF_8))
            out.fd.sync()
        }
        check(tmp.renameTo(target)) { "DIAGNOSTICS_RENAME_FAILED" }
        return target
    }
}
