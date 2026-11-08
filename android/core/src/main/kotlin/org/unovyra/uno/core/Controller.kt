package org.unovyra.uno.core

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicBoolean
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Single-writer reference controller: no system privileges and no durable IO.
 * The production version REQUIRES real Android auth, A_tx/A_fs and native evidence.
 */
class TrustController(
    private val native: NativePort,
    private val ledger: DurableLedger,
    private val allowedEffects: Map<Int, String> = emptyMap(),
    // Opt-in host/reference outbox bridge. The real Android path still requires owner/OS authority.
    private val intentJournal: ActionIntentJournal? = null
) {
    // Reference gate only. Production dispatch still requires Android owner auth and a durable WAL.
    // A ticket is valid only if this trusted controller issued it; caller-mutable Ticket is not authority.
    private data class Issued(
        val ticket: Ticket,
        var dispatched: Boolean = false,
        var nativeAdmittedAtNanos: Long = -1L
    )
    private val issued = linkedMapOf<String, Issued>()
    private val stopLatch = AtomicBoolean(false)
    val stopped: Boolean get() = stopLatch.get()
    private val rng = SecureRandom()
    private fun freshNonce(): String = ByteArray(16).also(rng::nextBytes).joinToString("") { "%02x".format(it) }
    var epoch = 0L
        private set
    var nonce: String = freshNonce()
        private set
    private var serial = 0L

    fun proposalDigest(p: Proposal): String {
        // Explicit bounded bytes; no untrusted repr serialization.
        val md = MessageDigest.getInstance("SHA-256")
        fun field(bytes: ByteArray) {
            md.update(ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(bytes.size).array())
            md.update(bytes)
        }
        field(ByteBuffer.allocate(4).putInt(p.verb).array())
        field(p.canonicalArgs)
        field(p.modelDigest.toByteArray(Charsets.UTF_8))
        field(ByteBuffer.allocate(8).putLong(p.goalId).array())
        field(p.traceDigest.toByteArray(Charsets.UTF_8))
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    @Synchronized fun prepare(p: Proposal, consent: Consent, now: Long, deadline: Long): Ticket? {
        if (stopLatch.get() || now < 0 || deadline <= now || issued.size >= UnoAbi.MAX_PENDING ||
            p.verb !in 3..23 || !allowedEffects.containsKey(p.verb)) return null
        // Snapshot mutable bytes BEFORE binding consent. Caller may mutate its Proposal after prepare().
        val frozen = p.copy(canonicalArgs = p.canonicalArgs.copyOf())
        val d = proposalDigest(frozen)
        if (!consent.ownerUnlocked || consent.proposalDigest != d ||
            consent.effectName != allowedEffects[p.verb] || consent.epoch != epoch ||
            consent.nonce != nonce || now >= consent.expiresAtNanos || now >= deadline ||
            consent.expiresAtNanos < 0 || deadline <= 0) return null
        if (serial == Long.MAX_VALUE) { stop(); return null }
        val t = Ticket("$nonce:$epoch:${++serial}",frozen,d,epoch,nonce,deadline,allowedEffects[p.verb]!!,Phase.PREPARED)
        // Persist immutable intent BEFORE making the ticket dispatchable. An orphan PREPARED
        // record if the next step fails is deliberately safe: recovery never auto-dispatches.
        if (intentJournal != null && !intentJournal.prepare(t.id, d)) return null
        if (stopLatch.get() || !ledger.prepare(t)) return null
        issued[t.id] = Issued(t)
        return t
    }

    /** This is an in-memory, host-only state machine; never wire a privileged Android port here.
     * Admission/dispatch and STOP use the same monitor. A call admitted before STOP may already
     * be in flight; STOP blocks new calls but cannot undo native effects.
     */
    /**
     * Legacy adapter for existing host-only call sites. This intentionally loses the difference
     * between pre-dispatch refusal and a native endpoint FALSE. Never use its return as a label.
     */
    @Deprecated("Ambiguous pre-dispatch FALSE; use dispatchOutcome() and independent readback")
    fun dispatch(t: Ticket, now: Long): NativeEndpoint = when (val outcome = dispatchOutcome(t, now)) {
        is DispatchAttempt.Rejected -> NativeEndpoint.FALSE
        is DispatchAttempt.Invoked -> outcome.nativeReturn
        DispatchAttempt.Unresolved -> NativeEndpoint.UNKNOWN
    }

    /**
     * Explicit causal status. No OS observation or independent endpoint evidence is created here.
     * Reference-only: synchronized callback still has an OS linearization/STOP race. Keep deny-all
     * Android wiring until a separately audited trusted Android dispatcher is implemented.
     */
    @Synchronized fun dispatchOutcome(t: Ticket, now: Long): DispatchAttempt {
        val record = issued[t.id] ?: return when (t.phase) {
            Phase.PREPARED, Phase.CANCELLED, Phase.DENIED ->
                DispatchAttempt.Rejected(DispatchRejection.NOT_ISSUED)
            else -> DispatchAttempt.Unresolved // unknown older disposition, no call in this attempt
        }
        if (record.ticket !== t) return DispatchAttempt.Rejected(DispatchRejection.WRONG_TICKET)
        if (record.dispatched) return DispatchAttempt.Unresolved // one-shot; never redispatch
        if (t.phase != Phase.PREPARED || t.used)
            return DispatchAttempt.Rejected(DispatchRejection.CLOSED_TICKET)
        if (stopLatch.get() || t.epoch != epoch || t.nonce != nonce || now < 0 || now >= t.deadlineNanos) {
            t.phase = Phase.CANCELLED
            issued.remove(t.id)
            return DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED)
        }
        val forNative = t.copy(proposal = t.proposal.copy(canonicalArgs = t.proposal.canonicalArgs.copyOf()))
        if (proposalDigest(forNative.proposal) != t.proposalDigest) {
            t.phase = Phase.DENIED
            issued.remove(t.id)
            return DispatchAttempt.Rejected(DispatchRejection.DIGEST_MISMATCH)
        }
        // A durable intent must be synced before any native call. The journal is not permission.
        if (intentJournal != null && !intentJournal.arm(t.id, t.proposalDigest)) {
            t.phase = Phase.CANCELLED
            issued.remove(t.id)
            return DispatchAttempt.Rejected(DispatchRejection.JOURNAL_UNAVAILABLE)
        }
        if (stopLatch.get()) {
            t.phase = Phase.CANCELLED
            issued.remove(t.id)
            return DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED)
        }
        record.dispatched = true
        record.nativeAdmittedAtNanos = now
        t.phase = Phase.MAY_HAVE_EXECUTED
        val result = try { native.dispatch(forNative) } catch (_: Exception) { NativeEndpoint.UNKNOWN }
        if (result == NativeEndpoint.UNKNOWN) {
            t.phase = Phase.MAY_HAVE_EXECUTED
        } else if (!stopLatch.get()) {
            t.phase = Phase.WAIT_READBACK
        }
        return DispatchAttempt.Invoked(result)
    }

    @Synchronized fun readbackAndCommit(t: Ticket, now: Long): Boolean {
        val record = issued[t.id] ?: return false
        if (record.ticket !== t || !record.dispatched || stopLatch.get() ||
            t.phase != Phase.WAIT_READBACK || t.used || now < 0 ||
            record.nativeAdmittedAtNanos < 0 || now < record.nativeAdmittedAtNanos) return false
        val forNative = t.copy(proposal = t.proposal.copy(canonicalArgs = t.proposal.canonicalArgs.copyOf()))
        if (proposalDigest(forNative.proposal) != t.proposalDigest) return false
        val evidence = try { native.readback(forNative, now) } catch (_: Exception) { return false }
        if (stopLatch.get() || t.epoch != epoch || t.nonce != nonce || now >= t.deadlineNanos ||
            evidence.ticketId != t.id || evidence.source != native.trustedSourceTag ||
            evidence.nativeGeneration <= 0 || evidence.observedAtNanos > now ||
            evidence.observedAtNanos < record.nativeAdmittedAtNanos) return false
        // FALSE is verified NON-success, and UNKNOWN is not evidence of completion.
        if (evidence.endpoint != NativeEndpoint.TRUE) {
            if (evidence.endpoint == NativeEndpoint.FALSE) t.phase = Phase.DENIED
            return false
        }
        if (intentJournal != null) {
            // For the reference path only: the legacy ledger must be demonstrably transient.
            // Never silently split a future durable ledger and this journal into two commits.
            // This single fsynced v2 record binds reference used=true + positive receipt;
            // it does NOT bind P-version, semantic memory, Android trust or OS causality.
            if (ledger !is InMemoryLedger || !ledger.commit(t, evidence) ||
                !intentJournal.recordReferenceUsedReceipt(t.id, t.proposalDigest, evidence)) {
                t.phase = Phase.MAY_HAVE_EXECUTED
                return false
            }
        } else if (!ledger.commit(t, evidence)) return false
        t.readback = evidence
        t.used = true
        t.phase = Phase.COMMITTED
        issued.remove(t.id)
        return true
    }

    fun stop() {
        stopLatch.set(true) // signal immediately, even while native.dispatch() is in flight
        synchronized(this) {
            if (epoch != Long.MAX_VALUE) epoch++
            issued.values.forEach { record ->
                if (!record.dispatched) record.ticket.phase = Phase.CANCELLED
                else if (record.ticket.phase != Phase.COMMITTED) record.ticket.phase = Phase.MAY_HAVE_EXECUTED
            }
            issued.clear()
        }
    }

    @Synchronized fun recoverAfterProcessDeath() {
        stopLatch.set(true)
        if (epoch != Long.MAX_VALUE) epoch++
        nonce = freshNonce()
        issued.clear()
        // Persistent implementation MUST reconcile durable records; never automatically redispatch.
        ledger.unresolved().forEach { if (it.phase != Phase.COMMITTED) it.phase = Phase.MAY_HAVE_EXECUTED }
    }

}

/** Explicitly transient test double; NO claim of transaction durability. */
class InMemoryLedger : DurableLedger {
    val items = linkedMapOf<String,Ticket>()
    override fun prepare(ticket: Ticket): Boolean {
        if (items.size >= UnoAbi.MAX_PENDING || items.containsKey(ticket.id)) return false
        items[ticket.id]=ticket
        return true
    }
    override fun commit(ticket: Ticket,evidence: NativeEvidence): Boolean = items[ticket.id] === ticket && !ticket.used
    override fun unresolved(): List<Ticket> = items.values.filter { it.phase != Phase.COMMITTED }
}

/** Synthetic local-only native port, to exercise state machine on JVM. */
class FakeNotesPort : NativePort {
    override val trustedSourceTag = "FAKE_JVM_NOTE"
    private val notes=mutableMapOf<String,String>()
    private var generation=0L
    override fun dispatch(ticket: Ticket): NativeEndpoint {
        if (ticket.proposal.verb != 15) return NativeEndpoint.UNKNOWN
        val pieces = ticket.proposal.canonicalArgs.toString(Charsets.UTF_8).split('|',limit=2)
        if (pieces.size != 2 || pieces[0].isEmpty()) return NativeEndpoint.UNKNOWN
        val prior = notes[pieces[0]]
        if (prior != null && prior != pieces[1]) return NativeEndpoint.FALSE
        notes[pieces[0]]=pieces[1];generation++
        return NativeEndpoint.TRUE
    }
    override fun readback(ticket: Ticket,nowNanos: Long): NativeEvidence {
        val p = ticket.proposal.canonicalArgs.toString(Charsets.UTF_8).split('|',limit=2)
        val ok=p.size==2 && notes[p[0]]==p[1]
        return NativeEvidence(ticket.id,if(ok) NativeEndpoint.TRUE else NativeEndpoint.FALSE,generation,nowNanos,trustedSourceTag)
    }
}
