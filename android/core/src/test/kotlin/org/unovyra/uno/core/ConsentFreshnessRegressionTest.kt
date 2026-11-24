package org.unovyra.uno.core

import java.nio.file.Files

/** Erratum 09 / C1: controlled monotonic clocks, synthetic native endpoint only. */
object ConsentFreshnessRegressionTest {
    var pass = 0
    private val effects = mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY")
    private fun proposal() = Proposal(15, "k|v".toByteArray(), "FIXTURE", 1L, "trace")
    private fun consent(c: TrustController, p: Proposal = proposal(), expiry: Long = 10L) =
        Consent(c.proposalDigest(p), effects.getValue(15), expiry, c.epoch, c.nonce, true)
    private class Native(private val duringRead: () -> Unit = {}) : NativePort {
        override val trustedSourceTag = "FAKE_C1_TEST"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return NativeEndpoint.TRUE }
        override fun readback(ticket: Ticket, nowNanos: Long): NativeEvidence {
            duringRead()
            return NativeEvidence(ticket.id, NativeEndpoint.TRUE, calls.toLong(), nowNanos, trustedSourceTag)
        }
    }
    private fun verify(name: String, block: () -> Unit) { block(); pass++; println("PASS C1 $name") }
    fun run() {
        verify("consent expiry bounds ticket even in legacy host clock mode") {
            val n = Native(); val c = TrustController(n, InMemoryLedger(), effects)
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            check(t.deadlineNanos == 10L)
            check(c.dispatchOutcome(t, 10) is DispatchAttempt.Rejected && n.calls == 0)
        }
        verify("stale caller timestamp cannot extend consent") {
            var now = 1L; val n = Native()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            now = 10L
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Rejected && n.calls == 0)
        }
        verify("before expiry is allowed in synthetic reference") {
            var now = 1L; val n = Native()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            now = 9L
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Invoked && n.calls == 1)
            check(c.readbackAndCommit(t, 1))
        }
        verify("task deadline earlier than consent") {
            var now = 1L; val n = Native()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 5))
            check(t.deadlineNanos == 5L)
            now = 5L
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Rejected && n.calls == 0)
        }
        verify("regressing trusted clock fails closed") {
            var now = 5L; val n = Native()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            now = 4L
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Rejected && n.calls == 0)
        }
        verify("throwing trusted clock fails closed") {
            var fail = false; val n = Native()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { if (fail) error("clock") else 1L })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            fail = true
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Rejected && n.calls == 0)
        }
        verify("clock rechecked after durable journal arm") {
            var sample = 0; val n = Native()
            val path = Files.createTempDirectory("uno-c1-").resolve("journal.bin").toFile()
            ActionIntentJournal(path).use { j ->
                val c = TrustController(n, InMemoryLedger(), effects, j, trustedClockNanos = {
                    sample++
                    if (sample >= 3) 10L else 1L
                })
                val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
                check(c.dispatchOutcome(t, 1) is DispatchAttempt.Rejected && n.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
                check(!j.arm(t.id, t.proposalDigest))
            }
        }
        verify("expiry during independent readback blocks positive commit") {
            var now = 1L; val n = Native { now = 10L }
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val t = checkNotNull(c.prepare(proposal(), consent(c), 1, 100))
            check(c.dispatchOutcome(t, 1) is DispatchAttempt.Invoked && n.calls == 1)
            check(!c.readbackAndCommit(t, 1) && !t.used && t.phase != Phase.COMMITTED)
            check(c.dispatchOutcome(t, 1) == DispatchAttempt.Unresolved && n.calls == 1)
        }
        verify("owner callback delay cannot authorize with old event time") {
            var now = 1L; val n = Native(); val p = proposal()
            val c = TrustController(n, InMemoryLedger(), effects, trustedClockNanos = { now })
            val owner = object : AuthenticatedOwnerUi {
                override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent {
                    val token = consent(c, proposal)
                    now = 10L
                    return token
                }
            }
            val neural = object : NeuralPort {
                override fun perceive(event: Percept) = NeuralOutput("FIXTURE", p)
            }
            val cycle = UnoFoundationReferenceCycle(neural, ExactMemory(), c, owner, trustedClockNanos = { now })
            val result = cycle.accept(Percept(PerceptType.TEXT, byteArrayOf(1), "TEST", 1), 1, 100, "session", 0)
            check(result.status == FoundationReferenceStatus.TRUST_REJECTED && n.calls == 0)
        }
        println("UNO_C1_HOST_PASS=$pass")
    }
}
