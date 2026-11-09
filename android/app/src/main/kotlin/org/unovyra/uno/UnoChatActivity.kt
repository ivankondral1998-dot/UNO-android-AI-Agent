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
    private lateinit var status: TextView
    private lateinit var transcript: TextView
    private lateinit var input: EditText
    private lateinit var send: Button
    private lateinit var stop: Button
    private var currentUser = ""
    private var partial = ""
    private val history by lazy { UnoChatHistoryStore(applicationContext) }

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
        tool("Выбрать GGUF") { selectModel() }
        tool("Новый чат") { confirmNewChat() }
        root.addView(tools)
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
        root.addView(line("Только текст. История хранится в приватном хранилище приложения БЕЗ шифрования. " +
            "Не вводите секреты. Оператор F, семантическая память и Android-действия не подключены.", 12f))
        setContentView(root)
        lockUi(false)
        startLoadHistory()
    }

    private fun lockUi(on: Boolean) {
        send.isEnabled = !on && loaded
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
                    render()
                    status.text = "История загружена: ${restored.size} реплик · модель не загружена"
                    busy.set(false)
                    val name = getPreferences(MODE_PRIVATE).getString("model_name", null)
                    if (name != null && Regex("sha256-[0-9a-f]{64}\\.gguf").matches(name)) {
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

    private fun selectModel() {
        if (busy.get()) return
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
        status.text = "Импорт GGUF в приватное хранилище · без сети"
        worker.execute {
            try {
                val model = importModel(uri)
                val prefs = getPreferences(MODE_PRIVATE)
                if (!prefs.edit().putString("model_name", model.name).commit())
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
        if (!busy.compareAndSet(false, true)) return
        lockUi(true)
        status.text = "Загружаю модель · CPU, контекст 2048"
        worker.execute { performLoad(file) }
    }
    private fun performLoad(file: File) {
        try {
            check(UnoNativeEngine.load(file.absolutePath)) { "MODEL_LOAD_RETURNED_FALSE" }
            main.post {
                if (active) {
                    loaded = true
                    status.text = "GGUF загружен · CPU · без Android-действий · offline"
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
        if (!loaded || !busy.compareAndSet(false, true)) return
        val messages = try { UnoPromptWindow.forInference(turns, user) }
            catch (e: Exception) { busy.set(false); status.text = "Текст недопустим: ${e.message}"; return }
        currentUser = user; partial = ""; cancelled.set(false)
        try { UnoNativeEngine.resetCancel() } catch (e: Throwable) {
            currentUser = ""; busy.set(false); status.text = "JNI недоступен: ${e.message}"; return
        }
        input.setText(""); render(); lockUi(true)
        status.text = "UNO вычисляет ответ локально"
        val snapshot = turns
        worker.execute {
            var first = -1L
            val started = SystemClock.elapsedRealtime()
            val tokens = AtomicInteger(0)
            var lastUi = 0L
            try {
                val data = UnoNativeEngine.generate(
                    messages.map { it.first }.toTypedArray(),
                    messages.map { it.second }.toTypedArray(),
                    UnoPromptWindow.MAX_GENERATION_TOKENS,
                    UnoTokenReceiver { bytes ->
                        val now = SystemClock.elapsedRealtime()
                        if (first < 0) first = now
                        tokens.incrementAndGet()
                        if (now - lastUi >= 80) {
                            lastUi = now
                            val text = String(bytes, Charsets.UTF_8)
                            main.post { if (active && !cancelled.get()) { partial = text; render() } }
                        }
                    }
                ) ?: error("INFERENCE_RETURNED_NULL")
                if (cancelled.get()) {
                    main.post { if (active) finishCancelled() }
                    return@execute
                }
                val answer = String(data, Charsets.UTF_8).trim()
                val committed = UnoPromptWindow.committed(snapshot, user, answer)
                history.save(committed) // Atomic local record, never claimed as verified OS result.
                val elapsed = (SystemClock.elapsedRealtime() - started).coerceAtLeast(1)
                val throughput = tokens.get() * 1000.0 / elapsed
                val ttft = if (first < 0) -1 else first - started
                main.post {
                    if (!active) return@post
                    turns = committed; currentUser = ""; partial = ""
                    render()
                    status.text = "Готово · ${tokens.get()} токенов · ${"%.1f".format(throughput)} т/с (общая) · TTFT ${ttft} мс"
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
                        history.save(emptyList())
                        main.post {
                            if (active) {
                                turns = emptyList(); currentUser = ""; partial = ""
                                render(); status.text = "Локальный диалог очищен по запросу владельца"
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
        try { UnoNativeEngine.cancel() } catch (_: Throwable) {}
        worker.shutdown()
        super.onDestroy()
    }
}
