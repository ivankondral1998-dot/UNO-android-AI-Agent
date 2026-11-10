package org.unovyra.uno

import android.app.Activity
import android.app.AlertDialog
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
import android.view.View
import org.json.JSONArray
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
    private val explicitStopLatched = AtomicBoolean(false)
    private val busy = AtomicBoolean(false)
    private val foreground = AtomicBoolean(false)
    @Volatile private var foundationCycle: UnoFoundationReferenceCycle? = null
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
        root.addView(label("UNOVYRA / UNO",25f))
        root.addView(label("УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName",12f))
        status = label("UNO · локальная диагностика по запросу",14f)
        root.addView(status)
        report = label("Один тест: CPU, RAM, IO, сенсоры и ранее записанная память.\n" +
            "Новой записи в точную память без отдельного согласия не будет.",13f)
        root.addView(report)
        val advancedContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        var buttonTarget: LinearLayout = root
        fun button(text:String,onClick:()->Unit) {
            buttonTarget.addView(Button(this).apply {
                this.text = text
                if (text.startsWith("СТОП")) tag = "critical_stop"
                themeButtons.add(this)
                setOnClickListener { onClick() }
            })
        }
        button("ОТКРЫТЬ ОФЛАЙН-ЧАТ UNO") {
            startActivity(Intent(this, UnoChatActivity::class.java))
        }
        button("ПРОВЕРИТЬ UNO · ОДИН ТЕСТ") { runUnifiedSelfTest() }
        button("КОПИРОВАТЬ ПОЛНЫЙ ОТЧЁТ") { copyFullReport() }
        button("СТОП: прервать все тесты и запретить действия") {
            UnoProcessStop.stop()
            explicitStopLatched.set(true)
            AppPrivateReadbackProbe.stop()
            labStop.stop();controller.stop();ownerGate.stop()
            status.text="STOP · новые лабораторные операции запрещены · уже начатый эффект не отменяется · epoch=${controller.epoch}"
        }
        button("НАСТРОЙКИ И ИНЖЕНЕРНАЯ ЛАБОРАТОРИЯ") {
            val open = advancedContainer.visibility != View.VISIBLE
            advancedContainer.visibility = if (open) View.VISIBLE else View.GONE
        }
        root.addView(advancedContainer)
        buttonTarget = advancedContainer
        advancedContainer.addView(label("ОФОРМЛЕНИЕ · ручной выбор; нейровыбор пока недоступен", 17f))
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
        advancedContainer.addView(consent)
        styleCheckbox = consent
        button("Спросить UNO, какую тему он предложит") {
            status.text="Нейромодель ещё не подключена. Выбор по общению недоступен — тема не изменена."
        }
        advancedContainer.addView(label("ЖУРНАЛ ДЕЙСТВИЙ · только диагностика, не разрешение ОС", 17f))
        button("Проверить SQLite (без создания базы)") { runOutcomeStoreInspection(false) }
        button("Создать пустую SQLite-базу и проверить") { runOutcomeStoreInspection(true) }
        advancedContainer.addView(label("ЛОКАЛЬНОЕ ДЕЙСТВИЕ · только файл внутри UNO; не Android-полномочие", 17f))
        button("СОЗДАТЬ ТЕСТОВЫЙ ЛОКАЛЬНЫЙ МАРКЕР И ПРОЧИТАТЬ ОБРАТНО") {
            runAppPrivateEffectProbe()
        }
        button("ПОВТОРНО ПРОЧИТАТЬ ПОСЛЕДНИЙ ЛОКАЛЬНЫЙ МАРКЕР") {
            inspectLastAppPrivateEffect()
        }
        advancedContainer.addView(label("ВЛАДЕЛЕЦ · системное подтверждение (только NOOP, без Android-действия)", 17f))
        button("Проверить владельца через экран Android") {
            if (UnoProcessStop.isStopped()) {
                ownerGate.stop(); showOwnerFeedback("STOP · подтверждение заблокировано")
                return@button
            }
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
            if (UnoProcessStop.isStopped()) {
                ownerGate.stop(); showOwnerFeedback("STOP · согласие заблокировано")
                return@button
            }
            val consumed = ownerGate.consume(ownerDiagnosticScope)
            showOwnerFeedback(if (consumed) {
                "NOOP: одноразовое подтверждение принято и погашено · действий ОС нет"
            } else {
                "NOOP: подтверждение отсутствует, истекло или уже использовано · действий ОС нет"
            })
        }
        ownerFeedback = label("РЕЗУЛЬТАТ ПРОВЕРКИ ВЛАДЕЛЬЦА: пока нет результата", 15f)
        advancedContainer.addView(ownerFeedback)
        button("Снимок состояния: RAM / CPU / батарея / тепло") { runSimple(false) }
        advancedContainer.addView(label("Точная память UNO: только отдельное подтверждение. Обычный снимок в память не записывается.", 13f))
        button("ЗАПИСАТЬ СНИМОК В ПАМЯТЬ UNO · отдельное согласие") { confirmExactObservation() }
        button("ПРОВЕРИТЬ ЗАПИСЬ ПАМЯТИ ПОСЛЕ ПЕРЕЗАПУСКА") { inspectLastExactObservation() }
        button("ОТОЗВАТЬ ДАННЫЕ ПАМЯТИ СНИМКОВ · отдельное подтверждение") { confirmExactRevocation() }
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

    private fun execute(label:String,allowAfterStop:Boolean=false,action:()->Pair<JSONObject,String>) {
        if ((explicitStopLatched.get() || UnoProcessStop.isStopped()) && !allowAfterStop) {
            status.text="STOP · новые лабораторные операции запрещены"
            return
        }
        if(!busy.compareAndSet(false,true)) { status.text="Уже запущен тест. Используй STOP.";return }
        status.text=label
        copyableReport = null // Never copy a stale result after a failed new test.
        worker.execute {
            val result=runCatching{
                if ((explicitStopLatched.get() || UnoProcessStop.isStopped()) && !allowAfterStop) throw IllegalStateException("STOP_LATCHED")
                action()
            }
            busy.set(false)
            runOnUiThread {
                if(alive.get()) {
                    status.text=if(result.isSuccess) {
                        val outcome = result.getOrThrow().first
                        if (outcome.optString("schema") == "UNO_ONE_TAP_DIAGNOSTIC/1")
                            "Единая проверка: ${outcome.optString("status")} · детали — «Копировать отчёт»"
                        else if (outcome.optString("schema") == "UNO_EXACT_OBSERVATION_REOPEN/1")
                            "Проверка памяти: ${outcome.optString("status")} · подробности в JSON"
                        else "Лаборатория: JSON сохранён в телефоне"
                    } else
                        "Ошибка: ${result.exceptionOrNull()?.javaClass?.simpleName ?: "UNKNOWN"}; " +
                        "если была запись, её исход проверь отдельно"
                    report.text=if(result.isSuccess) {
                        val (json,path)=result.getOrThrow()
                        val rawJson = json.toString(2)
                        copyableReport = "UNO_OFFLINE_DIAGNOSTIC\npackage=$packageName\npath=$path\n" + rawJson
                        val cropped = if (rawJson.length > 14000) {
                            "\n[На экране только первые 14000 символов; кнопка копирует полный JSON.]"
                        } else ""
                        if (json.optString("schema") == "UNO_ONE_TAP_DIAGNOSTIC/1")
                            "Итог: ${json.optString("status")}\n" +
                            "Локально: $path\nПолный JSON — кнопка копирования."
                        else "Локально: $path\nUI late >=350ms: ${heartbeatLateCount.get()} " +
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
        if (explicitStopLatched.get() || UnoProcessStop.isStopped()) { status.text="STOP · новая запись локального маркера запрещена"; return }
        if (busy.get()) { status.text = "Заверши текущую операцию"; return }
        labStop = LabStop()
        val stop = labStop
        execute("Локальный тест: создание файла и повторное открытие") {
            val outcome = AppPrivateReadbackProbe.run(filesDir) {
                explicitStopLatched.get() || UnoProcessStop.isStopped() || stop.isStopped() || Thread.currentThread().isInterrupted
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
        execute("Повторное открытие локального файла без новой записи", allowAfterStop=true) {
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
    /**
     * An actual Android observation enters the shared UNO foundation path, not
     * the experimental Qwen transcript. Stores selected measured fields exactly.
     * The full diagnostic is preserved separately in the existing diagnostics file.
     */
    private fun observeDeviceSnapshot(snapshot: JSONObject): FoundationReferenceResult {
        check(foreground.get() && !UnoProcessStop.isStopped()) { "UNO_NOT_IN_FOREGROUND" }
        val observedNanos = snapshot.optLong("elapsed_realtime_ns", -1L)
        // Exactly the pretty-printed bytes persisted by DeviceProbe.persistImmutable.
        val reportBytes = snapshot.toString(2).toByteArray(Charsets.UTF_8)
        val reportDigest = java.security.MessageDigest.getInstance("SHA-256")
            .digest(reportBytes).joinToString("") { "%02x".format(it) }
        val values = JSONObject()
            .put("schema", "UNO_DEVICE_METRICS_OBSERVATION/1")
            .put("observed_elapsed_ns", observedNanos)
            .put("sdk", snapshot.optInt("sdk", -1))
            .put("battery_percent_or_null",
                 snapshot.optJSONObject("battery")?.opt("level_percent") ?: JSONObject.NULL)
            .put("thermal_status_or_null",
                 snapshot.optJSONObject("thermal")?.opt("thermal_status_code_or_null") ?: JSONObject.NULL)
            .put("available_ram_bytes_or_null",
                 snapshot.optJSONObject("memory")?.opt("available_system_ram_bytes") ?: JSONObject.NULL)
            .put("full_diagnostic_sha256", reportDigest)
        val observedBytes = values.toString().toByteArray(Charsets.UTF_8)
        check(observedBytes.size in 1..4096) { "UNO_OBSERVATION_TOO_LARGE" }
        val now = SystemClock.elapsedRealtimeNanos()
        check(observedNanos >= 0 && observedNanos <= now &&
            now <= Long.MAX_VALUE - 600_000_000_000L) { "UNO_OBSERVATION_CLOCK_INVALID" }
        val runtime = synchronized(this) {
            val existing = foundationCycle
            if (existing != null && !existing.isStopped()) existing else {
                UnoFoundationReferenceCycle(
                    neural, UnoAndroidMemoryOwner.exact(applicationContext), controller,
                    object : AuthenticatedOwnerUi {
                        override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? =
                            null // No Android effect authorization in the foundation lab.
                    }
                ).also { foundationCycle = it }
            }
        }
        if (!foreground.get() || UnoProcessStop.isStopped()) {
            runtime.stop()
            error("UNO_STOPPED_BEFORE_OBSERVATION")
        }
        val outcome = runtime.accept(
            Percept(PerceptType.OS, observedBytes, "ANDROID_READONLY_DEVICE_METRICS",
                observedNanos, authenticatedSource = false),
            now, now + 600_000_000_000L, "device-observation", 0L
        )
        check(outcome.status == FoundationReferenceStatus.MODEL_UNAVAILABLE &&
            !outcome.verifiedAndroidEffect) { "UNO_FOUNDATION_REJECTED_${outcome.status}" }
        val exact = UnoAndroidMemoryOwner.exact(applicationContext).read(
            "device-observation", outcome.observedEventKey
                ?: error("UNO_FOUNDATION_EVENT_KEY_MISSING"), 1, 256, now, 0L
        )
        check(exact.status == ExactStatus.COMPLETE &&
            exact.entries.single().raw.contentEquals(observedBytes)) {
            "UNO_FOUNDATION_EXACT_READBACK_FAILED"
        }
        return outcome
    }

    /** Existing passive diagnostic: NO implicit exact-memory writes or Keystore access. */
    private fun runSimple(withCpu:Boolean) {
        execute("Чтение параметров устройства · без записи в память UNO") {
            val json=LabSystemMetrics.snapshot(applicationContext)
            json.put("ui_heartbeat_delay_over_350ms",heartbeatLateCount.get())
            json.put("ui_max_heartbeat_delay_ms",heartbeatMaxDelayMs.get())
            if(withCpu) json.put("cpu",DeviceProbe.benchmark())
            json.put("uno_exact_memory_write_performed", false)
            json to DeviceProbe.persist(applicationContext,json).absolutePath
        }
    }

    /** An explicit owner UI action. This is consent to store observations, NOT OS authority. */
    private fun confirmExactObservation() {
        if (!foreground.get() || busy.get() || UnoProcessStop.isStopped()) {
            status.text = "Память недоступна: STOP, фоновый режим или другая операция"
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Записать снимок в точную память UNO?")
            .setMessage("В защищённую память попадут только выбранные показатели батареи, " +
                "температуры, RAM и SHA-256 отчёта. Доступ к записи — до 10 минут. " +
                "Шифрованные записи НЕ удаляются автоматически по истечении этого срока. " +
                "Можно отдельно отозвать весь раздел, но восстановить его запись нельзя. " +
                "Полный диагностический JSON сохраняется отдельно, как раньше. " +
                "Это не подтверждение личности Android и не разрешение действий ОС.")
            .setNegativeButton("Отмена", null)
            .setPositiveButton("Сохранить") { _, _ -> runExactObservationWithConsent() }
            .show()
    }

    private fun runExactObservationWithConsent() {
        execute("Явно разрешённая запись наблюдения в память UNO") {
            val json = LabSystemMetrics.snapshot(applicationContext)
            // Persist the ordinary diagnostic first. If the encrypted memory
            // step fails, this original read-only report is still available.
            // No second disk write follows a successful memory commit.
            val diagnosticPath = DeviceProbe.persistImmutable(applicationContext, json).absolutePath
            val observed = observeDeviceSnapshot(json)
            // Durable *locator* only: never a receipt, permission, or substitute for vault readback.
            val eventKey = observed.observedEventKey
                ?: error("EXACT_OBSERVATION_COMMITTED_KEY_MISSING")
            val originalDigest = java.io.File(diagnosticPath).name
                .removePrefix("observation-").removeSuffix(".json")
            check(originalDigest.matches(Regex("[0-9a-f]{64}"))) {
                "EXACT_DIAGNOSTIC_DIGEST_NAME_INVALID"
            }
            val locatorSaved = getSharedPreferences("uno_exact_observation_locator_v1", MODE_PRIVATE)
                .edit().putString("last_event_key", eventKey)
                .putString("last_diagnostic_sha256", originalDigest).commit()
            json.put("uno_exact_observation", JSONObject()
                .put("status", if (locatorSaved) "LOCAL_EXACT_PERSISTED_AND_RETRIEVED" else
                    "LOCAL_EXACT_PERSISTED_RESTART_LOCATOR_UNAVAILABLE")
                .put("locator_saved_for_restart", locatorSaved)
                .put("explicit_user_ui_confirmation", true)
                .put("memory_generation", observed.memoryGeneration)
                .put("event_key", eventKey)
                .put("neural_status", observed.status.name)
                .put("android_action_verified", false)
                .put("note", "Chosen fields stored encrypted; no neural decision. " +
                    "Saved diagnostic JSON predates this receipt; copy the UI report for receipt details."))
            json to diagnosticPath
        }
    }

    /**
     * Separate owner-invoked vault readback after Activity/process restart.
     * No model call, no vault mutation, no recreation of lost/expired/denied data.
     * This is only a same-boot test; the owner locator is NOT an authority token.
     */
    private fun inspectLastExactObservation() {
        execute("Повторное открытие точной памяти без новой записи в хранилище UNO") {
            val json = buildExactObservationReadback()
            json to DeviceProbe.persist(applicationContext, json).absolutePath
        }
    }

    /** Fresh, read-only disk reopening shared by manual control and consolidated report. */
    private fun buildExactObservationReadback(): JSONObject {
        val prefs = getSharedPreferences("uno_exact_observation_locator_v1", MODE_PRIVATE)
        val key = prefs.getString("last_event_key", null)
        val digest = prefs.getString("last_diagnostic_sha256", null)
        val json = JSONObject()
            .put("schema", "UNO_EXACT_OBSERVATION_REOPEN/1")
            .put("event_key", key)
            .put("expected_source_sha256", digest)
            .put("new_vault_write_performed", false)
            .put("android_os_effect_verified", false)
            .put("cross_reboot_memory_verified", false)
        val validKey = key != null && key.matches(Regex("event:[1-9][0-9]*"))
        val validDigest = digest != null && digest.matches(Regex("[0-9a-f]{64}"))
        if (!validKey || !validDigest) {
            json.put("status", if (key == null || digest == null)
                "NO_DURABLE_LOCATOR" else "INVALID_LOCATOR")
        } else {
            val read = try {
                // Fresh disk-backed open: the process singleton would only
                // prove RAM state, not persistence across Activity restarts.
                UnoAndroidExactMemory(applicationContext, readOnly = true).read(
                    "device-observation", key!!, 1, 256,
                    SystemClock.elapsedRealtimeNanos(), 0L
                )
            } catch (_: Exception) { null }
            if (read == null) {
                json.put("status", "VAULT_UNAVAILABLE_FAIL_CLOSED")
            } else if (read.status != ExactStatus.COMPLETE || read.entries.size != 1) {
                // UNKNOWN includes a changed boot token. NOT_FOUND also means TTL expiry;
                // neither implies deletion or falsifies an old authenticated record.
                json.put("status", "EXACT_" + read.status.name)
            } else {
                val entry = read.entries.single()
                val observed = runCatching {
                    JSONObject(String(entry.raw, Charsets.UTF_8))
                }.getOrNull()
                val sourceSha = observed?.optString("full_diagnostic_sha256", "") ?: ""
                val sourceFile = java.io.File(filesDir,
                    "diagnostics/observation-${digest!!}.json")
                val sourceBytes = if (sourceFile.isFile &&
                    sourceFile.length() in 1L..65_536L) {
                    runCatching { sourceFile.readBytes() }.getOrNull()
                } else null
                val sourceActualSha = sourceBytes?.let { data ->
                    java.security.MessageDigest.getInstance("SHA-256").digest(data)
                        .joinToString("") { "%02x".format(it) }
                }
                val memorySha = java.security.MessageDigest.getInstance("SHA-256")
                    .digest(entry.raw).joinToString("") { "%02x".format(it) }
                val validMemory = entry.factKey == key && entry.scope == "device-observation" &&
                    entry.kind == EntryKind.OBSERVED &&
                    entry.source == "ANDROID_READONLY_DEVICE_METRICS" &&
                    memorySha == entry.sha256 &&
                    observed?.optString("schema", "") == "UNO_DEVICE_METRICS_OBSERVATION/1"
                json.put("status", if (validMemory && sourceSha == digest &&
                    sourceActualSha == digest) "SAME_BOOT_EXACT_AND_SOURCE_MATCH"
                    else "EXACT_OR_SOURCE_MISMATCH")
                    .put("source_file_present", sourceBytes != null)
                    .put("source_sha256_match", sourceActualSha == digest)
                    .put("memory_payload_valid", validMemory)
            }
        }
        return json
    }

    private fun confirmExactRevocation() {
        if (!foreground.get() || busy.get() || UnoProcessStop.isStopped()) {
            status.text = "Отзыв сейчас недоступен: STOP, фоновый режим или другая операция"
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Отозвать память снимков UNO?")
            .setMessage("Отзыв запрещает чтение всех записей в разделе device-observation " +
                "и дальнейшую запись в него. Из актуального шифрованного состояния записи " +
                "исключаются. Старые физические копии и отдельные диагностические JSON " +
                "этим действием НЕ удаляются. Отмена отзыва сейчас не предусмотрена.")
            .setNegativeButton("Отмена", null)
            .setPositiveButton("Отозвать раздел") { _, _ -> revokeExactObservations() }
            .show()
    }

    private fun revokeExactObservations() {
        execute("Отзыв доступа к памяти снимков по подтверждению владельца") {
            check(foreground.get() && !UnoProcessStop.isStopped()) { "STOP_OR_BACKGROUND" }
            val exact = UnoAndroidMemoryOwner.exact(applicationContext)
            exact.revoke("device-observation")
            check(exact.read("device-observation", "event:1", 1, 256,
                SystemClock.elapsedRealtimeNanos(), 0L).status == ExactStatus.DENIED) {
                "EXACT_REVOCATION_NOT_CONFIRMED"
            }
            val json = JSONObject()
                .put("schema", "UNO_EXACT_MEMORY_REVOCATION/1")
                .put("status", "SCOPE_REVOKED_READ_DENIED")
                .put("scope", "device-observation")
                .put("revision", exact.generation)
                .put("physical_flash_securely_erased", false)
                .put("legacy_diagnostic_json_deleted", false)
                .put("new_writes_in_scope_allowed", false)
            json to DeviceProbe.persist(applicationContext, json).absolutePath
        }
    }
    /**
     * One bounded, owner-initiated run. Never calls owner consent, native dispatch,
     * neural proposal or encrypted-memory mutation. Missing prior data is NOT_RUN.
     */
    private fun runUnifiedSelfTest() {
        if (busy.get()) { status.text = "Уже идёт проверка · доступен STOP"; return }
        labStop = LabStop()
        val stop = labStop
        execute("UNO · единая ограниченная проверка QUICK") {
            val parts = JSONArray()
            fun add(id: String, verdict: String, evidence: Any) {
                parts.put(JSONObject().put("id", id).put("status", verdict).put("evidence", evidence))
            }
            val lab = DeviceLab.run(applicationContext, LabProfile.QUICK, stop)
            val scenarios = lab.optJSONArray("results") ?: JSONArray()
            var failed = false
            var interrupted = stop.isStopped() || UnoProcessStop.isStopped() ||
                Thread.currentThread().isInterrupted
            for (i in 0 until scenarios.length()) {
                val scenario = scenarios.optJSONObject(i) ?: continue
                val verdict = scenario.optString("status", "INCONCLUSIVE")
                if (verdict == "FAIL") failed = true
                if (verdict == "ABORTED") interrupted = true
                add("LAB_" + scenario.optString("scenario", "UNKNOWN"), verdict, scenario)
            }
            if (!lab.isNull("abort_reason_or_null")) interrupted = true
            if (scenarios.length() == 0)
                add("LAB_SCENARIOS", "UNKNOWN", "No completed checks")
            if (!interrupted) {
                val journal = AndroidOutcomeInspection.inspect(applicationContext, false)
                val journalVerdict = when (journal.status) {
                    AndroidOutcomeInspection.Status.INSPECTED -> "PASS"
                    AndroidOutcomeInspection.Status.NOT_INITIALIZED -> "NOT_RUN"
                    AndroidOutcomeInspection.Status.UNAVAILABLE -> "FAIL"
                }
                if (journalVerdict == "FAIL") failed = true
                add("OUTCOME_JOURNAL_READ_ONLY", journalVerdict, JSONObject()
                    .put("status", journal.status.name)
                    .put("total", journal.total)
                    .put("may_have_executed", journal.mayHaveExecuted)
                    .put("stored_readback_claims_unverified", journal.storedReadbackClaims))
                val exact = runCatching { buildExactObservationReadback() }
                    .getOrElse { JSONObject().put("status", "VAULT_UNAVAILABLE_FAIL_CLOSED") }
                val exactVerdict = when (exact.optString("status")) {
                    "SAME_BOOT_EXACT_AND_SOURCE_MATCH" -> "PASS"
                    "NO_DURABLE_LOCATOR" -> "NOT_RUN"
                    "EXACT_DENIED" -> "DENIED"
                    "EXACT_NOT_FOUND", "EXACT_UNKNOWN", "EXACT_TRUNCATED", "EXACT_CONFLICT" -> "UNKNOWN"
                    else -> "FAIL"
                }
                if (exactVerdict == "FAIL") failed = true
                add("EXACT_MEMORY_FRESH_READ_ONLY", exactVerdict, exact)
                val markerId = getSharedPreferences("uno_private_probe", MODE_PRIVATE)
                    .getString("last_id", null)
                if (markerId == null) {
                    add("PRIVATE_MARKER_FRESH_READ_ONLY", "NOT_RUN", "No prior marker")
                } else {
                    val marker = AppPrivateReadbackProbe.inspect(filesDir, markerId)
                    val markerVerdict = when (marker.status) {
                        AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES -> "PASS"
                        AppPrivateReadbackProbe.Status.UNKNOWN_MAY_HAVE_WRITTEN -> "UNKNOWN"
                        else -> "FAIL"
                    }
                    if (markerVerdict == "FAIL") failed = true
                    add("PRIVATE_MARKER_FRESH_READ_ONLY", markerVerdict, JSONObject()
                        .put("status", marker.status.name).put("detail", marker.detail)
                        .put("sha256", marker.digest))
                }
            }
            add("OWNER_CREDENTIAL_AND_EXPLICIT_CONSENT", "MANUAL_REQUIRED",
                "A test cannot consent or authenticate on behalf of the owner")
            add("NATIVE_ANDROID_ACTION_READBACK", "NOT_IMPLEMENTED",
                "DenyAllAndroidPort; no OS action dispatched")
            add("NEURAL_DIALOGUE_QUALITY", "NOT_TESTED",
                "Offline neural quality requires a separate real model acceptance")
            val outcome = JSONObject()
                .put("schema", "UNO_ONE_TAP_DIAGNOSTIC/1")
                .put("status", if (interrupted) "ABORTED" else if (failed) "FAIL" else "PARTIAL")
                .put("package", packageName)
                .put("profile", "QUICK")
                .put("lab", lab)
                .put("checks", parts)
                .put("ui_delay_over_350ms", heartbeatLateCount.get())
                .put("ui_max_delay_ms", heartbeatMaxDelayMs.get())
                .put("exact_memory_write_performed", false)
                .put("owner_auth_performed", false)
                .put("native_android_dispatch_performed", false)
                .put("device_verified_by_owner", false)
                .put("note", "PARTIAL never means whole UNO acceptance")
            outcome to DeviceProbe.persist(applicationContext, outcome).absolutePath
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
            if (UnoProcessStop.isStopped()) {
                ownerGate.stop()
                showOwnerFeedback("STOP · системный ответ не даёт разрешения")
                return
            }
            val accepted = ownerGate.credentialResult(requestCode, resultCode == RESULT_OK)
            showOwnerFeedback(if (accepted) {
                "Android вернул успешное подтверждение NOOP · нажми одноразовую проверку · действий ОС нет"
            } else {
                "Android не подтвердил NOOP: отменено, устарело или результат недействителен · действий ОС нет"
            })
        }
    }
    override fun onResume() {
        super.onResume()
        foreground.set(true)
    }
    override fun onPause() {
        foreground.set(false)
        foundationCycle?.stop()
        ownerGate.revokeReadyForBackground()
        labStop.stop();controller.stop();super.onPause()
    }
    override fun onDestroy(){alive.set(false);foundationCycle?.stop();labStop.stop();mainHandler.removeCallbacks(heartbeat)
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
