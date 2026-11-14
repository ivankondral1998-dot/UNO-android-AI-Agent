package org.unovyra.uno

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputFilter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.unovyra.uno.core.ExactStatus
import org.unovyra.uno.core.UnoManualFacts
import org.unovyra.uno.core.UnoExactMemoryPort
import org.unovyra.uno.core.UnoProcessStop
import java.util.concurrent.Executors

/** Explicit local facts UI; no model, owner identity claim or Android effects. */
class UnoFactsActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var active = true
    private lateinit var key: EditText
    private lateinit var value: EditText
    private lateinit var result: TextView
    private lateinit var save: Button
    private lateinit var recall: Button
    private lateinit var erase: Button

    private fun currentScope(memory: UnoExactMemoryPort, repair: Boolean,
                             allowRevocationRepair: Boolean = false): String {
        val preferences = getSharedPreferences("uno_manual_facts_v1", MODE_PRIVATE)
        val previous = preferences.getLong("scope_generation", 0L)
        var scope = UnoManualFacts.scope(previous)
        val probe = UnoManualFacts.recall(memory, scope, "__scope_probe__", SystemClock.elapsedRealtimeNanos())
        // Persisted semantic tombstone wins over a still-readable exact scope after a torn revoke.
        // Construct a fresh read-only adapter: no key creation and no stale cached snapshot.
        val semanticRevoked = UnoAndroidSemanticMemory(applicationContext).isScopeRevoked(scope)
        if (semanticRevoked && probe.status != ExactStatus.DENIED && !allowRevocationRepair) {
            error("NOTE_SCOPE_REVOKE_INCOMPLETE_REPEAT_CONFIRMED_FORGET")
        }
        if (repair && probe.status == ExactStatus.DENIED) {
            // Recovery after a crash between authenticated revoke and preference update.
            val next = memory.generation
            require(next > previous) { "NOTE_SCOPE_RECOVERY_UNAVAILABLE" }
            check(preferences.edit().putLong("scope_generation", next).commit()) {
                "NOTE_SCOPE_LOCATOR_WRITE_FAILED"
            }
            scope = UnoManualFacts.scope(next)
        }
        return scope
    }

    private fun execute(readOnly: Boolean = false, allowRevocationRepair: Boolean = false,
                        action: (UnoExactMemoryPort, String) -> String) {
        save.isEnabled = false
        recall.isEnabled = false
        erase.isEnabled = false
        worker.execute {
            val message = try {
                val memory: UnoExactMemoryPort = if (readOnly)
                    UnoAndroidExactMemory(applicationContext, readOnly = true)
                else UnoAndroidMemoryOwner.exact(applicationContext)
                action(memory, currentScope(memory, repair = !readOnly,
                    allowRevocationRepair = allowRevocationRepair))
            } catch (e: Exception) {
                "Операция не подтверждена: ${e.message ?: e.javaClass.simpleName}. Проверь состояние перед повтором."
            }
            main.post {
                if (!active) return@post
                result.text = message
                save.isEnabled = !UnoProcessStop.isStopped()
                recall.isEnabled = true
                erase.isEnabled = !UnoProcessStop.isStopped()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(20, 20, 20, 20)
            setBackgroundColor(UnoChrome.BG)
            fitsSystemWindows = true
            setPadding(UnoChrome.dp(this, 20), UnoChrome.dp(this, 16), UnoChrome.dp(this, 20), UnoChrome.dp(this, 16))
        }
        fun label(text: String) = TextView(this).apply {
            this.text = text
            setTextColor(UnoChrome.INK)
            textSize = 15f
            setPadding(0, UnoChrome.dp(this, 8), 0, UnoChrome.dp(this, 8))
        }
        root.addView(label("Память").apply { textSize = 28f })
        root.addView(TextView(this).apply {
            text = "Сюда попадает только то, что ты сам сохранил."
            setTextColor(UnoChrome.MUTED)
            textSize = 14f
        })
        key = EditText(this).apply {
            hint = "Название"
            setTextColor(UnoChrome.INK)
            setHintTextColor(UnoChrome.MUTED)
            filters = arrayOf(InputFilter.LengthFilter(96))
            setSingleLine(true)
        }
        value = EditText(this).apply {
            hint = "Текст"
            setTextColor(UnoChrome.INK)
            setHintTextColor(UnoChrome.MUTED)
            filters = arrayOf(InputFilter.LengthFilter(2048))
            minLines = 3; maxLines = 6
        }
        root.addView(key)
        root.addView(value)
        save = Button(this).apply {
            text = "Запомнить"
            UnoChrome.button(this, UnoChrome.ACCENT, UnoChrome.ACCENT_INK)
        }
        recall = Button(this).apply {
            text = "Вспомнить по названию"
            UnoChrome.button(this, UnoChrome.SURFACE, UnoChrome.INK)
        }
        erase = Button(this).apply {
            text = "Забыть все ручные факты"
            UnoChrome.button(this, UnoChrome.SURFACE, UnoChrome.INK)
        }
        root.addView(save)
        root.addView(recall)
        root.addView(erase)
        result = label("Записи сохраняются локально в зашифрованном хранилище.")
        val scroll = ScrollView(this)
        scroll.addView(result)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)

        save.setOnClickListener {
            if (UnoProcessStop.isStopped()) { result.text = "STOP: новая запись запрещена"; return@setOnClickListener }
            val k = key.text.toString()
            val v = value.text.toString()
            AlertDialog.Builder(this)
                .setTitle("Записать факт?")
                .setMessage("Этот текст сохранится в зашифрованной памяти UNO. Он не станет разрешением на действия.")
                .setNegativeButton("Отмена", null)
                .setPositiveButton("Сохранить") { _, _ ->
                    execute { memory, scope ->
                        check(!UnoProcessStop.isStopped()) { "STOP" }
                        val row = UnoManualFacts.remember(memory, scope, k, v)
                        "Сохранено: ${row.factKey}; ревизия ${row.generation}. Не проверено внешним источником."
                    }
                }.show()
        }
        recall.setOnClickListener {
            val k = key.text.toString()
            execute(readOnly = true) { memory, scope ->
                val recalled = UnoManualFacts.recall(memory, scope, k, SystemClock.elapsedRealtimeNanos())
                when (recalled.status) {
                    ExactStatus.COMPLETE, ExactStatus.CONFLICT, ExactStatus.TRUNCATED -> {
                        val warning = when (recalled.status) {
                            ExactStatus.CONFLICT -> "ВНИМАНИЕ: разные версии одного факта, истина неизвестна."
                            ExactStatus.TRUNCATED -> "ВНИМАНИЕ: найдено больше записей, чем показано."
                            else -> "Точные записи (не проверенные факты):"
                        }
                        warning + "\n" + recalled.entries.joinToString("\n\n") { row ->
                            "${row.factKey} [${row.id}, ${row.source}]: " + row.raw.toString(Charsets.UTF_8)
                        }
                    }
                    ExactStatus.NOT_FOUND -> "Такой записи нет."
                    ExactStatus.DENIED -> "Доступ к этой области памяти отозван."
                    ExactStatus.UNKNOWN -> "Неизвестное состояние памяти. Нельзя выдавать ответ за точный."
                }
            }
        }
        erase.setOnClickListener {
            if (UnoProcessStop.isStopped()) { result.text = "STOP: изменение памяти запрещено"; return@setOnClickListener }
            AlertDialog.Builder(this)
                .setTitle("Забыть все ручные факты?")
                .setMessage("Записи в этой области станут недоступны после подтверждённого сохранения отзыва. " +
                    "Если сохранение прервётся, повтори это подтверждение; автоматического удаления нет. " +
                    "Это не гарантирует физическое стирание старых копий на флеш-памяти.")
                .setNegativeButton("Отмена", null)
                .setPositiveButton("Забыть") { _, _ ->
                    execute(allowRevocationRepair = true) { memory, scope ->
                        check(!UnoProcessStop.isStopped()) { "STOP" }
                        // One owner-confirmed forget across both existing stores, not a new UI action.
                        // If semantic persistence succeeds but exact fails, the tombstone denies reads
                        // until the owner repeats this confirmation. No automatic data deletion/retry.
                        UnoAndroidMemoryOwner.semantic(applicationContext).dropScopeIfPresent(scope)
                        check(!UnoProcessStop.isStopped()) { "STOP" }
                        val newGeneration = UnoManualFacts.forgetAll(memory, scope)
                        check(getSharedPreferences("uno_manual_facts_v1", MODE_PRIVATE).edit()
                            .putLong("scope_generation", newGeneration).commit()) {
                            "NOTE_SCOPE_REOPEN_REQUIRED"
                        }
                        "Все ручные факты отозваны. Новые записи сохранятся в новой области."
                    }
                }.show()
        }
    }

    override fun onDestroy() {
        active = false
        worker.shutdown()
        super.onDestroy()
    }
}
