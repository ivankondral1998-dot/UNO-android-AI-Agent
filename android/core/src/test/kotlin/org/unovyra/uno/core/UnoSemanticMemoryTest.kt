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
        ports.linkSummary(remembered, vector(1.0), S4Access("notes", 1L, 0L, 16))
        verify(ports.recallSummary(S4Access("notes", 1L, 0L, 16), vector(1.0), 4).status == SemanticStatus.SUMMARY_ONLY)
        verify(ports.recallExact("notes", "city", 1, 4, 1L, 0L).entries.single()
            .raw.contentEquals("Riga".toByteArray()))
        ports.revoke("notes")
        verify(ports.recallSummary(S4Access("notes", 1L, 0L, 16), vector(1.0), 4).status == SemanticStatus.DENIED)
        verify(ports.recallExact("notes", "city", 1, 4, 1L, 0L).status == ExactStatus.DENIED)
        verify(runCatching { ports.linkSummary(remembered, vector(1.0), S4Access("notes", 1L, 0L, 16)) }.isFailure)
        // S4 authority and failure injection: both scans share one budget.
        var exactBytes: ByteArray? = null
        var summaryBytes: ByteArray? = null
        var failExact = false
        var failSummary = false
        var clock = 10L
        val exactKey = key()
        val summaryKey = key()
        fun openExact() = UnoEncryptedExactMemory(exactKey, "boot-a", { exactBytes?.copyOf() },
            { if (failExact) error("exact disk failed") else exactBytes = it.copyOf() }) { clock }
        fun openSummary() = UnoSemanticMemory(summaryKey, "boot-a", { summaryBytes?.copyOf() },
            { if (failSummary) error("index disk failed") else summaryBytes = it.copyOf() })
        val vault = openExact()
        val summaries = openSummary()
        val bank = UnoMemoryPorts(vault, summaries)
        fun access(budget: Int = 16, epoch: Long = 7L, scope: String = "s4") =
            S4Access(scope, 10L, epoch, budget)
        fun view(p: UnoMemoryPorts = bank, a: S4Access = access(), width: Int = UnoSemanticMemory.DIM) =
            p.withS4Bank(a, width) { it }
        verify(view().status == S4Status.EMPTY)
        val rec = vault.write("s4", "fact", byteArrayOf(1), 100L, 7L, EntryKind.OBSERVED, "LOCAL_UI")
        bank.linkSummary(rec, vector(1.0), access())
        verify(view().status == S4Status.COMPLETE && view().scannedRows == 2)
        verify(view(a = access(0)).status == S4Status.BUDGET_EXCEEDED)
        verify(view(a = access(1)).status == S4Status.BUDGET_EXCEEDED && view(a = access(1)).scannedRows == 1)
        verify(view(a = access(2)).hits.single().exactId == rec.id)
        verify(view(a = access(epoch = 8)).status == S4Status.UNKNOWN)
        verify(view(width = 2).status == S4Status.INCOMPATIBLE)
        verify(view(a = access(scope = "foreign")).status == S4Status.EMPTY)
        verify(runCatching { bank.linkSummary(rec.copy(sha256 = "forged"), vector(1.0), access()) }.isFailure)
        val copied = view().hits.single().vector
        copied[0] = -1.0
        verify(view().hits.single().vector[0] == 1.0)
        clock = 100L
        verify(view().status == S4Status.UNKNOWN)
        clock = 10L
        verify(runCatching { bank.withS4Bank(access(), UnoSemanticMemory.DIM) { clock = 100L; it } }.isFailure)
        clock = 10L
        failExact = true
        verify(runCatching { bank.revoke("s4") }.isFailure)
        verify(view().status == S4Status.COMPLETE)
        failExact = false
        failSummary = true
        verify(bank.revoke("s4") == S4Revocation.REVOKED_CLEANUP_PENDING)
        verify(view().status == S4Status.DENIED)
        verify(bank.recallExact("s4", "fact", 1, 16, 10L, 7L).status == ExactStatus.DENIED)
        // Persisted stale index is deliberately left intact; authoritative view still denies.
        val restarted = UnoMemoryPorts(openExact(), openSummary())
        verify(view(restarted).status == S4Status.DENIED)
        verify(restarted.recallSummary(access(), vector(1.0), 4).status == SemanticStatus.DENIED)
        verify(runCatching { restarted.linkSummary(rec, vector(1.0), access()) }.isFailure)
        failSummary = false
        verify(restarted.revoke("s4") == S4Revocation.REVOKED_CLEAN)
        verify(view(UnoMemoryPorts(openExact(), openSummary())).status == S4Status.DENIED)
        println("UNO_SEMANTIC_MEMORY_HOST_PASS=$pass")
    }
}
