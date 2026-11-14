package org.unovyra.uno.core

import java.io.IOException
import java.io.RandomAccessFile
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger

/** Host-only causal evidence and replay regressions. This is NOT Android authority. */
object ActionReceiptRecoveryTest {
    var pass = 0
    private val effect = mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY")
    private fun test(label: String, block: () -> Unit) {
        block(); pass++; println("PASS RECEIPT_REPLAY $label")
    }
    private fun file() = Files.createTempDirectory("uno-receipt-").resolve("actions.bin").toFile()
    private fun proposal() = Proposal(15, "local|note".toByteArray(), "fixture", 11, "trace")
    private fun ticket(c: TrustController): Ticket {
        val p = proposal()
        val consent = Consent(c.proposalDigest(p), effect.getValue(15), 200, c.epoch, c.nonce, true)
        return c.prepare(p, consent, 0, 200) ?: error("prepare failed")
    }
    private fun native(
        getEvidence: (Ticket, Long) -> NativeEvidence = { t, now ->
            NativeEvidence(t.id, NativeEndpoint.TRUE, 1, now, "RECEIPT_FIXTURE")
        },
        count: AtomicInteger = AtomicInteger()
    ): NativePort = object : NativePort {
        override val trustedSourceTag = "RECEIPT_FIXTURE"
        override fun dispatch(ticket: Ticket): NativeEndpoint {
            count.incrementAndGet()
            return NativeEndpoint.TRUE
        }
        override fun readback(ticket: Ticket, nowNanos: Long): NativeEvidence = getEvidence(ticket, nowNanos)
    }
    fun run() {
        test("one synced positive receipt survives reopen") {
            val f = file()
            val tid: String
            ActionIntentJournal(f).use { j ->
                val c = TrustController(native(), InMemoryLedger(), effect, j)
                val t = ticket(c); tid = t.id
                check(c.dispatchOutcome(t, 5) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
                check(c.readbackAndCommit(t, 7) && t.used && t.phase == Phase.COMMITTED)
                val row = j.snapshot().single()
                check(row.phase == ActionIntentJournal.Phase.REFERENCE_USED_RECEIPT)
                val receipt = row.receipt ?: error("receipt missing")
                check(receipt.ticketId == tid && receipt.observedAtNanos == 7L)
            }
            ActionIntentJournal(f).use { j ->
                val row = j.snapshot().single()
                check(row.recovered && row.phase == ActionIntentJournal.Phase.REFERENCE_USED_RECEIPT)
                val receipt = row.receipt ?: error("receipt missing after replay")
                check(receipt.ticketId == tid && receipt.endpoint == NativeEndpoint.TRUE)
                check(!j.arm(row.id, row.proposalSha256))
            }
        }
        test("stale readback predating native admission never commits") {
            ActionIntentJournal(file()).use { j ->
                val n = native({ t, _ -> NativeEvidence(t.id, NativeEndpoint.TRUE, 1, 4, "RECEIPT_FIXTURE") })
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = ticket(c)
                check(c.dispatchOutcome(t, 5) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                check(!c.readbackAndCommit(t, 8))
                check(!t.used && t.readback == null && t.phase == Phase.WAIT_READBACK)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        test("same monotonic timestamp as admission may be valid") {
            ActionIntentJournal(file()).use { j ->
                val n = native({ t, _ -> NativeEvidence(t.id, NativeEndpoint.TRUE, 1, 5, "RECEIPT_FIXTURE") })
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = ticket(c)
                check(c.dispatchOutcome(t, 5) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                check(c.readbackAndCommit(t, 5))
                check(j.snapshot().single().receipt?.observedAtNanos == 5L)
            }
        }
        test("native-readback time from future is refused") {
            ActionIntentJournal(file()).use { j ->
                val n = native({ t, _ -> NativeEvidence(t.id, NativeEndpoint.TRUE, 1, 99, "RECEIPT_FIXTURE") })
                val c = TrustController(n, InMemoryLedger(), effect, j)
                val t = ticket(c)
                c.dispatchOutcome(t, 5)
                check(!c.readbackAndCommit(t, 8))
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        test("journal STOP after native blocks success even if ledger says yes") {
            val f = file()
            ActionIntentJournal(f).use { j ->
                val c = TrustController(native(), InMemoryLedger(), effect, j)
                val t = ticket(c)
                check(c.dispatchOutcome(t, 5) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                j.stop()
                check(!c.readbackAndCommit(t, 7))
                check(!t.used && t.phase == Phase.MAY_HAVE_EXECUTED)
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
            ActionIntentJournal(f).use { recovered ->
                check(recovered.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        test("receipt invalid id/digest/source/generation refused") {
            ActionIntentJournal(file()).use { j ->
                val c = TrustController(native(), InMemoryLedger(), effect, j)
                val t = ticket(c)
                c.dispatchOutcome(t, 2)
                val ok = NativeEvidence(t.id, NativeEndpoint.TRUE, 1, 4, "RECEIPT_FIXTURE")
                check(!j.recordReadbackClaim("other", t.proposalDigest, ok))
                check(!j.recordReadbackClaim(t.id, "b".repeat(64), ok))
                check(!j.recordReadbackClaim(t.id, t.proposalDigest, ok.copy(ticketId="other")))
                check(!j.recordReadbackClaim(t.id, t.proposalDigest, ok.copy(nativeGeneration=0)))
                check(!j.recordReadbackClaim(t.id, t.proposalDigest, ok.copy(source="bad/source")))
                check(!j.recordReadbackClaim(t.id, t.proposalDigest, ok.copy(endpoint=NativeEndpoint.UNKNOWN)))
                check(j.snapshot().single().phase == ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        test("readback claims cannot be added before arm or after replay") {
            val f=file()
            val id:String;val digest:String
            ActionIntentJournal(f).use { j ->
                val c=TrustController(native(),InMemoryLedger(),effect,j)
                val t=ticket(c); id=t.id;digest=t.proposalDigest
                check(!j.recordReadbackClaim(id,digest,NativeEvidence(id,NativeEndpoint.TRUE,1,2,"RECEIPT_FIXTURE")))
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.PREPARED)
            }
            ActionIntentJournal(f).use { j ->
                val row=j.snapshot().single()
                check(row.recovered && !j.arm(id,digest))
                check(!j.recordReadbackClaim(id,digest,NativeEvidence(id,NativeEndpoint.TRUE,1,2,"RECEIPT_FIXTURE")))
            }
        }
        test("duplicate receipt is rejected and cannot overwrite committed evidence") {
            ActionIntentJournal(file()).use { j ->
                val c=TrustController(native(),InMemoryLedger(),effect,j)
                val t=ticket(c)
                c.dispatchOutcome(t,5)
                check(c.readbackAndCommit(t,6))
                val receipt=j.snapshot().single().receipt
                check(!j.recordReadbackClaim(t.id,t.proposalDigest,
                    NativeEvidence(t.id,NativeEndpoint.TRUE,2,30,"RECEIPT_FIXTURE")))
                check(j.snapshot().single().receipt==receipt)
            }
        }
        test("corrupt claimed receipt stops recovery without auto repair") {
            val f=file()
            ActionIntentJournal(f).use { j ->
                val c=TrustController(native(),InMemoryLedger(),effect,j)
                val t=ticket(c); c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            val before=f.length()
            RandomAccessFile(f,"rw").use { r ->
                r.seek(before-1);val byte=r.readUnsignedByte();r.seek(before-1);r.writeByte(byte xor 0xff)
            }
            var rejected=false
            try { ActionIntentJournal(f).close() } catch (_: IOException) { rejected=true }
            check(rejected && f.length()==before)
        }
        test("truncated claimed receipt stops recovery without repair") {
            val f=file()
            ActionIntentJournal(f).use { j ->
                val c=TrustController(native(),InMemoryLedger(),effect,j)
                val t=ticket(c); c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            RandomAccessFile(f,"rw").use { r -> r.setLength(r.length()-1) }
            val before=f.length()
            var rejected=false
            try { ActionIntentJournal(f).close() } catch (_: IOException) { rejected=true }
            check(rejected && f.length()==before)
        }
        test("journal receipt never triggers replayed native action") {
            val f=file(); val t:Ticket
            ActionIntentJournal(f).use { j ->
                val c=TrustController(native(),InMemoryLedger(),effect,j)
                t=ticket(c);c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            ActionIntentJournal(f).use { j ->
                val calls=AtomicInteger()
                val c=TrustController(native(count=calls),InMemoryLedger(),effect,j)
                check(c.dispatchOutcome(t,7) === DispatchAttempt.Unresolved)
                check(calls.get()==0)
                check(!j.arm(t.id,t.proposalDigest))
            }
        }
        println("ACTION_RECEIPT_RECOVERY_PASS=$pass")
    }
}
fun main() { ActionReceiptRecoveryTest.run() }
