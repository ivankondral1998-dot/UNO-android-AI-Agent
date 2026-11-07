package org.unovyra.uno

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.unovyra.uno.core.*
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** WP-01 Foundation only. This UI cannot dispatch any system actions. */
class UnoActivity : Activity() {
    private val controller by lazy { TrustController(DenyAllAndroidPort(), DenyAllLedger()) }
    private val neural: NeuralPort = NoWeightsNeuralPort()
    private val worker = Executors.newSingleThreadExecutor()
    private val alive = AtomicBoolean(true)
    private lateinit var status: TextView
    private lateinit var report: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(30,45,30,40);setBackgroundColor(Color.rgb(12,18,27)) }
        fun label(s:String, size:Float=15f):TextView=TextView(this).apply {text=s;textSize=size;setTextColor(Color.WHITE);setPadding(0,10,0,10)}
        root.addView(label("UNOVYRA · UNO 1.0",26f))
        status=label("WP-01 FOUNDATION · нет обученных весов · все действия запрещены")
        root.addView(status)
        report=label("Исследования: https://uno-research.pages.dev/\nСайт не используется приложением для вычислений.")
        root.addView(report)
        fun button(text:String,onClick:()->Unit){root.addView(Button(this).apply {this.text=text;setOnClickListener {onClick()}})}
        button("Прочитать состояние устройства") { runProbe(false) }
        button("Измерить CPU (24 × 64³ MAC)") { runProbe(true) }
        button("Проверить отсутствие модели") {
            status.text=try {
                neural.perceive(Percept(PerceptType.TEXT,byteArrayOf(0),"OWNER_UI",android.os.SystemClock.elapsedRealtimeNanos(),true))
                "ERROR_UNEXPECTED_MODEL_OUTPUT"
            } catch (e:IllegalStateException) { e.message ?: "MODEL_UNAVAILABLE" }
        }
        button("STOP — запретить действия") {controller.stop();status.text="STOP активирован · epoch=${controller.epoch}"}
        setContentView(ScrollView(this).apply {addView(root)})
    }
    private fun runProbe(withCpu:Boolean) {
        val context=applicationContext
        status.text="Считывание (без действий Android)"
        worker.execute {
            val result=runCatching {
                val snapshot=DeviceProbe.snapshot(context)
                if(withCpu) snapshot.put("cpu",DeviceProbe.benchmark())
                val path=DeviceProbe.persist(context,snapshot)
                JSONObject().put("status","HOST_APP_FILE_CREATED_NOT_DEVICE_VERIFIED")
                    .put("path",path.absolutePath).put("observation",snapshot)
            }
            runOnUiThread {
                if(alive.get()) {
                    status.text=if(result.isSuccess) "Диагностика записана локально" else "Ошибка диагностики"
                    report.text=result.getOrNull()?.toString(2)?.take(12000) ?: result.exceptionOrNull()?.toString()
                }
            }
        }
    }
    override fun onPause() {super.onPause();controller.stop()}
    override fun onDestroy() {alive.set(false);worker.shutdownNow();controller.stop();super.onDestroy()}
}

/** Zero OS effects. Actual owner enrollment/permissions/readback belong to WP-02. */
class DenyAllAndroidPort: NativePort {
    override val trustedSourceTag="ANDROID_NOT_IMPLEMENTED"
    override fun dispatch(ticket:Ticket):NativeEndpoint=NativeEndpoint.UNKNOWN
    override fun readback(ticket:Ticket,nowNanos:Long):NativeEvidence=NativeEvidence(ticket.id,NativeEndpoint.UNKNOWN,0,nowNanos,trustedSourceTag)
}
class DenyAllLedger: DurableLedger {
    override fun prepare(ticket:Ticket):Boolean=false
    override fun commit(ticket:Ticket,evidence:NativeEvidence):Boolean=false
    override fun unresolved():List<Ticket> = emptyList()
}
