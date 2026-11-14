package org.unovyra.uno.core

/** Manually entered facts. No model inference, permissions, or claimed owner authentication. */
object UnoManualFacts {
    private val scopePattern = Regex("manual-note:[0-9]{1,19}")
    private const val MAX_KEY_CHARS = 96
    private const val MAX_VALUE_BYTES = 2048
    private const val SCAN_ROWS = 256
    const val SOURCE = "OWNER_TYPED_LOCAL"

    /** Exception to boot-clock expiry checks only; provenance label is not identity proof. */
    fun survivesBootForRead(entry: ExactEntry): Boolean =
        scopePattern.matches(entry.scope) && entry.source == SOURCE &&
        entry.kind == EntryKind.USER_DECLARATION &&
        entry.expiryMonotonicNanos == Long.MAX_VALUE

    fun scope(revision: Long): String {
        require(revision >= 0) { "NOTE_SCOPE_REVISION" }
        return "manual-note:$revision"
    }

    private fun checkScope(scope: String) {
        require(scopePattern.matches(scope)) { "NOTE_SCOPE_INVALID" }
    }

    private fun cleanKey(key: String): String {
        val result = key.trim()
        require(result.length in 1..MAX_KEY_CHARS && result.none { it.isISOControl() }) {
            "NOTE_KEY_INVALID"
        }
        return result
    }

    fun remember(memory: UnoExactMemoryPort, scope: String, key: String, value: String): ExactEntry {
        checkScope(scope)
        val bytes = value.toByteArray(Charsets.UTF_8)
        require(bytes.isNotEmpty() && bytes.size <= MAX_VALUE_BYTES && value.none { it == '\u0000' }) {
            "NOTE_VALUE_INVALID"
        }
        // Explicitly timeless, owner-typed content. Never an Android action or verified outcome.
        return memory.write(scope, cleanKey(key), bytes, Long.MAX_VALUE,
            0L, EntryKind.USER_DECLARATION, SOURCE)
    }

    fun recall(memory: UnoExactMemoryPort, scope: String, key: String, now: Long): ExactRead {
        checkScope(scope)
        return memory.read(scope, cleanKey(key), 16, SCAN_ROWS, now, 0L)
    }

    /** Explicit owner UI confirmation must precede this irreversible scope revocation. */
    fun forgetAll(memory: UnoExactMemoryPort, scope: String): Long {
        checkScope(scope)
        memory.revoke(scope)
        return memory.generation
    }
}
