package org.unovyra.uno

import android.app.Activity
import android.content.Intent
import android.content.ClipData
import android.content.ClipboardManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.graphics.Color
import android.content.res.ColorStateList
import android.widget.CheckBox
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
    // Owner-initiated OS credential probe only; never a ticket to native dispatch.
    private val ownerGate by lazy { OwnerConsentState(AndroidDeviceCredentialPlatform(this)) }
    // Closed diagnostic scope is defined once in OwnerConsentState (R5.3 NOOP verb=2).
    private val ownerDiagnosticScope by lazy { OwnerConsentState.diagnosticNoopScope() }
    private val worker = Executors.newSingleThreadExecutor()
    private val alive = AtomicBoolean(true)
    private val busy = AtomicBoolean(false)
    @Volatile private var labStop = LabStop()
    private lateinit var status: TextView
    // Credential result is shown next to the owner buttons, not only off-screen at top.
    private lateinit var ownerFeedback: TextView
    private lateinit var report: TextView
    // Contains the full last JSON, not the truncated on-screen preview. UI-thread only.
    private var copyableReport: String? = null
    private lateinit var uiRoot: LinearLayout
    private val labels = ArrayList<TextView>()
    private val themeButtons = ArrayList<Button>()
    private var styleCheckbox: CheckBox? = null
    private val themeGate = UnoThemeGate()

    private fun restoreTheme() {
        val preferences = getSharedPreferences("uno_ui_theme", MODE_PRIVATE)
        val rgb = preferences.getInt("accent_rgb", UnoThemeColors.ORANGE) and 0xFFFFFF
        val tone = if (preferences.getString("tone", "DARK") == "LIGHT") ThemeTone.LIGHT else ThemeTone.DARK
        themeGate.setManually(UnoTheme(tone, rgb))
        themeGate.setConversationStyleConsent(preferences.getBoolean("style_consent", false))
    }

    private fun applyTheme() {
        val theme = themeGate.current
        val back = UnoThemeColors.background(theme.tone)
        uiRoot.setBackgroundColor(Color.rgb((back shr 16) and 255, (back shr 8) and 255, back and 255))
        val fg = if (theme.tone == ThemeTone.DARK) Color.WHITE else Color.rgb(22, 29, 42)
        labels.forEach { it.setTextColor(fg) }
        styleCheckbox?.setTextColor(fg)
        val accent = theme.accentRgb
        val tint = Color.rgb((accent shr 16) and 255, (accent shr 8) and 255, accent and 255)
        val ink = if (UnoThemeColors.contrast(accent, 0x000000) >= 4.5) Color.BLACK else Color.WHITE
        for (button in themeButtons) {
            if (button.tag == "critical_stop") {
                button.backgroundTintList = ColorStateList.valueOf(Color.rgb(184, 55, 65))
                button.setTextColor(Color.WHITE)
            } else {
                button.backgroundTintList = ColorStateList.valueOf(tint)
                button.setTextColor(ink)
            }
        }
    }

    /** In-app owner diagnostic feedback. UI-thread only; NOOP cannot grant native authority. */
    private fun showOwnerFeedback(message: String) {
        status.text = message
        if (::ownerFeedback.isInitialized) {
            ownerFeedback.text = "РЕЗУЛЬТАТ ПРОВЕРКИ ВЛАДЕЛЬЦА: $message"
        }
    }

    private fun chooseManualTheme(rgb: Int, tone: ThemeTone) {
        themeGate.setManually(UnoTheme(tone, rgb))
        getSharedPreferences("uno_ui_theme", MODE_PRIVATE).edit()
            .putInt("accent_rgb", themeGate.current.accentRgb)
            .putString("tone", themeGate.current.tone.name).apply()
        applyTheme()
        status.text = "Тема выбрана владельцем · офлайн · сохранена на устройстве"
    }
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
        restoreTheme()
        val root=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setPadding(24,38,24,38)
            setBackgroundColor(Color.rgb(12,18,27))
        }
        uiRoot = root
        fun label(s:String, size:Float=15f)=TextView(this).apply {
            text=s;textSize=size;setTextColor(Color.WHITE);setPadding(0,8,0,8)
            labels.add(this)
        }
        root.addView(label("UNOVYRA / UNO 1.0 LAB",25f))
        root.addView(label("УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName", 13f))
        root.addView(label("Если кнопок SQLite ниже нет — открыта другая версия UNO.", 13f))
        status=label("Офлайн-лаборатория WP-01 · действий ОС нет · модель не загружена")
        root.addView(status)
        root.addView(label("Сценарии запускаются вручную. Режим STRESS ограничен 60 секундами, QUICK — 12. STOP блокирует новые шаги.",13f))
        report=label("Исследования: https://uno-research.pages.dev/\nСайт не используется приложением. \nДля сохранённых JSON: adb run-as ${packageName}")
        root.addView(report)
        fun button(text:String,onClick:()->Unit) {
            root.addView(Button(this).apply {
                this.text=text
                if (text.startsWith("СТОП")) tag="critical_stop"
                themeButtons.add(this)
                setOnClickListener{onClick()}
            })
        }
        root.addView(label("ОФОРМЛЕНИЕ · ручной выбор; нейровыбор пока недоступен", 17f))
        button("🟠 Оранжевый · тёмная тема") { chooseManualTheme(UnoThemeColors.ORANGE, ThemeTone.DARK) }
        button("🟡 Жёлтый · тёмная тема") { chooseManualTheme(UnoThemeColors.YELLOW, ThemeTone.DARK) }
        button("🩷🩵 Розово-голубой · тёмная тема") { chooseManualTheme(UnoThemeColors.ROSE, ThemeTone.DARK) }
        button("Светлая тема · оранжевый") { chooseManualTheme(UnoThemeColors.ORANGE, ThemeTone.LIGHT) }
        val consent = CheckBox(this).apply {
            text = "Разрешить в будущем локальный подбор по стилю общения"
            setTextColor(Color.WHITE)
            isChecked = themeGate.conversationStyleConsent
            setOnCheckedChangeListener { _, checked ->
                themeGate.setConversationStyleConsent(checked)
                getSharedPreferences("uno_ui_theme", MODE_PRIVATE).edit().putBoolean("style_consent", checked).apply()
                status.text = if (checked) "Согласие сохранено; анализа общения сейчас нет" else "Анализ общения отключён"
            }
        }
        root.addView(consent)
        styleCheckbox = consent
        button("Спросить UNO, какую тему он предложит") {
            status.text="Нейромодель ещё не подключена. Выбор по общению недоступен — тема не изменена."
        }
        root.addView(label("ЖУРНАЛ ДЕЙСТВИЙ · только диагностика, не разрешение ОС", 17f))
        button("Проверить SQLite (без создания базы)") { runOutcomeStoreInspection(false) }
        button("Создать пустую SQLite-базу и проверить") { runOutcomeStoreInspection(true) }
        root.addView(label("ЛОКАЛЬНОЕ ДЕЙСТВИЕ · только файл внутри UNO; не Android-полномочие", 17f))
        button("СОЗДАТЬ ТЕСТОВЫЙ ЛОКАЛЬНЫЙ МАРКЕР И ПРОЧИТАТЬ ОБРАТНО") {
            runAppPrivateEffectProbe()
        }
        button("ПОВТОРНО ПРОЧИТАТЬ ПОСЛЕДНИЙ ЛОКАЛЬНЫЙ МАРКЕР") {
            inspectLastAppPrivateEffect()
        }
        root.addView(label("ВЛАДЕЛЕЦ · системное подтверждение (только NOOP, без Android-действия)", 17f))
        button("Проверить владельца через экран Android") {
            val code = ownerGate.begin(
                ownerDiagnosticScope,
                OwnerConsentState.DIAGNOSTIC_DESCRIPTION
            )
            showOwnerFeedback(if (code != null) {
                "Ожидается системный ответ Android · действий ОС нет"
            } else {
                "Подтверждение недоступно или уже ожидается ответ · действий ОС нет"
            })
        }
        button("Проверить одноразовое согласие · без действия") {
            val consumed = ownerGate.consume(ownerDiagnosticScope)
            showOwnerFeedback(if (consumed) {
                "NOOP: одноразовое подтверждение принято и погашено · действий ОС нет"
            } else {
                "NOOP: подтверждение отсутствует, истекло или уже использовано · действий ОС нет"
            })
        }
        ownerFeedback = label("РЕЗУЛЬТАТ ПРОВЕРКИ ВЛАДЕЛЬЦА: пока нет результата", 15f)
        root.addView(ownerFeedback)
        button("Снимок состояния: RAM / CPU / батарея / тепло") { runSimple(false) }
        button("Каталог сенсоров и их характеристики") { runSensorInventory() }
        button("📋 СКОПИРОВАТЬ ВЕСЬ ПОСЛЕДНИЙ ОТЧЁТ") { copyFullReport() }
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
            labStop.stop();controller.stop();ownerGate.stop()
            status.text="STOP · тесты отменены · trusted epoch=${controller.epoch}"
        }
        setContentView(ScrollView(this).apply {addView(root)})
        applyTheme()
        mainHandler.post(heartbeat)
        reportFullyDrawn() // For full launch timing use separate physical-device Macrobenchmark.
    }

    /** Manual clipboard export only. No network, SAF, generic external intents or write access. */
    private fun copyFullReport() {
        val text = copyableReport
        if (text.isNullOrEmpty()) {
            status.text = "Сначала выполните проверку, затем нажмите «Скопировать весь отчёт»."
            return
        }
        try {
            val manager = getSystemService(CLIPBOARD_SERVICE) as? ClipboardManager
                ?: throw IllegalStateException("CLIPBOARD_UNAVAILABLE")
            manager.setPrimaryClip(ClipData.newPlainText("UNO offline diagnostic report", text))
            status.text = "Скопировано ${text.length} символов. Буфер обмена доступен другим приложениям."
        } catch (_: Exception) {
            status.text = "Не удалось скопировать отчёт. Локальный JSON остался сохранён."
        }
    }

    private fun execute(label:String,action:()->Pair<JSONObject,String>) {
        if(!busy.compareAndSet(false,true)) { status.text="Уже запущен тест. Используй STOP.";return }
        status.text=label
        copyableReport = null // Never copy a stale result after a failed new test.
        worker.execute {
            val result=runCatching{action()}
            busy.set(false)
            runOnUiThread {
                if(alive.get()) {
                    status.text=if(result.isSuccess) "Лаборатория: JSON сохранён в телефоне" else "Ошибка: тест не завершён"
                    report.text=if(result.isSuccess) {
                        val (json,path)=result.getOrThrow()
                        val rawJson = json.toString(2)
                        copyableReport = "UNO_OFFLINE_DIAGNOSTIC\npackage=$packageName\npath=$path\n" + rawJson
                        val cropped = if (rawJson.length > 14000) {
                            "\n[На экране только первые 14000 символов; кнопка копирует полный JSON.]"
                        } else ""
                        "Локально: $path\nUI late >=350ms: ${heartbeatLateCount.get()} " +
                            "max=${heartbeatMaxDelayMs.get()}ms\n" + rawJson.take(14000) + cropped
                    } else result.exceptionOrNull()?.javaClass?.simpleName?:"UNKNOWN"
                }
            }
        }
    }
    /**
     * Only an owner-tapped app-private storage diagnostic.
     * Never issues action tickets, calls native dispatch or upgrades a claim to verified OS state.
     */
    private fun runOutcomeStoreInspection(initialize: Boolean) {
        execute(if (initialize) "Создание пустого SQLite-журнала" else "Чтение состояния SQLite-журнала") {
            val summary = AndroidOutcomeInspection.inspect(applicationContext, initialize)
            if (summary.status == AndroidOutcomeInspection.Status.UNAVAILABLE) {
                throw IllegalStateException("OUTCOME_STORE_UNAVAILABLE_FAIL_CLOSED")
            }
            val json = JSONObject()
                .put("schema", "UNO_OUTCOME_INSPECTION/1")
                .put("status", summary.status.name)
                .put("total", summary.total)
                .put("prepared", summary.prepared)
                .put("may_have_executed", summary.mayHaveExecuted)
                .put("stored_readback_claims_UNVERIFIED", summary.storedReadbackClaims)
                .put("native_actions_enabled", false)
                .put("verified_os_outcomes", false)
                .put("note", "App-private inspection; no ticket replay and no owner authorization")
            json to DeviceProbe.persist(applicationContext, json).absolutePath
        }
    }
    /** A bounded owner-tapped local fixture. Not a credential grant or native Android dispatch. */
    private fun runAppPrivateEffectProbe() {
        if (busy.get()) { status.text = "Заверши текущую операцию"; return }
        labStop = LabStop()
        val stop = labStop
        execute("Локальный тест: создание файла и повторное открытие") {
            val outcome = AppPrivateReadbackProbe.run(filesDir) {
                stop.isStopped() || Thread.currentThread().isInterrupted
            }
            // Persist only the opaque app-generated ID. This is a locator, never a receipt.
            val locatorPersisted = if (outcome.id != null) {
                getSharedPreferences("uno_private_probe", MODE_PRIVATE).edit()
                    .putString("last_id", outcome.id).commit()
            } else false
            val independentlyReopened = if (outcome.id != null &&
                outcome.status == AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES &&
                !stop.isStopped()) AppPrivateReadbackProbe.inspect(filesDir, outcome.id)
                else null
            val json = JSONObject()
                .put("schema", "UNO_APP_PRIVATE_EFFECT_PROBE/1")
                .put("status", outcome.status.name)
                .put("id", outcome.id)
                .put("sha256", outcome.digest)
                .put("write_readback", outcome.detail)
                .put("last_id_locator_persisted", locatorPersisted)
                .put("independent_reopen_status", independentlyReopened?.status?.name)
                .put("independent_reopen_detail", independentlyReopened?.detail)
                .put("native_os_action_executed", false)
                .put("owner_credential_used", false)
                .put("scope", "APP_PRIVATE_FILE_ONLY")
                .put("limitations", "Local bytes readback, not OS attestation, crash durability or neural autonomy")
            json to DeviceProbe.persist(applicationContext, json).absolutePath
        }
    }
    /** Separate owner-tapped readback, including after Activity/process restart. */
    private fun inspectLastAppPrivateEffect() {
        execute("Повторное открытие локального файла без новой записи") {
            val id = getSharedPreferences("uno_private_probe", MODE_PRIVATE)
                .getString("last_id", null)
            val outcome = if (id == null) null else AppPrivateReadbackProbe.inspect(filesDir, id)
            val json = JSONObject()
                .put("schema", "UNO_APP_PRIVATE_REOPEN/1")
                .put("status", outcome?.status?.name ?: "NOT_INITIALIZED")
                .put("id", id)
                .put("sha256", outcome?.digest)
                .put("detail", outcome?.detail ?: "NO_PRIOR_MARKER")
                .put("new_write_performed", false)
                .put("native_os_action_executed", false)
                .put("limitations", "Fresh app-private file read, not external OS authority or durability attestation")
            json to DeviceProbe.persist(applicationContext, json).absolutePath
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
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode in 0x4100..0x7fef) {
            val accepted = ownerGate.credentialResult(requestCode, resultCode == RESULT_OK)
            showOwnerFeedback(if (accepted) {
                "Android вернул успешное подтверждение NOOP · нажми одноразовую проверку · действий ОС нет"
            } else {
                "Android не подтвердил NOOP: отменено, устарело или результат недействителен · действий ОС нет"
            })
        }
    }
    override fun onPause() {
        ownerGate.revokeReadyForBackground()
        labStop.stop();controller.stop();super.onPause()
    }
    override fun onDestroy(){alive.set(false);labStop.stop();mainHandler.removeCallbacks(heartbeat)
        worker.shutdownNow();controller.stop();ownerGate.stop();super.onDestroy()}
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
