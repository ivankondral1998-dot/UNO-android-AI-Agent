package org.unovyra.uno

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.Sensor
import android.hardware.SensorManager
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import android.os.PowerManager
import android.os.Process
import android.os.StatFs
import android.os.SystemClock
import java.io.File
import org.json.JSONArray
import org.json.JSONObject

/** Read-only, no special permissions. A null value means unavailable, NOT zero. */
object LabSystemMetrics {
    private fun opt(value: Number?): Any = value ?: JSONObject.NULL
    private fun batteryIntent(context: Context): Intent? = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    private fun Int.notSentinel(): Int? = if (this == Int.MIN_VALUE) null else this
    private fun Long.notSentinel(): Long? = if (this == Long.MIN_VALUE) null else this

    fun battery(context: Context): JSONObject {
        val intent = batteryIntent(context)
        val bm = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        fun extra(key:String):Int? = intent?.getIntExtra(key,Int.MIN_VALUE)?.notSentinel()
        val level = extra(BatteryManager.EXTRA_LEVEL)
        val scale = extra(BatteryManager.EXTRA_SCALE)
        // Properties vary by OEM; never claim energy from amperes without voltage/time integration.
        val current = runCatching { bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW).notSentinel() }.getOrNull()
        val charge = runCatching { bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CHARGE_COUNTER).notSentinel() }.getOrNull()
        val energy = runCatching { bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_ENERGY_COUNTER).notSentinel() }.getOrNull()
        return JSONObject()
            .put("level_percent",opt(if(level!=null && scale!=null && scale>0) 100.0*level/scale else null))
            .put("battery_temperature_c",opt(extra(BatteryManager.EXTRA_TEMPERATURE)?.let { it / 10.0 }))
            .put("battery_voltage_mv",opt(extra(BatteryManager.EXTRA_VOLTAGE)))
            .put("battery_health_code",opt(extra(BatteryManager.EXTRA_HEALTH)))
            .put("battery_status_code",opt(extra(BatteryManager.EXTRA_STATUS)))
            .put("battery_plugged_code",opt(extra(BatteryManager.EXTRA_PLUGGED)))
            .put("current_now_microamp_or_null",opt(current))
            .put("charge_counter_microamp_hours_or_null",opt(charge))
            .put("energy_counter_nanowatt_hours_or_null",opt(energy))
            .put("current_sign_oem_dependent",true)
            .put("physical_joules_measured",false)
    }

    fun memory(context:Context): JSONObject {
        val self = Debug.MemoryInfo().also(Debug::getMemoryInfo)
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val system = ActivityManager.MemoryInfo().also(am::getMemoryInfo)
        val runtime = Runtime.getRuntime()
        val stats = JSONObject()
        for ((key,value) in Debug.getRuntimeStats()) {
            if (key.startsWith("art.gc") || key.startsWith("art.heap")) stats.put(key, value)
        }
        val storage=runCatching { StatFs(context.filesDir.absolutePath) }.getOrNull()
        return JSONObject()
            .put("self_pss_kib",self.totalPss)
            .put("self_private_dirty_kib",self.totalPrivateDirty)
            .put("self_dalvik_pss_kib",self.dalvikPss)
            .put("self_native_pss_kib",self.nativePss)
            .put("self_rss_kib", if(Build.VERSION.SDK_INT>=35) opt(runCatching{Debug.getRss()}.getOrNull()) else JSONObject.NULL)
            .put("native_heap_allocated_bytes",Debug.getNativeHeapAllocatedSize())
            .put("native_heap_free_bytes",Debug.getNativeHeapFreeSize())
            .put("java_heap_used_bytes",runtime.totalMemory()-runtime.freeMemory())
            .put("java_heap_committed_bytes",runtime.totalMemory())
            .put("java_heap_max_bytes",runtime.maxMemory())
            .put("available_system_ram_bytes",system.availMem)
            .put("total_system_ram_bytes",system.totalMem)
            .put("low_memory_threshold_bytes",system.threshold)
            .put("system_low_memory",system.lowMemory)
            .put("app_files_free_bytes",opt(storage?.availableBytes))
            .put("app_files_total_bytes",opt(storage?.totalBytes))
            .put("known_jvm_threads",Thread.getAllStackTraces().size)
            .put("gc_runtime_stats",stats)
    }

    fun thermal(context:Context): JSONObject {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val status: Int? = if(Build.VERSION.SDK_INT>=29) runCatching{pm.currentThermalStatus}.getOrNull() else null
        val headroom: Float? = if(Build.VERSION.SDK_INT>=30)
            runCatching{pm.getThermalHeadroom(0)}.getOrNull()?.takeIf { !it.isNaN() && it.isFinite() } else null
        return JSONObject().put("thermal_status_code_or_null",opt(status))
            .put("thermal_headroom_or_null",opt(headroom))
            .put("is_power_save_mode",pm.isPowerSaveMode)
            .put("is_device_idle_mode",pm.isDeviceIdleMode)
            .put("is_interactive",pm.isInteractive)
    }

    /** CPU frequencies in kHz from readable sysfs nodes, with explicit unavailability. */
    private fun cpuFrequencies():JSONArray {
        val out=JSONArray()
        for(core in 0 until 16) {
            val file=File("/sys/devices/system/cpu/cpu$core/cpufreq/scaling_cur_freq")
            if(!file.exists())continue
            val khz=runCatching{file.readText().trim().toLongOrNull()}.getOrNull()
            out.put(JSONObject().put("cpu",core).put("khz_or_null",opt(khz)))
        }
        return out
    }

    fun sensorInventory(context:Context): JSONObject {
        val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val sensors = runCatching { manager.getSensorList(Sensor.TYPE_ALL) }.getOrDefault(emptyList())
        val result=JSONArray()
        sensors.take(128).forEach { s ->
            result.put(JSONObject().put("type",s.type).put("name",s.name)
                .put("vendor",s.vendor).put("max_range",s.maximumRange)
                .put("resolution",s.resolution).put("min_delay_us",s.minDelay)
                .put("reporting_mode",s.reportingMode)
                .put("is_wake_up",s.isWakeUpSensor))
        }
        return JSONObject().put("count",sensors.size).put("recorded_count",result.length())
            .put("truncated",sensors.size>128).put("sensors",result)
    }

    fun snapshot(context:Context): JSONObject = JSONObject()
        .put("schema","UNO_LAB_METRICS_2")
        .put("record_kind","OBSERVATION_NOT_INDEPENDENT_ACTION_READBACK")
        .put("unix_time_ms",System.currentTimeMillis())
        .put("elapsed_realtime_ns",SystemClock.elapsedRealtimeNanos())
        .put("uptime_ms",SystemClock.uptimeMillis())
        .put("process_elapsed_cpu_ms",Process.getElapsedCpuTime())
        .put("process_pid",Process.myPid())
        .put("sdk",Build.VERSION.SDK_INT)
        .put("android_release",Build.VERSION.RELEASE)
        .put("manufacturer",Build.MANUFACTURER)
        .put("device_model",Build.MODEL)
        .put("supported_abis",JSONArray(Build.SUPPORTED_ABIS.toList()))
        .put("memory", memory(context))
        .put("cpu_frequency_khz_if_readable",cpuFrequencies())
        .put("battery", battery(context))
        .put("thermal", thermal(context))
        .put("network_used_by_lab",false)
        .put("app_android_effects_enabled",false)
        .put("trained_neural_model_loaded",false)
}
