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
        // C2: crash/error after durable semantic tombstone but before exact revoke.
        val unfinishedExact = ExactMemory()
        val old = unfinishedExact.write("partial", "secret", "old raw".toByteArray(), 500L, 0L,
            EntryKind.USER_DECLARATION, "OWNER_UI")
        val partialKey = key()
        var partialBytes: ByteArray? = null
        val partialIndex = UnoSemanticMemory(partialKey, "boot-a",
            { partialBytes?.copyOf() }, { partialBytes = it.copyOf() })
        val failingExact = object : UnoExactMemoryPort by unfinishedExact {
            override fun revoke(scope: String) { throw IllegalStateException("INJECT_EXACT_PERSIST_FAIL") }
        }
        val partial = UnoMemoryPorts(failingExact, partialIndex)
        partial.linkSummary(old, vector(1.0))
        verify(runCatching { partial.revoke("partial") }.isFailure)
        verify(unfinishedExact.read("partial", "secret", 1, 16, 1L, 0L).status == ExactStatus.COMPLETE)
        verify(partial.recallExact("partial", "secret", 1, 16, 1L, 0L).status == ExactStatus.DENIED)
        verify(partial.recallSummary("partial", vector(1.0), 1, 16).status == SemanticStatus.DENIED)
        verify(runCatching { partial.linkSummary(old, vector(1.0)) }.isFailure)

        // Reopen persisted semantic state after the partial revoke; no ghost fact through the gate.
        val reopenedPartialIndex = UnoSemanticMemory(partialKey, "boot-a",
            { partialBytes?.copyOf() }, { partialBytes = it.copyOf() })
        val reopenedPartial = UnoMemoryPorts(unfinishedExact, reopenedPartialIndex)
        verify(reopenedPartial.recallExact("partial", "secret", 1, 16, 1L, 0L).status == ExactStatus.DENIED)
        verify(reopenedPartial.recallSummary("partial", vector(1.0), 1, 16).status == SemanticStatus.DENIED)
        reopenedPartial.revoke("partial")
        verify(unfinishedExact.read("partial", "secret", 1, 16, 1L, 0L).status == ExactStatus.DENIED)

        // C2: if the first tombstone write fails, only the in-process barrier is guaranteed.
        val failedPersistExact = ExactMemory()
        failedPersistExact.write("retry", "k", "raw".toByteArray(), 500L, 0L,
            EntryKind.USER_DECLARATION, "OWNER_UI")
        val failedPersistIndex = UnoSemanticMemory(key(), "boot-a", { null },
            { throw IllegalStateException("INJECT_SEMANTIC_PERSIST_FAIL") })
        val failedPersist = UnoMemoryPorts(failedPersistExact, failedPersistIndex)
        verify(runCatching { failedPersist.revoke("retry") }.isFailure)
        verify(failedPersist.recallExact("retry", "k", 1, 16, 1L, 0L).status == ExactStatus.DENIED)
        verify(failedPersistExact.read("retry", "k", 1, 16, 1L, 0L).status == ExactStatus.COMPLETE)

        // C2: a read racing a failed semantic tombstone write must not expose exact bytes
        // through the process-local gateway. This is not a durable cross-process guarantee.
        val raceExact = ExactMemory()
        raceExact.write("race", "secret", "still present".toByteArray(), 500L, 0L,
            EntryKind.USER_DECLARATION, "OWNER_UI")
        val racePersistEntered = java.util.concurrent.CountDownLatch(1)
        val racePersistRelease = java.util.concurrent.CountDownLatch(1)
        val raceIndex = UnoSemanticMemory(key(), "boot-a", { null }, {
            racePersistEntered.countDown()
            check(racePersistRelease.await(5L, java.util.concurrent.TimeUnit.SECONDS)) {
                "C2_TEST_TOMBSTONE_TIMEOUT"
            }
            error("C2_TEST_TOMBSTONE_WRITE_FAILED")
        })
        val racePorts = UnoMemoryPorts(raceExact, raceIndex)
        val raceWriteError = java.util.concurrent.atomic.AtomicReference<Throwable?>(null)
        val raceReadError = java.util.concurrent.atomic.AtomicReference<Throwable?>(null)
        val raceReadStatus = java.util.concurrent.atomic.AtomicReference<ExactStatus?>(null)
        val raceReadStarted = java.util.concurrent.CountDownLatch(1)
        val raceWriter = Thread {
            runCatching { racePorts.revoke("race") }.onFailure(raceWriteError::set)
        }
        val raceReader = Thread {
            raceReadStarted.countDown()
            runCatching {
                racePorts.recallExact("race", "secret", 1, 16, 1L, 0L).status
            }.onSuccess(raceReadStatus::set).onFailure(raceReadError::set)
        }
        raceWriter.start()
        try {
            check(racePersistEntered.await(5L, java.util.concurrent.TimeUnit.SECONDS)) {
                "C2_TEST_REVOKE_NOT_STARTED"
            }
            raceReader.start()
            check(raceReadStarted.await(5L, java.util.concurrent.TimeUnit.SECONDS)) {
                "C2_TEST_READER_NOT_STARTED"
            }
        } finally {
            racePersistRelease.countDown()
        }
        raceWriter.join(5000L)
        raceReader.join(5000L)
        verify(!raceWriter.isAlive && !raceReader.isAlive &&
            raceWriteError.get()?.message == "C2_TEST_TOMBSTONE_WRITE_FAILED" &&
            raceReadError.get() == null && raceReadStatus.get() == ExactStatus.DENIED)
        // The unrevoked raw store remains readable: only the gateway is protected.
        verify(raceExact.read("race", "secret", 1, 16, 1L, 0L).status == ExactStatus.COMPLETE)

        // C2: a future revoke must not serialize a snapshot the existing parser rejects.
        val capacityKey = key()
        var capacityBytes: ByteArray? = null
        val capacityIndex = UnoSemanticMemory(capacityKey, "boot-a",
            { capacityBytes?.copyOf() }, { capacityBytes = it.copyOf() })
        repeat(256) { capacityIndex.dropScope("scope-$it") }
        val lastValidSnapshot = capacityBytes!!.copyOf()
        verify(capacityIndex.isScopeRevoked("scope-0") &&
            capacityIndex.isScopeRevoked("scope-255"))
        verify(runCatching { capacityIndex.dropScope("scope-256") }.exceptionOrNull()
            ?.message == "SEMANTIC_REVOKE_CAPACITY")
        verify(capacityBytes!!.contentEquals(lastValidSnapshot))
        val capacityReopened = UnoSemanticMemory(capacityKey, "boot-a",
            { capacityBytes?.copyOf() }, { capacityBytes = it.copyOf() })
        verify(capacityReopened.isScopeRevoked("scope-255") &&
            !capacityReopened.isScopeRevoked("scope-256"))
        println("UNO_SEMANTIC_MEMORY_HOST_PASS=$pass")
    }
}
