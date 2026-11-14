package org.unovyra.uno.core

import javax.crypto.KeyGenerator

object UnoManualFactsTest {
    var pass = 0
        private set
    private fun verify(ok: Boolean) { check(ok); pass++ }

    fun run() {
        val key = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
        var persisted: ByteArray? = null
        var failWrites = false
        val load = { persisted?.copyOf() }
        val persist: (ByteArray) -> Unit = { data ->
            if (failWrites) error("SIMULATED_DISK_ERROR")
            persisted = data.copyOf()
        }
        val scope = UnoManualFacts.scope(0L)
        val a = UnoEncryptedExactMemory(key, "boot-A", load, persist) { 100L }
        val first = UnoManualFacts.remember(a, scope, "город", "Рига")
        verify(first.kind == EntryKind.USER_DECLARATION && first.source == UnoManualFacts.SOURCE)
        verify(first.expiryMonotonicNanos == Long.MAX_VALUE)
        verify(persisted!!.toList().windowed("Рига".toByteArray(Charsets.UTF_8).size).none {
            it == "Рига".toByteArray(Charsets.UTF_8).toList()
        })
        first.raw[0] = 0
        verify(UnoManualFacts.recall(a, scope, "город", 100L)
            .entries.single().raw.decodeToString() == "Рига")
        verify(UnoManualFacts.recall(a, "manual-note:999", "город", 100L)
            .status == ExactStatus.NOT_FOUND)
        val b = UnoEncryptedExactMemory(key, "boot-B", load, persist) { 10L }
        verify(UnoManualFacts.recall(b, scope, "город", 10L).status == ExactStatus.COMPLETE)
        verify(UnoManualFacts.recall(b, scope, "город", 10L)
            .entries.single().raw.decodeToString() == "Рига")
        UnoManualFacts.remember(b, scope, "город", "Минск")
        verify(UnoManualFacts.recall(b, scope, "город", 10L).status == ExactStatus.CONFLICT)
        verify(UnoManualFacts.recall(b, scope, "город", 10L).entries.size == 2)
        failWrites = true
        val before = b.generation
        verify(runCatching { UnoManualFacts.remember(b, scope, "знак", "!" ) }.isFailure)
        verify(b.generation == before)
        failWrites = false
        verify(runCatching { UnoManualFacts.remember(b, scope, "", "x") }.isFailure)
        verify(runCatching { UnoManualFacts.remember(b, scope, "ok", "") }.isFailure)
        verify(runCatching { UnoManualFacts.remember(b, scope, "ok", "x".repeat(2049)) }.isFailure)
        verify(runCatching { UnoManualFacts.remember(b, "device-event", "ok", "x") }.isFailure)
        verify(runCatching { UnoManualFacts.remember(b, scope, "bad\nkey", "x") }.isFailure)
        val rev = UnoManualFacts.forgetAll(b, scope)
        verify(rev == b.generation && rev > before)
        verify(UnoManualFacts.recall(b, scope, "город", 10L).status == ExactStatus.DENIED)
        val c = UnoEncryptedExactMemory(key, "boot-C", load, persist) { 2L }
        verify(UnoManualFacts.recall(c, scope, "город", 2L).status == ExactStatus.DENIED)
        val nextScope = UnoManualFacts.scope(c.generation)
        verify(nextScope != scope)
        UnoManualFacts.remember(c, nextScope, "ключ", "новая память")
        verify(UnoManualFacts.recall(c, nextScope, "ключ", 2L).status == ExactStatus.COMPLETE)
        verify(UnoManualFacts.recall(c, scope, "город", 2L).status == ExactStatus.DENIED)
        val corrupt = persisted!!.copyOf().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }
        verify(runCatching { UnoEncryptedExactMemory(key, "boot-C", { corrupt }, persist) { 2L } }.isFailure)
        println("UNO_MANUAL_FACTS_HOST_PASS=$pass")
    }
}
