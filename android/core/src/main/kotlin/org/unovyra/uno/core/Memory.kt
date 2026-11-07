package org.unovyra.uno.core

import java.security.MessageDigest

enum class ExactStatus { DENIED, UNKNOWN, TRUNCATED, CONFLICT, COMPLETE }
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

    fun write(scope:String, factKey:String, raw:ByteArray, expiry:Long,consentEpoch:Long,kind:EntryKind,source:String): ExactEntry {
        require(scope.isNotEmpty() && source.isNotEmpty() && factKey.isNotEmpty() && expiry>=0)
        require(raw.size<=4096 && rows.size<limit && !revoked.contains(scope))
        val copy=raw.copyOf()
        val r=ExactEntry(++seq,++generation,scope,factKey,copy,sha(copy),expiry,consentEpoch,kind,source)
        rows[r.id]=r
        return r
    }
    fun revoke(scope:String) {
        revoked.add(scope)
        rows.entries.removeAll { it.value.scope==scope }
        generation++
    }
    fun read(scope:String,factKey:String,k:Int,scanBudget:Int,now:Long,consentEpoch:Long):ExactRead {
        if (revoked.contains(scope) || scope.isEmpty()) return ExactRead(ExactStatus.DENIED,emptyList(),0)
        if (broken || k<=0 || scanBudget<0) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        // A real store requires a controller-held snapshot lock/revision guarantee.
        val snapshot=rows.values.toList()
        if (scanBudget<snapshot.size) return ExactRead(ExactStatus.TRUNCATED,emptyList(),0)
        val matches=snapshot.filter { it.scope==scope && it.factKey==factKey && now<it.expiryMonotonicNanos }
        if (matches.any { it.consentEpoch!=consentEpoch || sha(it.raw)!=it.sha256 }) return ExactRead(ExactStatus.UNKNOWN,emptyList(),0)
        if (matches.size>k) return ExactRead(ExactStatus.TRUNCATED,matches.take(k),matches.size)
        val digests=matches.map { it.sha256 }.toSet()
        return ExactRead(if (digests.size>1) ExactStatus.CONFLICT else ExactStatus.COMPLETE,matches,matches.size)
    }
    private fun sha(b:ByteArray):String=MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }
}
