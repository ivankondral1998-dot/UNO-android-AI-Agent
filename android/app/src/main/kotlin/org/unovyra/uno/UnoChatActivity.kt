package org.unovyra.uno

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputFilter
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.unovyra.uno.core.UnoChatTurn
import org.unovyra.uno.core.UnoPromptWindow
import org.unovyra.uno.core.UnoTextCycle
import org.unovyra.uno.core.UnoTextInput
import org.unovyra.uno.core.UnoTextStatus
import org.unovyra.uno.core.UnoProcessStop
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/** WP-04 EXPERIMENT: local CPU inference, no owner authorization, no OS effects. */
class UnoChatActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val busy = AtomicBoolean(false)
    private val cancelled = AtomicBoolean(false)
    private var active = true
    private var loaded = false
    private var turns = listOf<UnoChatTurn>()
    private var textCycle: UnoTextCycle? = null
    private lateinit var status: TextView
    private lateinit var transcript: TextView
    private lateinit var input: EditText
    private lateinit var send: Button
    private lateinit var stop: Button
    private var currentUser = ""
    private var partial = ""
    private var copyModelOnPick = false
    private val history by lazy { UnoSecureChatHistoryStore(applicationContext) }

    private fun line(text: String, size: Float = 15f) = TextView(this).apply {
        this.text = text; textSize = size; setTextColor(0xfff5f5f5.toInt())
        setPadding(12, 10, 12, 10)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(0xff10151e.toInt())
            setPadding(12, 18, 12, 18)
        }
        root.addView(line("UNO · Локальный нейрочат (эксперимент)", 21f))
        status = line("Нет загруженной модели · действия Android недоступны")
        root.addView(status)
        val tools = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        fun tool(label: String, action: () -> Unit) {
            tools.addView(Button(this).apply {
                text = label
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                setOnClickListener { action() }
            })
        }
        tool("GGUF без копии") { selectModel(false) }
        tool("Новый чат") { confirmNewChat() }
        root.addView(tools)
        root.addView(Button(this).apply {
            text = "Резервный импорт GGUF с копированием (занимает сотни МБ)"
            setOnClickListener { selectModel(true) }
        })
        val scroller = ScrollView(this).apply { isFillViewport = true }
        transcript = line("История ещё не загружена.")
        scroller.addView(transcript)
        root.addView(scroller, LinearLayout.LayoutParams(-1, 0, 1f))
        input = EditText(this).apply {
            hint = "Сообщение UNO"
            setTextColor(0xffffffff.toInt())
            setHintTextColor(0xffb9b9b9.toInt())
            filters = arrayOf(InputFilter.LengthFilter(1200))
            minLines = 2; maxLines = 4
        }
        root.addView(input)
        val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER }
        send = Button(this).apply { text = "Отправить"; setOnClickListener { submit() } }
        stop = Button(this).apply {
            text = "СТОП ОТВЕТА"
            isEnabled = false
            setOnClickListener {
                cancelled.set(true)
                try { UnoNativeEngine.cancel() } catch (_: Throwable) {}
                status.text = "Генерация отменяется; системный STOP и права ОС не менялись"
            }
        }
        controls.addView(send, LinearLayout.LayoutParams(0, -2, 1f))
        controls.addView(stop, LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(controls)
        root.addView(Button(this).apply {
            text = "СТОП UNO · запретить новые операции до перезапуска процесса"
            setOnClickListener {
                UnoProcessStop.stop()
                cancelled.set(true)
                textCycle?.stop()
                try { UnoNativeEngine.cancel() } catch (_: Throwable) {}
                lockUi(false)
                status.text = "STOP UNO: новые вычисления этого процесса закрыты; Android-действия и так запрещены"
            }
        })
        root.addView(line("Только текст. История текущего чата шифруется AndroidKeyStore (AES-GCM). " +
            "Не вводите секреты: старая v1-история может остаться на устройстве без шифрования. Оператор F и Android-действия не подключены.", 12f))
        setContentView(root)
        lockUi(false)
        startLoadHistory()
    }

    private fun lockUi(on: Boolean) {
        send.isEnabled = !on && loaded && !UnoProcessStop.isStopped()
        stop.isEnabled = on
    }
    private fun render() {
        val sb = StringBuilder()
        turns.forEach { sb.append(if (it.role == "user") "ВЫ: " else "UNO: ").append(it.content).append("\n\n") }
        if (currentUser.isNotEmpty()) sb.append("ВЫ: ").append(currentUser)
            .append("\nUNO: ").append(partial.ifEmpty { "…" })
        transcript.text = if (sb.isEmpty()) "Новый диалог." else sb.toString()
    }
    private fun startLoadHistory() {
        busy.set(true)
        worker.execute {
            try {
                val restored = history.load()
                main.post {
                    if (!active) return@post
                    turns = restored
                    textCycle = UnoTextCycle(restored) { history.save(it) }
                    render()
                    status.text = "История загружена: ${restored.size} реплик · модель не загружена"
                    busy.set(false)
                    val preferences = getPreferences(MODE_PRIVATE)
                    val name = if (preferences.getString("model_mode", "COPY") == "COPY")
                        preferences.getString("model_name", null) else null
                    if (!UnoProcessStop.isStopped() && name != null && Regex("sha256-[0-9a-f]{64}\\.gguf").matches(name)) {
                        val modelFile = File(File(filesDir, "models"), name)
                        if (modelFile.isFile) loadModel(modelFile)
                    }
                }
            } catch (e: Exception) {
                main.post {
                    if (!active) return@post
                    status.text = "История недоступна: ${e.message} · новые записи заблокированы"
                    busy.set(true) // Fail closed: do not silently overwrite a damaged transcript.
                    render()
                }
            }
        }
    }

    private fun selectModel(copyIntoApp: Boolean) {
        if (UnoProcessStop.isStopped()) { status.text = "STOP · импорт модели запрещён"; return }
        if (busy.get()) return
        copyModelOnPick = copyIntoApp
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_LOCAL_ONLY, true)
        }
        startActivityForResult(intent, 51)
    }

    @Deprecated("Compatible Android 12/14 local picker, no AndroidX dependency.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 51 || resultCode != RESULT_OK) return
        if (UnoProcessStop.isStopped()) { status.text = "STOP · импорт заблокирован"; return }
        val uri = data?.data ?: return
        // Even an app with no INTERNET permission could read via a networked SAF provider.
        // Allow only Android's well-known local document providers. Others FAIL CLOSED.
        val allowed = setOf("com.android.providers.downloads.documents",
                            "com.android.externalstorage.documents",
                            "com.android.providers.media.documents")
        if (uri.scheme != "content" || uri.authority !in allowed) {
            status.text = "Отказ: источник GGUF не подтверждён как локальный. Переместите файл в Download."
            return
        }
        if (!busy.compareAndSet(false, true)) return
        lockUi(true)
        val copy = copyModelOnPick
        status.text = if (copy) "Импорт GGUF: будет создана отдельная копия" else
            "Открываю GGUF без копирования · источник остаётся в Downloads"
        worker.execute {
            if (!copy) {
                performDirectLoad(uri)
            } else {
                try {
                    val model = importModel(uri)
                    val prefs = getPreferences(MODE_PRIVATE)
                    if (!prefs.edit().putString("model_mode", "COPY")
                            .putString("model_name", model.name).commit())
                        error("MODEL_LOCATOR_SAVE_FAILED")
                    performLoad(model)
                } catch (e: Exception) {
                    main.post {
                        if (active) {
                            busy.set(false); lockUi(false)
                            status.text = "Ошибка импорта: ${e.message}"
                        }
                    }
                }
            }
        }
    }

    /**
     * Experimental SAF descriptor path. The user-selected GGUF is read in place,
     * never copied by this path. Backend may reject /proc/self/fd on some devices:
     * failure is explicit; NO silent fallback to a large private duplicate.
     */
    private fun performDirectLoad(uri: Uri) {
        try {
            check(!UnoProcessStop.isStopped()) { "STOP" }
            val handle = contentResolver.openFileDescriptor(uri, "r")
                ?: error("GGUF_DESCRIPTOR_UNAVAILABLE")
            handle.use { descriptor ->
                val path = "/proc/self/fd/${descriptor.fd}"
                check(UnoNativeEngine.load(path)) { "DIRECT_GGUF_LOAD_UNSUPPORTED" }
            }
            // Session-only by design: no persisted SAF grant, no stale source after restart.
            val saved = getPreferences(MODE_PRIVATE).edit()
                .putString("model_mode", "DIRECT_RESELECT").commit()
            check(saved) { "MODEL_MODE_WRITE_FAILED" }
            main.post {
                if (active) {
                    loaded = !UnoProcessStop.isStopped()
                    busy.set(false); lockUi(false)
                    status.text = if (loaded)
                        "GGUF открыт без копирования · при следующем запуске выбери файл снова" else
                        "STOP · модель заблокирована"
                }
            }
        } catch (e: Throwable) {
            main.post {
                if (active) {
                    loaded = false
                    busy.set(false); lockUi(false)
                    status.text = "Прямая загрузка GGUF не удалась (${e.message ?: e.javaClass.simpleName}). " +
                        "Копирование не выполнено. Резервный импорт — только по твоему выбору."
                }
            }
        }
    }

    private fun importModel(uri: Uri): File {
        val dir = File(filesDir, "models")
        require(dir.isDirectory || dir.mkdirs()) { "MODEL_DIRECTORY_UNAVAILABLE" }
        val tmp = File.createTempFile("import-", ".part", dir)
        val digest = MessageDigest.getInstance("SHA-256")
        var size = 0L
        try {
            val stream = contentResolver.openInputStream(uri) ?: error("MODEL_SOURCE_UNAVAILABLE")
            stream.use { input ->
                FileOutputStream(tmp).use { output ->
                    val magic = byteArrayOf(71, 71, 85, 70) // ASCII GGUF
                    for (expected in magic) {
                        val actual = input.read()
                        require(actual == (expected.toInt() and 0xff)) { "NOT_A_GGUF_FILE" }
                    }
                    output.write(magic); digest.update(magic); size = 4
                    val buffer = ByteArray(128 * 1024)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        size += n
                        require(size <= 1_073_741_824L) { "MODEL_EXCEEDS_1_GIB" }
                        digest.update(buffer, 0, n)
                        output.write(buffer, 0, n)
                    }
                    require(size >= 10_000_000) { "MODEL_FILE_TOO_SMALL" }
                    output.fd.sync()
                }
            }
            val sha = digest.digest().joinToString("") { "%02x".format(it) }
            val dest = File(dir, "sha256-$sha.gguf")
            if (dest.exists()) {
                require(dest.isFile && dest.length() == size) { "MODEL_FILE_COLLISION" }
            } else {
                require(tmp.renameTo(dest)) { "MODEL_IMPORT_RENAME_FAILED" }
            }
            return dest
        } finally {
            if (tmp.exists()) tmp.delete() // Only a newly created temporary copy, never the supplied original.
        }
    }
    private fun loadModel(file: File) {
        if (UnoProcessStop.isStopped()) return
        if (!busy.compareAndSet(false, true)) return
        lockUi(true)
        status.text = "Загружаю модель · CPU, контекст 2048"
        worker.execute { performLoad(file) }
    }
    private fun performLoad(file: File) {
        if (UnoProcessStop.isStopped()) return
        try {
            check(UnoNativeEngine.load(file.absolutePath)) { "MODEL_LOAD_RETURNED_FALSE" }
            main.post {
                if (active) {
                    loaded = !UnoProcessStop.isStopped()
                    status.text = if (loaded) "GGUF загружен · CPU · без Android-действий · offline" else "STOP · модель загружена, но использование запрещено"
                    busy.set(false); lockUi(false)
                }
            }
        } catch (e: Throwable) {
            main.post {
                if (active) {
                    loaded = false; busy.set(false); lockUi(false)
                    status.text = "Модель не загружена: ${e.message ?: e.javaClass.simpleName}"
                }
            }
        }
    }

    private fun submit() {
        val user = input.text.toString().trim()
        val cycle = textCycle ?: run { status.text = "Состояние диалога недоступно"; return }
        if (UnoProcessStop.isStopped()) { status.text = "STOP · генерация запрещена"; return }
        if (!loaded || !busy.compareAndSet(false, true)) return
        currentUser = user; partial = ""; cancelled.set(false)
        try { UnoNativeEngine.resetCancel() } catch (e: Throwable) {
            currentUser = ""; busy.set(false); status.text = "JNI недоступен: ${e.message}"; return
        }
        input.setText(""); render(); lockUi(true)
        status.text = "UNO вычисляет ответ локально"
        val stamp = SystemClock.elapsedRealtimeNanos()
        worker.execute {
            var first = -1L
            val started = SystemClock.elapsedRealtime()
            val tokens = AtomicInteger(0)
            var lastUi = 0L
            try {
                val receipt = cycle.run(UnoTextInput(user, stamp, "LOCAL_UI_TEXT"), { cancelled.get() || UnoProcessStop.isStopped() }) { prompt, shouldStop ->
                    val data = UnoNativeEngine.generate(
                        prompt.map { it.first }.toTypedArray(),
                        prompt.map { it.second }.toTypedArray(),
                        UnoPromptWindow.MAX_GENERATION_TOKENS,
                        UnoTokenReceiver { bytes ->
                            if (shouldStop()) {
                                UnoNativeEngine.cancel()
                            } else {
                                val now = SystemClock.elapsedRealtime()
                                if (first < 0) first = now
                                tokens.incrementAndGet()
                                if (now - lastUi >= 80) {
                                    lastUi = now
                                    val text = String(bytes, Charsets.UTF_8)
                                    main.post { if (active && !cancelled.get()) { partial = text; render() } }
                                }
                            }
                        }
                    ) ?: error("INFERENCE_RETURNED_NULL")
                    String(data, Charsets.UTF_8)
                }
                val elapsed = (SystemClock.elapsedRealtime() - started).coerceAtLeast(1)
                val throughput = tokens.get() * 1000.0 / elapsed
                val ttft = if (first < 0) -1 else first - started
                main.post {
                    if (!active) return@post
                    turns = receipt.history
                    currentUser = ""; partial = ""; render()
                    status.text = when (receipt.status) {
                        UnoTextStatus.COMMITTED ->
                            "Диалог записан · rev=${receipt.revision} · ${tokens.get()} токенов · ${"%.1f".format(throughput)} т/с (общая) · TTFT ${ttft} мс"
                        UnoTextStatus.CANCELLED -> "Ответ отменён · в память ничего не записано"
                        UnoTextStatus.MODEL_FAILED -> "Модель не вернула допустимый ответ · память сохранена без изменений"
                        UnoTextStatus.STORAGE_FAILED -> "Ошибка сохранения · ответ не засчитан · проверь память телефона"
                        UnoTextStatus.INVALID_INPUT -> "Некорректное сообщение или время события"
                        UnoTextStatus.STOPPED -> "Нейродиалог остановлен"
                        UnoTextStatus.BUSY -> "Нейродиалог уже выполняется"
                    }
                    busy.set(false); lockUi(false)
                }
            } catch (e: Throwable) {
                main.post {
                    if (!active) return@post
                    currentUser = ""; partial = ""; render()
                    status.text = "Ошибка нейрочата: ${e.message ?: e.javaClass.simpleName}"
                    busy.set(false); lockUi(false)
                }
            }
        }
    }
    private fun finishCancelled() {
        currentUser = ""; partial = ""; render()
        status.text = "Ответ отменён без записи в историю · новая текстовая генерация доступна"
        busy.set(false); lockUi(false)
    }

    private fun confirmNewChat() {
        if (UnoProcessStop.isStopped()) { status.text = "STOP · запись и очистка заблокированы"; return }
        if (busy.get()) return
        AlertDialog.Builder(this)
            .setTitle("Новый чат")
            .setMessage("Стереть локальную историю только этого экспериментального диалога?")
            .setNegativeButton("Отмена", null)
            .setPositiveButton("Стереть") { _, _ ->
                if (!busy.compareAndSet(false, true)) return@setPositiveButton
                lockUi(true)
                worker.execute {
                    try {
                        val cycle = textCycle ?: error("CYCLE_UNAVAILABLE")
                        val receipt = cycle.clear()
                        main.post {
                            if (active) {
                                if (receipt.status == UnoTextStatus.COMMITTED) {
                                    turns = receipt.history; currentUser = ""; partial = ""
                                    render()
                                    status.text = "Локальный диалог очищен по запросу владельца"
                                } else {
                                    status.text = "Очистка отклонена: ${receipt.status}"
                                }
                                busy.set(false); lockUi(false)
                            }
                        }
                    } catch (e: Exception) {
                        main.post {
                            if (active) {
                                status.text = "Не удалось очистить: ${e.message}"
                                busy.set(false); lockUi(false)
                            }
                        }
                    }
                }
            }
            .show()
    }

    override fun onDestroy() {
        active = false
        cancelled.set(true)
        textCycle?.stop()
        try { UnoNativeEngine.cancel() } catch (_: Throwable) {}
        worker.shutdown()
        super.onDestroy()
    }
}
