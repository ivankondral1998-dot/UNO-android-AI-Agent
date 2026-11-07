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
    private val allowedEffects: Map<Int, String> = emptyMap()
) {
    val stopLatch = AtomicBoolean(false)
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

    fun prepare(p: Proposal, consent: Consent, now: Long, deadline: Long): Ticket? {
        if (stopLatch.get() || p.verb !in 3..23 || !allowedEffects.containsKey(p.verb)) return null
        val d = proposalDigest(p)
        if (!consent.ownerUnlocked || consent.proposalDigest != d ||
            consent.effectName != allowedEffects[p.verb] || consent.epoch != epoch ||
            consent.nonce != nonce || now >= consent.expiresAtNanos || now >= deadline ||
            consent.expiresAtNanos < 0 || deadline <= 0) return null
        if (serial == Long.MAX_VALUE) { stop(); return null }
        val t = Ticket("$nonce:$epoch:${++serial}",p,d,epoch,nonce,deadline,allowedEffects[p.verb]!!,Phase.PREPARED)
        return if (ledger.prepare(t)) t else null
    }

    /** Only this function may call native.dispatch; STOP and current epoch gated. */
    fun dispatch(t: Ticket, now: Long): NativeEndpoint {
        if (t.phase != Phase.PREPARED || t.used) return NativeEndpoint.UNKNOWN
        if (stopLatch.get() || t.epoch != epoch || t.nonce != nonce || now >= t.deadlineNanos) {
            t.phase = Phase.CANCELLED
            return NativeEndpoint.UNKNOWN
        }
        // A crash after this point is MAY_HAVE_EXECUTED, never blindly retry.
        t.phase = Phase.MAY_HAVE_EXECUTED
        val response = native.dispatch(t)
        t.phase = Phase.WAIT_READBACK
        return response
    }

    fun readbackAndCommit(t: Ticket, now: Long): Boolean {
        // Evidence originates in native port only. Untrusted worker cannot pass a receipt.
        if (stopLatch.get() || t.phase != Phase.WAIT_READBACK || t.used) return false
        val e = native.readback(t, now)
        if (stopLatch.get() || t.phase != Phase.WAIT_READBACK || t.used || t.epoch != epoch || t.nonce != nonce || now >= t.deadlineNanos) return false
        if (e.ticketId != t.id || e.source != native.trustedSourceTag ||
            e.nativeGeneration <= 0 || e.observedAtNanos > now || e.observedAtNanos < 0 ||
            e.endpoint == NativeEndpoint.UNKNOWN) return false
        if (!ledger.commit(t,e)) return false
        t.readback = e;t.used = true;t.phase=Phase.COMMITTED
        return true
    }

    fun stop() {
        stopLatch.set(true)
        epoch++
    }

    fun recoverAfterProcessDeath() {
        stopLatch.set(true)
        epoch++
        nonce=freshNonce()
        // ledger.unresolved() is for reconciliation ONLY, never automatic dispatch.
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
