package org.unovyra.uno.core

import javax.crypto.KeyGenerator

object UnoEncryptedExactMemoryTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private fun key() = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

    fun run() {
        val secret = key()
        var stored: ByteArray? = null
        var now = 100L
        var failWrite = false
        val load = { stored?.copyOf() }
        val persist: (ByteArray) -> Unit = { b ->
            if (failWrite) error("disk full")
            stored = b.copyOf()
        }
        val boot = "boot-test-a"
        val source = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        val raw = "Привет, UNO".toByteArray(Charsets.UTF_8)
        val entry = source.write("owner", "conversation:1", raw, 500L, 3L,
            EntryKind.OBSERVED, "LOCAL_UI")
        verify(entry.id == 1L && entry.generation == 1L && source.generation == 1L)
        verify(stored != null && !String(stored!!, Charsets.ISO_8859_1).contains("Привет"))
        raw[0] = 0
        entry.raw[0] = 0
        verify(source.read("owner", "conversation:1", 1, 2, 100L, 3L)
            .entries.single().raw.decodeToString() == "Привет, UNO")
        val restored = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        val read = restored.read("owner", "conversation:1", 2, 2, now, 3L)
        verify(read.status == ExactStatus.COMPLETE && read.entries.size == 1)
        verify(read.entries.single().id == 1L && restored.generation == 1L)
        verify(restored.read("other", "conversation:1", 1, 2, now, 3L).status == ExactStatus.NOT_FOUND)
        verify(restored.read("owner", "conversation:1", 1, 0, now, 3L).status == ExactStatus.TRUNCATED)
        verify(restored.read("owner", "conversation:1", 1, 2, now, 4L).status == ExactStatus.UNKNOWN)

        val b = restored.write("owner", "conversation:1", "other".toByteArray(), 500L, 3L,
            EntryKind.USER_DECLARATION, "OWNER_UI")
        verify(b.id == 2L && restored.generation == 2L)
        verify(restored.read("owner", "conversation:1", 2, 2, now, 3L).status == ExactStatus.CONFLICT)
        verify(restored.read("owner", "conversation:1", 1, 2, now, 3L).status == ExactStatus.TRUNCATED)
        val s = restored.write("owner", "conversation:1", "summary".toByteArray(), 500L, 3L,
            EntryKind.SEMANTIC_SUMMARY, "UNTRUSTED_MODEL")
        verify(s.id == 3L && restored.read("owner", "conversation:1", 2, 3, now, 3L).status == ExactStatus.CONFLICT)
        verify(restored.read("owner", "missing", 2, 3, now, 3L).status == ExactStatus.NOT_FOUND)
        verify(runCatching {
            restored.write("owner", "false-success", byteArrayOf(1), 500L, 3L,
                EntryKind.VERIFIED_COMPLETION, "MODEL")
        }.isFailure)
        verify(restored.generation == 3L)

        failWrite = true
        verify(runCatching { restored.write("owner", "write-fail", byteArrayOf(1), 500L, 3L,
            EntryKind.OBSERVED, "LOCAL_UI") }.isFailure)
        verify(restored.generation == 3L && restored.read("owner", "write-fail", 1, 3, now, 3L)
            .status == ExactStatus.NOT_FOUND)
        failWrite = false
        val staleBoot = UnoEncryptedExactMemory(secret, "boot-test-b", load, persist) { now }
        verify(staleBoot.read("owner", "conversation:1", 2, 3, now, 3L).status == ExactStatus.UNKNOWN)
        now = 600L
        verify(restored.read("owner", "conversation:1", 2, 3, 100L, 3L).status == ExactStatus.NOT_FOUND)
        now = 100L

        val beforeRevoked = stored!!.copyOf()
        failWrite = true
        verify(runCatching { restored.revoke("owner") }.isFailure)
        verify(restored.read("owner", "conversation:1", 2, 3, now, 3L).status == ExactStatus.CONFLICT)
        failWrite = false
        restored.revoke("owner")
        verify(restored.read("owner", "conversation:1", 2, 3, now, 3L).status == ExactStatus.DENIED)
        verify(restored.generation == 4L)
        verify(runCatching { restored.write("owner", "new", byteArrayOf(1), 500L, 3L,
            EntryKind.OBSERVED, "LOCAL_UI") }.isFailure)
        val afterRevocation = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        verify(afterRevocation.read("owner", "conversation:1", 2, 3, now, 3L).status == ExactStatus.DENIED)
        val next = afterRevocation.write("new-scope", "key", byteArrayOf(4), 500L, 3L,
            EntryKind.OBSERVED, "LOCAL_UI")
        verify(next.id == 5L && next.generation == 5L)

        val corrupt = stored!!.copyOf().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }
        verify(runCatching { UnoEncryptedExactMemory(secret, boot, { corrupt }, persist) { now } }.isFailure)
        verify(runCatching { UnoEncryptedExactMemory(key(), boot, { stored }, persist) { now } }.isFailure)
        verify(runCatching { UnoEncryptedExactMemory(secret, boot, { beforeRevoked.copyOf(8) }, persist) { now } }.isFailure)
        verify(runCatching { UnoEncryptedExactMemory(secret, "", load, persist) { now } }.isFailure)
        // Actual foundation reference cycle now accepts a durable exact-memory port.
        val cycleBytes = "one observed event".toByteArray(Charsets.UTF_8)
        val liveVault = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        val reference = UnoFoundationReferenceCycle(
            NoWeightsNeuralPort(), liveVault,
            TrustController(FakeNotesPort(), InMemoryLedger()),
            object : AuthenticatedOwnerUi {
                override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
            }
        )
        val event = Percept(PerceptType.TEXT, cycleBytes, "UNVERIFIED_INPUT", 100L)
        val observed = reference.accept(event, 100L, 500L, "device-event", 3L)
        verify(observed.status == FoundationReferenceStatus.MODEL_UNAVAILABLE &&
            observed.observedEventKey == "event:6" &&
            !observed.verifiedAndroidEffect)
        val reopened = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        val persisted = reopened.read("device-event", "event:6", 1, 4, now, 3L)
        verify(persisted.status == ExactStatus.COMPLETE &&
            persisted.entries.single().raw.contentEquals(cycleBytes))
        verify(persisted.entries.single().kind == EntryKind.OBSERVED)
        verify(runCatching {
            reopened.write("device-event", "fake-outcome", byteArrayOf(1), 500L, 3L,
                EntryKind.VERIFIED_COMPLETION, "FAKE_MODEL")
        }.isFailure)


        // Reload the shared vault and start a fresh cycle: persistently unique event key.
        val afterFirst = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        val secondCycle = UnoFoundationReferenceCycle(
            NoWeightsNeuralPort(), afterFirst,
            TrustController(FakeNotesPort(), InMemoryLedger()),
            object : AuthenticatedOwnerUi {
                override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
            }
        )
        verify(secondCycle.accept(Percept(PerceptType.OS, byteArrayOf(2),
            "ANDROID_LOCAL_SNAPSHOT", 101L), 101L, 500L, "device-event", 3L).status ==
            FoundationReferenceStatus.MODEL_UNAVAILABLE)
        val newReload = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        verify(newReload.read("device-event", "event:7", 1, 8, now, 3L)
            .entries.single().raw.contentEquals(byteArrayOf(2)))
        verify(newReload.read("device-event", "event:6", 1, 8, now, 3L)
            .entries.single().raw.contentEquals(cycleBytes))
        // Two independent reference cycles share one persistent memory writer.
        // Their event:keys must be allocated in the same lock as the write.
        val shared = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        fun referenceCycle() = UnoFoundationReferenceCycle(
            NoWeightsNeuralPort(), shared,
            TrustController(FakeNotesPort(), InMemoryLedger()),
            object: AuthenticatedOwnerUi {
                override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
            }
        )
        val first = referenceCycle()
        val second = referenceCycle()
        val ready = java.util.concurrent.CountDownLatch(1)
        val finished = java.util.concurrent.CountDownLatch(2)
        val status = java.util.Collections.synchronizedList(
            mutableListOf<FoundationReferenceStatus>())
        listOf(first, second).forEachIndexed { i, cycle ->
            Thread {
                try {
                    ready.await(2, java.util.concurrent.TimeUnit.SECONDS)
                    status.add(cycle.accept(Percept(PerceptType.OS,
                        byteArrayOf((i + 10).toByte()), "ANDROID_LOCAL", 102L + i),
                        105L, 500L, "device-event", 3L).status)
                } finally { finished.countDown() }
            }.start()
        }
        ready.countDown()
        verify(finished.await(3, java.util.concurrent.TimeUnit.SECONDS))
        verify(status.size == 2 && status.all {
            it == FoundationReferenceStatus.MODEL_UNAVAILABLE
        })
        val persistedBoth = UnoEncryptedExactMemory(secret, boot, load, persist) { now }
        verify(persistedBoth.read("device-event", "event:8", 1, 12, now, 3L).status ==
            ExactStatus.COMPLETE)
        verify(persistedBoth.read("device-event", "event:9", 1, 12, now, 3L).status ==
            ExactStatus.COMPLETE)
        // Android first-use mode: the empty authenticated genesis is persisted
        // before opening; a restart must read the same revision=0 vault.
        val bootstrapKey = key()
        var genesis: ByteArray? = null
        val bootstrapPersist: (ByteArray) -> Unit = { data -> genesis = data.copyOf() }
        val initialized = UnoEncryptedExactMemory(bootstrapKey, boot,
            { genesis?.copyOf() }, bootstrapPersist,
            initializeEmptyOnFirstOpen = true) { 100L }
        verify(genesis != null && initialized.generation == 0L)
        val genesisCopy = genesis!!.copyOf()
        val restart = UnoEncryptedExactMemory(bootstrapKey, boot,
            { genesis?.copyOf() }, bootstrapPersist,
            initializeEmptyOnFirstOpen = true) { 100L }
        verify(restart.generation == 0L && genesis!!.contentEquals(genesisCopy))
        verify(restart.read("new", "unknown", 1, 0, 100L, 0L).status == ExactStatus.NOT_FOUND)
        verify(runCatching {
            UnoEncryptedExactMemory(bootstrapKey, boot, { null },
                { _: ByteArray -> error("BOOTSTRAP_IO_ERROR") },
                initializeEmptyOnFirstOpen = true) { 100L }
        }.isFailure)
        verify(runCatching {
            UnoEncryptedExactMemory(bootstrapKey, boot, { byteArrayOf(1, 2, 3) },
                bootstrapPersist, initializeEmptyOnFirstOpen = true) { 100L }
        }.isFailure)
        verify(genesis!!.contentEquals(genesisCopy))
        verify(exactFirstOpen(ExactVaultResidue.COMMITTED, true, false, false) ==
            ExactFirstOpen.REOPEN_COMMITTED)
        verify(exactFirstOpen(ExactVaultResidue.NONE, true, false, false) ==
            ExactFirstOpen.WRITE_GENESIS)
        verify(exactFirstOpen(ExactVaultResidue.NONE, false, false, false) ==
            ExactFirstOpen.WRITE_GENESIS)
        verify(exactFirstOpen(ExactVaultResidue.NONE, true, true, false) ==
            ExactFirstOpen.REJECT_READONLY_EMPTY)
        verify(exactFirstOpen(ExactVaultResidue.PARTIAL, true, false, true) ==
            ExactFirstOpen.PROMOTE_PARTIAL)
        verify(exactFirstOpen(ExactVaultResidue.PARTIAL, true, false, false) ==
            ExactFirstOpen.REJECT_PARTIAL)
        verify(exactFirstOpen(ExactVaultResidue.PARTIAL, false, false, true) ==
            ExactFirstOpen.REJECT_PARTIAL)
        verify(runCatching {
            exactFirstOpen(ExactVaultResidue.COMMITTED, false, false, false)
        }.isFailure)
        verify(exactPartialAuthentic(genesisCopy, bootstrapKey))
        verify(!exactPartialAuthentic(byteArrayOf(9, 9, 9), bootstrapKey))
        println("UNO_ENCRYPTED_EXACT_MEMORY_HOST_PASS=$pass")
    }
}
