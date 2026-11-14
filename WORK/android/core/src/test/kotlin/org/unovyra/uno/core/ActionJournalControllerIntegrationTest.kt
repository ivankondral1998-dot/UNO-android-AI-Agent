package org.unovyra.uno.core

import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger

/** JVM-only cross-check between controller, persistent outbox and fake native effect. */
object ActionJournalControllerIntegrationTest {
    var pass = 0
    private fun verify(name: String, block: () -> Unit) {
        block(); pass++; println("PASS CONTROLLER_OUTBOX $name")
    }
    private fun file() = Files.createTempDirectory("uno-controller-outbox-").resolve("actions.bin").toFile()
    private val effect = mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY")
    private fun proposal() = Proposal(15, "k|value".toByteArray(), "test-only-model", 1, "test-trace")
    private fun prepare(c: TrustController, p: Proposal = proposal()): Ticket {
        val consent = Consent(c.proposalDigest(p), effect.getValue(15), 100, c.epoch, c.nonce, true)
        return c.prepare(p, consent, 0, 100) ?: error("prepare blocked")
    }
    private class ProbeNative(private val checkBeforeDispatch: (Ticket) -> Unit) : NativePort {
        override val trustedSourceTag = "FAKE_INTEGRATION"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint {
            calls++
            checkBeforeDispatch(ticket)
            return NativeEndpoint.TRUE
        }
        override fun readback(ticket: Ticket, nowNanos: Long) =
            NativeEvidence(ticket.id, NativeEndpoint.TRUE, 1, nowNanos, trustedSourceTag)
    }
    fun run() {
        verify("durable PREPARED precedes ticket admission") {
            ActionIntentJournal(file()).use { j ->
                val c = TrustController(ProbeNative { }, InMemoryLedger(), effect, j)
                val t = prepare(c)
                val row = j.snapshot().single()
                check(row.id == t.id && row.proposalSha256 == t.proposalDigest)
                check(row.phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("durable MAY_HAVE_EXECUTED precedes native dispatch") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { t ->
                    val row = j.snapshot().single()
                    check(row.id == t.id && row.phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
                }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                check(c.dispatch(t, 1) == NativeEndpoint.TRUE)
                check(n.calls == 1)
            }
        }
        verify("journal STOP blocks native even with a prepared ticket") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                j.stop()
                check(c.dispatch(t, 1) == NativeEndpoint.FALSE)
                check(n.calls == 0)
            }
        }
        verify("controller STOP blocks native and leaves unarmed PREPARED") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                c.stop()
                check(c.dispatch(t, 1) == NativeEndpoint.FALSE)
                check(n.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("tampered proposal is refused before persistent arm") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                t.proposal.canonicalArgs[0] = 42
                check(c.dispatch(t, 1) == NativeEndpoint.FALSE)
                check(n.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("no replay after previous MAY_HAVE_EXECUTED and process restart") {
            val f = file()
            val oldTicket: Ticket
            ActionIntentJournal(f).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                oldTicket = prepare(c)
                check(c.dispatch(oldTicket, 1) == NativeEndpoint.TRUE)
                check(n.calls == 1)
            }
            ActionIntentJournal(f).use { recovered ->
                val row = recovered.snapshot().single()
                check(row.id == oldTicket.id && row.recovered)
                check(row.phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
                check(!recovered.arm(oldTicket.id, oldTicket.proposalDigest))
                val n = ProbeNative { error("old ticket must not trigger new native dispatch") }
                val c = TrustController(n, InMemoryLedger(), effect, recovered)
                check(c.dispatch(oldTicket, 2) != NativeEndpoint.TRUE)
                check(n.calls == 0)
            }
        }
        verify("fake ticket identity rejected before native") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                val fake = t.copy()
                check(c.dispatch(fake, 1) == NativeEndpoint.FALSE)
                check(n.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("never-issued PREPARED id is pre-native FALSE, not UNKNOWN") {
            ActionIntentJournal(file()).use { j ->
                val native = ProbeNative { }
                val c = TrustController(native, InMemoryLedger(), effect, j)
                val prepared = prepare(c)
                val forgedId = prepared.copy(id = "never-issued-ticket")
                check(c.dispatch(forgedId, 1) == NativeEndpoint.FALSE)
                check(native.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("duplicate dispatch never arms or calls native twice") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = prepare(c)
                check(c.dispatch(t, 1) == NativeEndpoint.TRUE)
                check(c.dispatch(t, 2) == NativeEndpoint.UNKNOWN)
                check(n.calls == 1)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        verify("failed/invalid consent never allocates durable intent") {
            ActionIntentJournal(file()).use { j ->
                val c = TrustController(ProbeNative { }, InMemoryLedger(), effect, j)
                val p = proposal()
                val invalid = Consent("bad", effect.getValue(15), 100, c.epoch, c.nonce, true)
                check(c.prepare(p, invalid, 0, 100) == null)
                check(j.snapshot().isEmpty())
            }
        }
        verify("closed journal denies controller prepare") {
            val j = ActionIntentJournal(file()); j.close()
            val c = TrustController(ProbeNative { }, InMemoryLedger(), effect, j)
            val p = proposal()
            val consent = Consent(c.proposalDigest(p), effect.getValue(15), 100, c.epoch, c.nonce, true)
            check(c.prepare(p, consent, 0, 100) == null)
        }
        verify("native exception stays MAY_HAVE_EXECUTED without retry") {
            ActionIntentJournal(file()).use { j ->
                val calls = AtomicInteger()
                val native = object : NativePort {
                    override val trustedSourceTag = "EXCEPTION_FIXTURE"
                    override fun dispatch(ticket: Ticket): NativeEndpoint {
                        calls.incrementAndGet()
                        throw IllegalStateException("may have acted before throwing")
                    }
                    override fun readback(ticket: Ticket, nowNanos: Long) =
                        NativeEvidence(ticket.id, NativeEndpoint.UNKNOWN, 0, nowNanos, trustedSourceTag)
                }
                val c = TrustController(native, InMemoryLedger(), effect, j)
                val t = prepare(c)
                check(c.dispatch(t, 1) == NativeEndpoint.UNKNOWN)
                check(t.phase == Phase.MAY_HAVE_EXECUTED)
                check(c.dispatch(t, 2) == NativeEndpoint.UNKNOWN && calls.get() == 1)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        verify("rejected ledger leaves safe orphan PREPARED, no native") {
            ActionIntentJournal(file()).use { j ->
                val rejected = object : DurableLedger {
                    override fun prepare(ticket: Ticket) = false
                    override fun commit(ticket: Ticket, evidence: NativeEvidence) = false
                    override fun unresolved(): List<Ticket> = emptyList()
                }
                val native = ProbeNative { }
                val c = TrustController(native, rejected, effect, j)
                val p = proposal()
                val consent = Consent(c.proposalDigest(p), effect.getValue(15), 100, c.epoch, c.nonce, true)
                check(c.prepare(p, consent, 0, 100) == null)
                check(native.calls == 0)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.PREPARED)
            }
        }
        verify("typed PREPARED without issuance is REJECTED not observed FALSE") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val real = prepare(c)
                val fake = real.copy(id = "unissued")
                check(c.dispatchOutcome(fake, 1) ==
                    DispatchAttempt.Rejected(DispatchRejection.NOT_ISSUED))
                check(n.calls == 0)
            }
        }
        verify("typed forged existing ticket is rejected before native") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket.copy(), 1) ==
                    DispatchAttempt.Rejected(DispatchRejection.WRONG_TICKET))
                check(n.calls == 0)
            }
        }
        verify("typed STOP refusal is distinct from native FALSE") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                c.stop()
                check(c.dispatchOutcome(ticket, 1) ==
                    DispatchAttempt.Rejected(DispatchRejection.NOT_ISSUED))
                check(n.calls == 0)
            }
        }
        verify("typed journal refusal is distinct from native UNKNOWN") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                j.stop()
                check(c.dispatchOutcome(ticket, 1) ==
                    DispatchAttempt.Rejected(DispatchRejection.JOURNAL_UNAVAILABLE))
                check(n.calls == 0)
            }
        }
        verify("typed bad digest never becomes a native negative sample") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                ticket.proposal.canonicalArgs[0] = 0
                check(c.dispatchOutcome(ticket, 1) ==
                    DispatchAttempt.Rejected(DispatchRejection.DIGEST_MISMATCH))
                check(n.calls == 0)
            }
        }
        verify("typed native FALSE is INVOKED not REJECTED and not verified") {
            ActionIntentJournal(file()).use { j ->
                val calls = AtomicInteger()
                val native = object : NativePort {
                    override val trustedSourceTag = "FALSE_NATIVE_FIXTURE"
                    override fun dispatch(ticket: Ticket): NativeEndpoint {
                        calls.incrementAndGet(); return NativeEndpoint.FALSE
                    }
                    override fun readback(ticket: Ticket, nowNanos: Long) =
                        NativeEvidence(ticket.id, NativeEndpoint.FALSE, 1, nowNanos, trustedSourceTag)
                }
                val c = TrustController(native, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket, 1) == DispatchAttempt.Invoked(NativeEndpoint.FALSE))
                check(ticket.phase == Phase.WAIT_READBACK && !ticket.used)
                check(calls.get() == 1)
                check(!c.readbackAndCommit(ticket, 2))
                check(ticket.phase == Phase.DENIED)
            }
        }
        verify("typed native TRUE is not independent readback success") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket, 1) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                check(!ticket.used && ticket.readback == null && ticket.phase == Phase.WAIT_READBACK)
                check(n.calls == 1)
                check(c.readbackAndCommit(ticket, 2) && ticket.used)
            }
        }
        verify("typed UNKNOWN is invoked only once; following result is unresolved") {
            ActionIntentJournal(file()).use { j ->
                val calls = AtomicInteger()
                val native = object : NativePort {
                    override val trustedSourceTag = "UNKNOWN_NATIVE_FIXTURE"
                    override fun dispatch(ticket: Ticket): NativeEndpoint {
                        calls.incrementAndGet(); return NativeEndpoint.UNKNOWN
                    }
                    override fun readback(ticket: Ticket, nowNanos: Long) =
                        NativeEvidence(ticket.id, NativeEndpoint.UNKNOWN, 1, nowNanos, trustedSourceTag)
                }
                val c = TrustController(native, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket, 1) == DispatchAttempt.Invoked(NativeEndpoint.UNKNOWN))
                check(c.dispatchOutcome(ticket, 2) === DispatchAttempt.Unresolved)
                check(calls.get() == 1 && ticket.phase == Phase.MAY_HAVE_EXECUTED)
            }
        }
        verify("typed expired ticket is pre-native refusal") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket, 100) ==
                    DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED))
                check(n.calls == 0)
            }
        }
        verify("typed crash-recovered ticket remains unresolved without native") {
            ActionIntentJournal(file()).use { j ->
                val n = ProbeNative { }
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val ticket = prepare(c)
                check(c.dispatchOutcome(ticket, 1) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                c.recoverAfterProcessDeath()
                check(c.dispatchOutcome(ticket, 2) === DispatchAttempt.Unresolved)
                check(n.calls == 1)
            }
        }
        println("ACTION_JOURNAL_CONTROLLER_INTEGRATION_PASS=$pass")
    }
}
fun main() { ActionJournalControllerIntegrationTest.run() }
