package org.unovyra.uno.core

import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/** Single conversation state. Not the research operator F and not Android authority. */
data class UnoTextInput(val raw: String, val observedElapsedNanos: Long, val origin: String) {
    init {
        require(observedElapsedNanos >= 0L)
        require(origin == "LOCAL_UI_TEXT")
    }
}

enum class UnoTextStatus { COMMITTED, CANCELLED, BUSY, STOPPED, INVALID_INPUT, MODEL_FAILED, STORAGE_FAILED }

data class UnoTextReceipt(
    val status: UnoTextStatus,
    val history: List<UnoChatTurn>,
    val revision: Long,
    val stateSha256: String,
    val nativeEffectDispatched: Boolean = false
)

/**
 * A real bounded UI->prompt->inference->atomic transcript write text path.
 * The LLM returns data only; NO Android dispatcher, OS outcome, semantic memory, or training.
 * The state hash describes local transcript bytes; it is NOT evidence of OS completion.
 *
 * STOP is one-way for this instance; in-flight local filesystem writes cannot be
 * physically cancelled after they enter the persist callback.
 */
class UnoTextCycle(
    restored: List<UnoChatTurn>,
    private val persist: (List<UnoChatTurn>) -> Unit
) {
    private val halted = AtomicBoolean(false)
    private val running = AtomicBoolean(false)
    private var history = UnoPromptWindow.sanitizeHistory(restored)
    private var revision = 0L
    private var lastObservedNanos = -1L

    @Synchronized fun snapshot(): UnoTextReceipt =
        receipt(if (halted.get()) UnoTextStatus.STOPPED else UnoTextStatus.COMMITTED)

    fun stop() { halted.set(true) }
    fun isStopped(): Boolean = halted.get()

    /**
     * Model executes outside the snapshot lock and never holds an Android authority.
     * Callback should check interrupted() at inference checkpoints (native token/prefill).
     */
    fun run(
        input: UnoTextInput,
        cancelled: () -> Boolean,
        infer: (List<Pair<String, String>>, () -> Boolean) -> String
    ): UnoTextReceipt {
        if (halted.get()) return synchronized(this) { receipt(UnoTextStatus.STOPPED) }
        if (!running.compareAndSet(false, true)) return synchronized(this) { receipt(UnoTextStatus.BUSY) }
        try {
            val initial: List<UnoChatTurn>
            val prompt: List<Pair<String, String>>
            synchronized(this) {
                if (halted.get()) return receipt(UnoTextStatus.STOPPED)
                if (input.observedElapsedNanos < lastObservedNanos) return receipt(UnoTextStatus.INVALID_INPUT)
                lastObservedNanos = input.observedElapsedNanos
                initial = history.toList()
                prompt = try { UnoPromptWindow.forInference(initial, input.raw) }
                         catch (_: IllegalArgumentException) { return receipt(UnoTextStatus.INVALID_INPUT) }
            }
            if (halted.get() || cancelled()) return synchronized(this) { receipt(UnoTextStatus.CANCELLED) }
            val answer = try { infer(prompt) { halted.get() || cancelled() } }
                         catch (_: Exception) { return synchronized(this) { receipt(UnoTextStatus.MODEL_FAILED) } }
            if (halted.get() || cancelled()) return synchronized(this) { receipt(UnoTextStatus.CANCELLED) }
            val next = try { UnoPromptWindow.committed(initial, input.raw, answer.trim()) }
                       catch (_: IllegalArgumentException) {
                           return synchronized(this) { receipt(UnoTextStatus.MODEL_FAILED) }
                       }
            synchronized(this) {
                if (halted.get() || cancelled()) return receipt(UnoTextStatus.CANCELLED)
                // Persist before state revision becomes visible. Old transcript survives write failures.
                try { persist(next) }
                catch (_: Exception) { return receipt(UnoTextStatus.STORAGE_FAILED) }
                history = next
                revision += 1L
                return receipt(UnoTextStatus.COMMITTED)
            }
        } finally {
            running.set(false)
        }
    }

    /** Only for explicit owner-cleared local chat. Not general revocation of long-term memory. */
    fun clear(): UnoTextReceipt {
        if (halted.get()) return synchronized(this) { receipt(UnoTextStatus.STOPPED) }
        if (!running.compareAndSet(false, true)) return synchronized(this) { receipt(UnoTextStatus.BUSY) }
        try {
            synchronized(this) {
                if (halted.get()) return receipt(UnoTextStatus.STOPPED)
                try { persist(emptyList()) }
                catch (_: Exception) { return receipt(UnoTextStatus.STORAGE_FAILED) }
                history = emptyList()
                revision += 1
                return receipt(UnoTextStatus.COMMITTED)
            }
        } finally { running.set(false) }
    }

    private fun receipt(status: UnoTextStatus): UnoTextReceipt {
        val copy = history.toList()
        val hash = MessageDigest.getInstance("SHA-256")
        fun update(text: String) {
            val b = text.toByteArray(Charsets.UTF_8)
            hash.update(((b.size ushr 24) and 255).toByte())
            hash.update(((b.size ushr 16) and 255).toByte())
            hash.update(((b.size ushr 8) and 255).toByte())
            hash.update((b.size and 255).toByte())
            hash.update(b)
        }
        copy.forEach { update(it.role); update(it.content) }
        return UnoTextReceipt(status, copy, revision,
            hash.digest().joinToString("") { "%02x".format(it) })
    }
}
