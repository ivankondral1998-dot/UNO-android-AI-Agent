package org.unovyra.uno

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.graphics.Color
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.unovyra.uno.core.*
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong

/** WP-01 offline test laboratory. No model weights, no executable Android-effect catalogue. */
class UnoActivity : Activity() {
    private val controller by lazy { TrustController(DenyAllAndroidPort(), DenyAllLedger()) }
    private val neural: NeuralPort = NoWeightsNeuralPort()
    private val worker = Executors.newSingleThreadExecutor()
    private val alive = AtomicBoolean(true)
    private val busy = AtomicBoolean(false)
    @Volatile private var labStop = LabStop()
    private lateinit var status: TextView
    private lateinit var report: TextView
    private val mainHandler = Handler(Looper.getMainLooper())
    private val heartbeatLateCount = AtomicLong(0)
    private val heartbeatMaxDelayMs = AtomicLong(0)
    private var expectedBeatMs=0L
    private val heartbeat=object:Runnable {
        override fun run() {
            if(!alive.get())return
            val now=SystemClock.uptimeMillis()
            if(expectedBeatMs>0L) {
                val delay=(now-expectedBeatMs).coerceAtLeast(0)
                if(delay>=350)heartbeatLateCount.incrementAndGet()
                heartbeatMaxDelayMs.accumulateAndGet(delay) { a,b -> maxOf(a,b) }
            }
            expectedBeatMs=now+250
            mainHandler.postDelayed(this,250)
        }
    }

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        val root=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setPadding(24,38,24,38)
            setBackgroundColor(Color.rgb(12,18,27))
        }
        fun label(s:String, size:Float=15f)=TextView(this).apply {
            text=s;textSize=size;setTextColor(Color.WHITE);setPadding(0,8,0,8)
        }
        root.addView(label("UNOVYRA / UNO 1.0 LAB",25f))
        status=label("Офлайн-лаборатория WP-01 · действий ОС нет · модель не загружена")
        root.addView(status)
        root.addView(label("Сценарии запускаются вручную. Жёсткий тест ограничен 45 секундами, STOP останавливает новые шаги.",13f))
        report=label("Исследования: https://uno-research.pages.dev/\nСайт не используется приложением. \nДля сохранённых JSON: adb run-as org.unovyra.uno.scaffold")
        root.addView(report)
        fun button(text:String,onClick:()->Unit) {
            root.addView(Button(this).apply { this.text=text;setOnClickListener{onClick()} })
        }
        button("Снимок состояния: RAM / CPU / батарея / тепло") { runSimple(false) }
        button("Каталог сенсоров и их характеристики") { runSensorInventory() }
        button("Быстрая лаборатория: CPU, память, IO, STOP, сенсоры") { runLab(LabProfile.QUICK) }
        button("ЖЁСТКАЯ лаборатория: нагрузки до 60 сек") { runLab(LabProfile.STRESS) }
        button("Нет обученной модели — проверить fail-closed") {
            status.text=try {
                neural.perceive(Percept(PerceptType.TEXT,byteArrayOf(0),"OWNER_UI",
                    SystemClock.elapsedRealtimeNanos(),true))
                "ERROR_UNEXPECTED_MODEL_OUTPUT"
            } catch (e:IllegalStateException) {e.message?:"MODEL_UNAVAILABLE"}
        }
        button("СТОП: прервать все тесты и запретить действия") {
            labStop.stop();controller.stop()
            status.text="STOP · тесты отменены · trusted epoch=${controller.epoch}"
        }
        setContentView(ScrollView(this).apply {addView(root)})
        mainHandler.post(heartbeat)
        reportFullyDrawn() // For full launch timing use separate physical-device Macrobenchmark.
    }

    private fun execute(label:String,action:()->Pair<JSONObject,String>) {
        if(!busy.compareAndSet(false,true)) { status.text="Уже запущен тест. Используй STOP.";return }
        status.text=label
        worker.execute {
            val result=runCatching{action()}
            busy.set(false)
            runOnUiThread {
                if(alive.get()) {
                    status.text=if(result.isSuccess) "Лаборатория: JSON сохранён в телефоне" else "Ошибка: тест не завершён"
                    report.text=if(result.isSuccess) {
                        val (json,path)=result.getOrThrow()
                        "Локально: $path\nUI late >=350ms: ${heartbeatLateCount.get()} " +
                        "max=${heartbeatMaxDelayMs.get()}ms\n" + json.toString(2).take(14000)
                    } else result.exceptionOrNull()?.javaClass?.simpleName?:"UNKNOWN"
                }
            }
        }
    }
    private fun runSimple(withCpu:Boolean) {
        execute("Чтение параметров устройства") {
            val json=LabSystemMetrics.snapshot(applicationContext)
            json.put("ui_heartbeat_delay_over_350ms",heartbeatLateCount.get())
            json.put("ui_max_heartbeat_delay_ms",heartbeatMaxDelayMs.get())
            if(withCpu) json.put("cpu",DeviceProbe.benchmark())
            json to DeviceProbe.persist(applicationContext,json).absolutePath
        }
    }
    private fun runSensorInventory() {
        execute("Получение каталога датчиков") {
            val json=JSONObject().put("schema","UNO_SENSOR_INVENTORY_1")
                .put("device",LabSystemMetrics.snapshot(applicationContext))
                .put("inventory",LabSystemMetrics.sensorInventory(applicationContext))
            json to DeviceProbe.persist(applicationContext,json).absolutePath
        }
    }
    private fun runLab(profile:LabProfile) {
        if(busy.get()) { status.text="Сначала заверши текущий тест или нажми STOP";return }
        labStop=LabStop()
        val stop=labStop
        execute("${profile.name}: проверки офлайн · никаких действий вне приложения") {
            val json=DeviceLab.run(applicationContext,profile,stop)
                .put("ui_heartbeat_delays_gt_350ms",heartbeatLateCount.get())
                .put("ui_max_heartbeat_delay_ms",heartbeatMaxDelayMs.get())
            json to DeviceLab.save(applicationContext,json).absolutePath
        }
    }
    override fun onPause(){labStop.stop();controller.stop();super.onPause()}
    override fun onDestroy(){alive.set(false);labStop.stop();mainHandler.removeCallbacks(heartbeat)
        worker.shutdownNow();controller.stop();super.onDestroy()}
}

/** The foundation app has no capability to perform native actions, even with consent. */
class DenyAllAndroidPort:NativePort {
    override val trustedSourceTag="ANDROID_NOT_IMPLEMENTED"
    override fun dispatch(ticket:Ticket):NativeEndpoint=NativeEndpoint.UNKNOWN
    override fun readback(ticket:Ticket,nowNanos:Long):NativeEvidence=
        NativeEvidence(ticket.id,NativeEndpoint.UNKNOWN,0,nowNanos,trustedSourceTag)
}
class DenyAllLedger:DurableLedger {
    override fun prepare(ticket:Ticket):Boolean=false
    override fun commit(ticket:Ticket,evidence:NativeEvidence):Boolean=false
    override fun unresolved():List<Ticket> = emptyList()
}
