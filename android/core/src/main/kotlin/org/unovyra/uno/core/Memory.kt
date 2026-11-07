package org.unovyra.uno.core

import java.security.MessageDigest

enum class ExactStatus { DENIED, UNKNOWN, TRUNCATED, CONFLICT, COMPLETE, NOT_FOUND }
enum class EntryKind { OBSERVED, USER_DECLARATION, VERIFIED_COMPLETION, HYPOTHESIS }

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
class ExactMemory(private val limit: Int = UnoAbi.MAX_MEMORY) {
    init { require(limit in 1..UnoAbi.MAX_MEMORY) }
    private val rows=linkedMapOf<Long,ExactEntry>()
    private val revoked=mutableSetOf<String>()
    private var seq=0L
    var generation=0L
        private set
    var broken=false

    @Synchronized fun write(scope:String, factKey:String, raw:ByteArray, expiry:Long,consentEpoch:Long,kind:EntryKind,source:String): ExactEntry {
        require(scope.isNotEmpty() && source.isNotEmpty() && factKey.isNotEmpty() && expiry>=0)
        // No verified OS outcome can originate from a free-form memory write.
        // Production needs a controller-bound native readback receipt and durable journal.
        require(kind != EntryKind.VERIFIED_COMPLETION) { "VERIFIED_COMPLETION_REQUIRES_NATIVE_READBACK" }
        require(raw.size<=4096 && rows.size<limit && !revoked.contains(scope))
        val copy=raw.copyOf()
        val r=ExactEntry(++seq,++generation,scope,factKey,copy,sha(copy),expiry,consentEpoch,kind,source)
        rows[r.id]=r
        // Callers must never get a live reference to internal stored bytes.
        return r.copy(raw = r.raw.copyOf())
    }
    @Synchronized fun revoke(scope:String) {
        revoked.add(scope)
        rows.entries.removeAll { it.value.scope==scope }
        generation++
    }
    @Synchronized fun read(scope:String,factKey:String,k:Int,scanBudget:Int,now:Long,consentEpoch:Long):ExactRead {
        if (revoked.contains(scope) || scope.isEmpty()) return ExactRead(ExactStatus.DENIED,emptyList(),0)
        if (broken || k<=0 || scanBudget<0) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        // A real store requires a controller-held snapshot lock/revision guarantee.
        val snapshot=rows.values.toList()
        if (scanBudget<snapshot.size) return ExactRead(ExactStatus.TRUNCATED,emptyList(),0)
        val matches=snapshot.filter { it.scope==scope && it.factKey==factKey && now<it.expiryMonotonicNanos }
        if (matches.any { it.consentEpoch!=consentEpoch || sha(it.raw)!=it.sha256 }) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        if (matches.size>k) return ExactRead(ExactStatus.TRUNCATED,matches.take(k).map { it.copy(raw = it.raw.copyOf()) },matches.size)
        if (matches.isEmpty()) return ExactRead(ExactStatus.NOT_FOUND, emptyList(), 0)
        val digests=matches.map { it.sha256 }.toSet()
        return ExactRead(if (digests.size>1) ExactStatus.CONFLICT else ExactStatus.COMPLETE,
            matches.map { it.copy(raw = it.raw.copyOf()) }, matches.size)
    }
    private fun sha(b:ByteArray):String=MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }
}
