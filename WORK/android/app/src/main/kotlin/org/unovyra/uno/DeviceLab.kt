package org.unovyra.uno

import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.os.SystemClock
import org.json.JSONArray
import org.json.JSONObject
import org.unovyra.uno.core.*
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest

/** Deliberate manual offline lab. No network, no permissions, no interactions outside own sandbox. */
object DeviceLab {
    private fun hash(data:ByteArray):String = MessageDigest.getInstance("SHA-256").digest(data)
        .joinToString("") { "%02x".format(it) }

    /** Writes and reads app-owned diagnostics fixture only; no arbitrary filesystem access. */
    private fun storage(context:Context, size:Int, cancelled:()->Boolean): LabResult {
        val started=SystemClock.elapsedRealtimeNanos()
        if(cancelled())return LabResult("STORAGE_FSYNC_SHA256",LabStatus.ABORTED,0,emptyMap())
        val path=File(context.filesDir,"diagnostics").apply {
            check(isDirectory||mkdirs()) {"LAB_DIAGNOSTIC_DIRECTORY_UNAVAILABLE"}
        }
        val file=File(path,"uno_lab_owned_io_fixture.bin")
        val payload=ByteArray(size) { (it*7+11).toByte() }
        val expected=hash(payload)
        val wroteAt=SystemClock.elapsedRealtimeNanos()
        FileOutputStream(file,false).use { it.write(payload);it.fd.sync() }
        val wroteNs=SystemClock.elapsedRealtimeNanos()-wroteAt
        if(cancelled())return LabResult("STORAGE_FSYNC_SHA256",LabStatus.ABORTED,
            SystemClock.elapsedRealtimeNanos()-started,mapOf("written_bytes" to size.toString()))
        val readAt=SystemClock.elapsedRealtimeNanos()
        val actual=FileInputStream(file).use { it.readBytes() }
        val readNs=SystemClock.elapsedRealtimeNanos()-readAt
        val equal=actual.size==size && hash(actual)==expected
        return LabResult("STORAGE_FSYNC_SHA256",if(equal)LabStatus.PASS else LabStatus.FAIL,
            SystemClock.elapsedRealtimeNanos()-started,
            mapOf("bytes" to size.toString(), "fsync_write_ns" to wroteNs.toString(),
                "read_ns" to readNs.toString(), "hash_match" to equal.toString(),
                "note" to "app-private fixture, fsync return != verified crash durability"))
    }

    private fun labResult(r:LabResult, before:JSONObject, after:JSONObject):JSONObject {
        return JSONObject().put("scenario",r.name).put("status",r.status.name)
            .put("duration_ns",r.durationNanos)
            .put("details",JSONObject(r.details))
            .put("before",before).put("after",after)
    }

    fun run(context:Context,profile:LabProfile,ownerStop:LabStop):JSONObject {
        val started=SystemClock.elapsedRealtime()
        val results=JSONArray()
        val sample=LabSystemMetrics.snapshot(context)
        var lastGuardSample=0L
        var cachedGuard:String?=null
        fun abortReason():String? {
            if(ownerStop.isStopped() || Thread.currentThread().isInterrupted)return "STOP_OR_BACKGROUND"
            val now=SystemClock.elapsedRealtime()
            if(now-started>=profile.maxDurationMs)return "TIME_BUDGET"
            if(now-lastGuardSample>=1200L || lastGuardSample==0L) {
                lastGuardSample=now
                val battery=LabSystemMetrics.battery(context)
                val level=battery.optDouble("level_percent",Double.NaN)
                val temp=battery.optDouble("battery_temperature_c",Double.NaN)
                val thermal=LabSystemMetrics.thermal(context).optInt("thermal_status_code_or_null",-1)
                val lowMemory=LabSystemMetrics.memory(context).optBoolean("system_low_memory",false)
                cachedGuard=when {
                    lowMemory -> "SYSTEM_LOW_MEMORY"
                    level.isFinite() && level<15.0 -> "LOW_BATTERY"
                    temp.isFinite() && temp>=44.5 -> "BATTERY_TEMPERATURE_LIMIT"
                    Build.VERSION.SDK_INT>=29 && thermal>=PowerManager.THERMAL_STATUS_SEVERE -> "THERMAL_SEVERE"
                    else -> null
                }
            }
            return cachedGuard
        }
        fun abort():Boolean=abortReason()!=null
        fun step(label:String, fn:()->LabResult) {
            if(abort())return
            val before=LabSystemMetrics.snapshot(context)
            val result=runCatching{fn()}.getOrElse {
                LabResult(label,LabStatus.FAIL,0L,mapOf("exception_class" to it.javaClass.simpleName))
            }
            val after=LabSystemMetrics.snapshot(context)
            results.put(labResult(result,before,after))
        }
        // CPU sample size includes ≥20 rounds for useful p95; no neural-quality claims.
        step("CPU_FP32") { LabWorkloads.cpu(if(profile==LabProfile.QUICK)24 else 48,
            if(profile==LabProfile.QUICK)96 else 128,::abort,SystemClock::elapsedRealtimeNanos) }
        step("CPU_SUSTAINED") { LabWorkloads.sustainedCpu(
            if(profile==LabProfile.QUICK)1_000L else 25_000L,
            if(profile==LabProfile.QUICK)96 else 128,
            ::abort,SystemClock::elapsedRealtimeNanos) }
        step("CPU_PARALLEL") { LabWorkloads.parallelCpu(
            profile.parallelism,if(profile==LabProfile.QUICK)64 else 96,
            ::abort,SystemClock::elapsedRealtimeNanos) }
        step("QUEUE_STOP") { LabWorkloads.scheduler(profile.parallelism,
            if(profile==LabProfile.QUICK)1000 else 8000,::abort,SystemClock::elapsedRealtimeNanos) }
        step("HEAP_PRESSURE") { LabWorkloads.heap(profile.maxHeapMiB,::abort,SystemClock::elapsedRealtimeNanos) }
        step("INTEGRITY") { LabWorkloads.integrity(if(profile==LabProfile.QUICK)65_536 else 2_097_152,
            ::abort,SystemClock::elapsedRealtimeNanos) }
        step("STORAGE_FSYNC_SHA256") {storage(context,
            if(profile==LabProfile.QUICK)262_144 else 2_097_152,::abort)}
        if(!abort()) {
            val before=LabSystemMetrics.snapshot(context)
            val sensor=runCatching{SensorLab.sample(context,if(profile==LabProfile.QUICK)1000L else 4000L,::abort)}
            val after=LabSystemMetrics.snapshot(context)
            val status=when {
                sensor.isFailure -> LabStatus.FAIL
                sensor.getOrThrow().optBoolean("cancelled") -> LabStatus.ABORTED
                sensor.getOrThrow().optInt("available_in_this_run")==0 -> LabStatus.UNSUPPORTED
                sensor.getOrThrow().getJSONArray("results").let { array ->
                    (0 until array.length()).sumOf { index -> array.getJSONObject(index).optInt("count",0) }==0 } -> LabStatus.INCONCLUSIVE
                else -> LabStatus.PASS
            }
            results.put(JSONObject().put("scenario","SENSOR_STREAM")
                .put("status",status.name).put("before",before).put("after",after)
                .put("observation",sensor.getOrNull()?:JSONObject.NULL)
                .put("error_class_or_null",sensor.exceptionOrNull()?.javaClass?.simpleName?:JSONObject.NULL)
                .put("note","PASS means events recorded, not absolute measurement accuracy"))
        }
        return JSONObject().put("schema","UNO_OFFLINE_LAB_REPORT_1")
            .put("run_kind","OWNER_INITIATED_SANDBOX_ONLY")
            .put("profile",profile.name)
            .put("profile_limit_ms",profile.maxDurationMs)
            .put("started_wall_ms",sample.optLong("unix_time_ms"))
            .put("device_before",sample)
            .put("device_after",LabSystemMetrics.snapshot(context))
            .put("sensor_inventory",LabSystemMetrics.sensorInventory(context))
            .put("elapsed_wall_ms",SystemClock.elapsedRealtime()-started)
            .put("abort_reason_or_null",abortReason()?:JSONObject.NULL)
            .put("results",results)
            .put("android_apk_tested",true)
            .put("neural_quality_tested",false)
            .put("native_action_gate_tested",false)
            .put("physical_joules_measured",false)
            .put("no_external_effects",true)
    }

    /** Evidence stays in app-private storage. Never auto-delete or silently upload anything. */
    fun save(context:Context, report:JSONObject):File {
        val dir=File(context.filesDir,"diagnostics")
        check(dir.isDirectory||dir.mkdirs()) { "LAB_DIAGNOSTICS_DIR_UNAVAILABLE" }
        check((dir.listFiles()?.count {it.name.startsWith("uno_lab_report_") && it.name.endsWith(".json")}?:1000)<30) {
            "LAB_REPORT_QUOTA_REACHED_EXPORT_WITH_ADB_FIRST"
        }
        val stamp=System.currentTimeMillis()
        val name="uno_lab_report_${stamp}.json"
        val final=File(dir,name)
        check(!final.exists()) { "LAB_REPORT_ALREADY_EXISTS" }
        val tmp=File(dir,"$name.pending")
        val text=report.toString(2).toByteArray(Charsets.UTF_8)
        FileOutputStream(tmp).use { it.write(text);it.fd.sync() }
        check(tmp.renameTo(final)) { "LAB_REPORT_RENAME_FAILED" }
        return final
    }
}
