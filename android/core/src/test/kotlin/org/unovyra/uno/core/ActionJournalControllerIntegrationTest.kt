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
        println("ACTION_JOURNAL_CONTROLLER_INTEGRATION_PASS=$pass")
    }
}
fun main() { ActionJournalControllerIntegrationTest.run() }
