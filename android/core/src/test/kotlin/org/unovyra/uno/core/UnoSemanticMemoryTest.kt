package org.unovyra.uno.core

import javax.crypto.KeyGenerator
import kotlin.math.abs

object UnoSemanticMemoryTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private fun key() = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
    private fun vector(first: Double) = DoubleArray(UnoSemanticMemory.DIM) { if (it == 0) first else 0.0 }

    fun run() {
        val exact = ExactMemory()
        val positive = exact.write("notes", "v", "plus".toByteArray(), 500L, 0L,
            EntryKind.OBSERVED, "LOCAL_UI")
        val negative = exact.write("notes", "v-neg", "minus".toByteArray(), 500L, 0L,
            EntryKind.OBSERVED, "LOCAL_UI")
        val secret = key()
        var stored: ByteArray? = null
        val index = UnoSemanticMemory(secret, "boot-a", { stored?.copyOf() }, { stored = it.copyOf() })
        verify(index.retrieve("notes", vector(1.0), 4, 16).status == SemanticStatus.UNKNOWN)
        index.link(positive, vector(1.0))
        index.link(negative, vector(-1.0))
        val summary = index.retrieve("notes", vector(1.0), 4, 16)
        verify(summary.status == SemanticStatus.SUMMARY_ONLY && summary.hits.size == 2)
        verify(summary.hits[0].exactId == positive.id && summary.hits[0].score > summary.hits[1].score)
        verify(summary.hits.none { it.sha256.isEmpty() })
        val exactRead = exact.read("notes", "v", 4, 16, 1L, 0L)
        verify(exactRead.status == ExactStatus.COMPLETE &&
            exactRead.entries.single().raw.contentEquals("plus".toByteArray()))
        val mean = unoSemanticAggregate(listOf(vector(1.0), vector(-1.0)))
        verify(mean.all { abs(it) < 1e-12 })
        verify(index.retrieve("notes", mean, 4, 16).status == SemanticStatus.UNKNOWN)

        val reopened = UnoSemanticMemory(secret, "boot-a", { stored?.copyOf() }, { stored = it.copyOf() })
        verify(reopened.retrieve("notes", vector(1.0), 1, 16).status == SemanticStatus.TRUNCATED)
        verify(reopened.retrieve("notes", vector(1.0), 1, 16).matchedLowerBound == 2)
        verify(reopened.retrieve("notes", DoubleArray(3), 4, 16).status == SemanticStatus.UNKNOWN)
        verify(reopened.retrieve("notes", vector(Double.NaN), 4, 16).status == SemanticStatus.UNKNOWN)
        reopened.dropScope("notes")
        verify(reopened.retrieve("notes", vector(1.0), 4, 16).status == SemanticStatus.DENIED)
        verify(exact.read("notes", "v-neg", 4, 16, 1L, 0L).entries.single()
            .raw.contentEquals("minus".toByteArray()))
        exact.revoke("notes")
        verify(exact.read("notes", "v", 4, 16, 1L, 0L).status == ExactStatus.DENIED)

        val otherBoot = UnoSemanticMemory(secret, "boot-b", { stored?.copyOf() }, { stored = it.copyOf() })
        verify(otherBoot.retrieve("other", vector(1.0), 4, 16).status == SemanticStatus.UNKNOWN)
        val copy = stored!!.copyOf()
        verify(runCatching {
            UnoSemanticMemory(secret, "boot-a", { byteArrayOf(1, 2, 3) }, { stored = it.copyOf() })
        }.isFailure)
        verify(stored!!.contentEquals(copy))
        val portsExact = ExactMemory()
        val portsSecret = key()
        var portsBytes: ByteArray? = null
        val ports = UnoMemoryPorts(portsExact, UnoSemanticMemory(portsSecret, "boot-a",
            { portsBytes?.copyOf() }, { portsBytes = it.copyOf() }))
        val remembered = portsExact.write("notes", "city", "Riga".toByteArray(), 500L, 0L,
            EntryKind.USER_DECLARATION, "OWNER_UI")
        ports.linkSummary(remembered, vector(1.0))
        verify(ports.recallSummary("notes", vector(1.0), 4, 16).status == SemanticStatus.SUMMARY_ONLY)
        verify(ports.recallExact("notes", "city", 1, 4, 1L, 0L).entries.single()
            .raw.contentEquals("Riga".toByteArray()))
        ports.revoke("notes")
        verify(ports.recallSummary("notes", vector(1.0), 4, 16).status == SemanticStatus.DENIED)
        verify(ports.recallExact("notes", "city", 1, 4, 1L, 0L).status == ExactStatus.DENIED)
        verify(runCatching { ports.linkSummary(remembered, vector(1.0)) }.isFailure)
        println("UNO_SEMANTIC_MEMORY_HOST_PASS=$pass")
    }
}
