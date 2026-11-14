package org.unovyra.uno

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap

/** Explicit foreground-only sensor sampling, never registered as an always-on service. */
object SensorLab {
    private val types=listOf(Sensor.TYPE_ACCELEROMETER,Sensor.TYPE_GYROSCOPE,
        Sensor.TYPE_MAGNETIC_FIELD,Sensor.TYPE_LIGHT,Sensor.TYPE_PRESSURE,
        Sensor.TYPE_PROXIMITY,Sensor.TYPE_GRAVITY,Sensor.TYPE_ROTATION_VECTOR)

    fun sample(context:Context, durationMs:Long, cancelled:()->Boolean): JSONObject {
        require(durationMs in 100L..5_000L)
        val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val handlerThread=HandlerThread("UNO-Sensor-Lab").apply{start()}
        val handler=Handler(handlerThread.looper)
        data class Counters(var count:Int=0,var firstNs:Long=0,var lastNs:Long=0,
                            var maxDelayNs:Long=0,var outOfOrder:Int=0,var maskedInvalid:Int=0)
        val counters=ConcurrentHashMap<Int,Counters>()
        val registered=ArrayList<Sensor>()
        val listener=object:SensorEventListener {
            override fun onSensorChanged(event:SensorEvent) {
                val now=SystemClock.elapsedRealtimeNanos()
                val c=counters.getOrPut(event.sensor.type){Counters()}
                synchronized(c) {
                    if(c.count>0 && event.timestamp<c.lastNs) c.outOfOrder++
                    if(event.values.any { !it.isFinite() }) c.maskedInvalid++
                    if(c.count==0)c.firstNs=event.timestamp
                    c.count++
                    c.lastNs=event.timestamp
                    if(now>=event.timestamp) c.maxDelayNs=maxOf(c.maxDelayNs,now-event.timestamp)
                }
            }
            override fun onAccuracyChanged(sensor:Sensor,accuracy:Int) { /* not an independent physical truth */ }
        }
        val started=SystemClock.elapsedRealtime()
        var error:String?=null
        try {
            for (type in types) {
                if(cancelled())break
                val sensor=sm.getDefaultSensor(type) ?: continue
                val ok=runCatching{sm.registerListener(listener,sensor,SensorManager.SENSOR_DELAY_UI,handler)}
                    .onFailure {error=it.javaClass.simpleName}.getOrDefault(false)
                if(ok)registered.add(sensor)
            }
            while(!cancelled() && SystemClock.elapsedRealtime()-started<durationMs) {
                try { Thread.sleep(40) } catch (_:InterruptedException) { break }
            }
        } finally {
            sm.unregisterListener(listener)
            handlerThread.quitSafely()
            runCatching{handlerThread.join(500)}
        }
        val table=JSONArray()
        for (s in registered) {
            val c=counters[s.type] ?: Counters()
            table.put(JSONObject().put("type",s.type).put("name",s.name)
                .put("count",c.count).put("first_timestamp_ns",if(c.count>0)c.firstNs else JSONObject.NULL)
                .put("last_timestamp_ns",if(c.count>0)c.lastNs else JSONObject.NULL)
                .put("max_delivery_delay_ns",if(c.count>0)c.maxDelayNs else JSONObject.NULL)
                .put("out_of_order_count",c.outOfOrder).put("nonfinite_samples",c.maskedInvalid))
        }
        return JSONObject().put("schema","UNO_SENSOR_LAB_1")
            .put("available_in_this_run",registered.size)
            .put("duration_ms",SystemClock.elapsedRealtime()-started)
            .put("cancelled",cancelled()).put("error_or_null",error?:JSONObject.NULL)
            .put("results",table)
            .put("note","events are observations, not ground-truth sensor accuracy; missing != zero")
    }
}
