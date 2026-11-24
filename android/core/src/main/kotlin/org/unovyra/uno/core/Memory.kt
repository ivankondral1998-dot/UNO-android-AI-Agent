package org.unovyra.uno.core

import java.security.MessageDigest

enum class ExactStatus { DENIED, UNKNOWN, TRUNCATED, CONFLICT, COMPLETE, NOT_FOUND }
enum class EntryKind { OBSERVED, USER_DECLARATION, VERIFIED_COMPLETION, HYPOTHESIS, SEMANTIC_SUMMARY }

data class ExactEntry(
    val id: Long,
    val generation: Long,
    val scope: String,
    val factKey: String,
    val raw: ByteArray,
    val sha256: String,
    val expiryMonotonicNanos: Long,
    val consentEpoch: Long,
    val kind: EntryKind,
    val source: String
)

data class ExactRead(val status: ExactStatus,val entries: List<ExactEntry>,val matchedLowerBound: Int)

/** In-memory exact retrieval oracle. Actual encrypted storage and snapshot atomicity are OPEN. */
class ExactMemory(private val limit: Int = UnoAbi.MAX_MEMORY) : UnoExactMemoryPort {
    init { require(limit in 1..UnoAbi.MAX_MEMORY) }
    private val rows=linkedMapOf<Long,ExactEntry>()
    private val revoked=mutableSetOf<String>()
    private var seq=0L
    override var generation=0L
        private set
    var broken = false
        @Synchronized get
        @Synchronized set(value) {
            if (field == value) return
            check(generation < Long.MAX_VALUE) { "EXACT_GENERATION_EXHAUSTED" }
            field = value
            generation++
        }

    @Synchronized override fun write(scope:String, factKey:String, raw:ByteArray, expiry:Long,consentEpoch:Long,kind:EntryKind,source:String): ExactEntry {
        require(scope.isNotEmpty() && source.isNotEmpty() && factKey.isNotEmpty() && expiry>=0)
        // No verified OS outcome can originate from a free-form memory write.
        // Production needs a controller-bound native readback receipt and durable journal.
        require(kind != EntryKind.VERIFIED_COMPLETION) { "VERIFIED_COMPLETION_REQUIRES_NATIVE_READBACK" }
        require(raw.size<=4096 && rows.size<limit && !revoked.contains(scope))
        check(seq < Long.MAX_VALUE && generation < Long.MAX_VALUE) { "EXACT_GENERATION_EXHAUSTED" }
        val copy=raw.copyOf()
        val r=ExactEntry(++seq,++generation,scope,factKey,copy,sha(copy),expiry,consentEpoch,kind,source)
        rows[r.id]=r
        // Callers must never get a live reference to internal stored bytes.
        return r.copy(raw = r.raw.copyOf())
    }
    @Synchronized override fun revoke(scope:String) {
        require(scope.isNotBlank())
        if (scope in revoked) return
        check(generation < Long.MAX_VALUE) { "EXACT_GENERATION_EXHAUSTED" }
        revoked.add(scope)
        rows.entries.removeAll { it.value.scope==scope }
        generation++
    }
    @Synchronized override fun <T> withS4Authority(access: S4Access, use: (S4AuthorityView) -> T): T {
        fun result(status: S4Status, live: Set<S4RecordRef> = emptySet(), scanned: Int = 0,
                   validUntil: Long = Long.MAX_VALUE) =
            use(S4AuthorityView(status, generation, live, scanned, validUntil))
        if (access.scope.isBlank() || access.scope in revoked) return result(S4Status.DENIED)
        if (broken || access.now < 0 || access.consentEpoch < 0 || access.scanBudget < 0)
            return result(S4Status.UNKNOWN)
        if (rows.size > access.scanBudget) return result(S4Status.BUDGET_EXCEEDED)
        val liveRows = rows.values.filter { e -> e.scope == access.scope && e.consentEpoch == access.consentEpoch &&
            access.now < e.expiryMonotonicNanos && e.kind != EntryKind.SEMANTIC_SUMMARY &&
            e.kind != EntryKind.VERIFIED_COMPLETION && sha(e.raw) == e.sha256
        }
        val live = liveRows.map { S4RecordRef(it.id, it.generation, it.sha256, it.scope) }.toSet()
        val rev = generation
        val output = result(if (live.isEmpty()) S4Status.EMPTY else S4Status.COMPLETE, live, rows.size, liveRows.minOfOrNull { it.expiryMonotonicNanos } ?: Long.MAX_VALUE)
        check(generation == rev) { "S4_AUTHORITY_STALE" }
        return output
    }
    private var causalFloorNanos = -1L
    @Synchronized override fun causalFloor(): Long = causalFloorNanos
    @Synchronized override fun noteCausalFloor(eventNanos: Long) {
        require(eventNanos >= 0 && eventNanos > causalFloorNanos) { "CAUSAL_FLOOR_INVALID" }
        causalFloorNanos = eventNanos
    }
    @Synchronized override fun read(scope:String,factKey:String,k:Int,scanBudget:Int,now:Long,consentEpoch:Long):ExactRead {
        if (revoked.contains(scope) || scope.isBlank()) return ExactRead(ExactStatus.DENIED,emptyList(),0)
        if (broken || k<=0 || scanBudget<0 || now<0 || consentEpoch<0) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        // A real store requires a controller-held snapshot lock/revision guarantee.
        val snapshot=rows.values.toList()
        if (scanBudget<snapshot.size) return ExactRead(ExactStatus.TRUNCATED,emptyList(),0)
        val matches=snapshot.filter { it.scope==scope && it.factKey==factKey && now<it.expiryMonotonicNanos && it.kind!=EntryKind.SEMANTIC_SUMMARY }
        if (matches.any { it.consentEpoch!=consentEpoch || sha(it.raw)!=it.sha256 }) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        if (matches.size>k) return ExactRead(ExactStatus.TRUNCATED,matches.take(k).map { it.copy(raw = it.raw.copyOf()) },matches.size)
        if (matches.isEmpty()) return ExactRead(ExactStatus.NOT_FOUND, emptyList(), 0)
        val digests=matches.map { it.sha256 }.toSet()
        return ExactRead(if (digests.size>1) ExactStatus.CONFLICT else ExactStatus.COMPLETE,
            matches.map { it.copy(raw = it.raw.copyOf()) }, matches.size)
    }
    private fun sha(b:ByteArray):String=MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }
}
