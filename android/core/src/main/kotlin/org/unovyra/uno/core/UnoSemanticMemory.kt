package org.unovyra.uno.core

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlin.math.sqrt

enum class SemanticStatus { SUMMARY_ONLY, UNKNOWN, DENIED, TRUNCATED }

/** A numeric hint plus the exact record it points at. Never the raw fact. */
data class SemanticHit(
    val exactId: Long,
    val generation: Long,
    val sha256: String,
    val scope: String,
    val score: Double,
    val vector: DoubleArray
)

/** Raw S4 candidate. Not a verified exact record or training-derived key/value. */
data class S4EligibleSummary(
    val exactId: Long,
    val generation: Long,
    val sha256: String,
    val scope: String,
    val vector: DoubleArray
)

/** Typed catalogue admission; only COMPLETE/EMPTY may feed F. */
enum class S4Status { COMPLETE, EMPTY, DENIED, BUDGET_EXCEEDED, UNKNOWN, INCOMPATIBLE }
enum class S4Reason { NONE, DENIED_SCOPE, SCAN_LIMIT, UNAVAILABLE, STALE_LINK, INDEX_UNAVAILABLE, INCOMPATIBLE_VECTOR }
private fun S4Status.reason() = when (this) {
    S4Status.COMPLETE, S4Status.EMPTY -> S4Reason.NONE
    S4Status.DENIED -> S4Reason.DENIED_SCOPE
    S4Status.BUDGET_EXCEEDED -> S4Reason.SCAN_LIMIT
    S4Status.UNKNOWN -> S4Reason.UNAVAILABLE
    S4Status.INCOMPATIBLE -> S4Reason.INCOMPATIBLE_VECTOR
}
data class S4Catalogue(val status: S4Status, val hits: List<S4EligibleSummary>, val scannedRows: Int,
                       val authorityGeneration: Long? = null, val semanticGeneration: Long? = null,
                       val validUntilNanos: Long = Long.MAX_VALUE, val reason: S4Reason = status.reason())

data class SemanticRead(
    val status: SemanticStatus,
    val hits: List<SemanticHit>,
    val matchedLowerBound: Int,
    val catalogueStatus: S4Status? = null,
    val catalogueReason: S4Reason? = null
)

/**
 * Summary index for one organism. The caller supplies the vector.
 * This store does not embed text and does not decide anything.
 * A missing or unusable index is UNKNOWN, never an empty COMPLETE.
 */
class UnoSemanticMemory(
    private val key: SecretKey,
    private val bootToken: String,
    private val load: () -> ByteArray?,
    private val persist: (ByteArray) -> Unit,
    private val dimension: Int = DIM
) {
    init { require(dimension in 1..128 && bootToken.length in 1..128) }
    private var links = emptyList<Link>()
    private var revoked = emptySet<String>()
    private val commit = UnoSnapshotCommit(load, persist)
    private var revision = 0L
    internal val generation: Long
        @Synchronized get() { commit.requireHealthy(); return revision }

    init {
        val bytes = commit.takeInitial()
        if (bytes != null) {
            val opened = open(bytes, key)
            links = opened.links
            revoked = opened.revoked
        }
    }

    @Synchronized internal fun link(entry: ExactEntry, vector: DoubleArray) {
        commit.requireHealthy()
        require(entry.kind != EntryKind.SEMANTIC_SUMMARY &&
            entry.kind != EntryKind.VERIFIED_COMPLETION) { "SEMANTIC_LINK_KIND" }
        require(entry.scope !in revoked) { "SEMANTIC_SCOPE_REVOKED" }
        require(vector.size == dimension && vector.all(Double::isFinite)) { "SEMANTIC_VECTOR" }
        check(generation < Long.MAX_VALUE) { "SEMANTIC_GENERATION_EXHAUSTED" }
        val kept = links.filterNot { it.exactId == entry.id && it.boot == bootToken }
        require(kept.size < MAX_LINKS) { "SEMANTIC_CAPACITY" }
        val next = kept + Link(entry.id, entry.generation, entry.sha256, entry.scope,
            bootToken, vector.copyOf())
        commit.write(seal(Snapshot(next, revoked), key))
        links = next
        revision++
    }

    @Synchronized internal fun dropScope(scope: String) {
        commit.requireHealthy()
        require(scope.isNotEmpty())
        if (scope in revoked) return
        check(generation < Long.MAX_VALUE) { "SEMANTIC_GENERATION_EXHAUSTED" }
        require(revoked.size < MAX_LINKS) { "SEMANTIC_REVOKE_CAPACITY" }
        val nextRevoked = revoked + scope
        val nextLinks = links.filterNot { it.scope == scope }
        commit.write(seal(Snapshot(nextLinks, nextRevoked), key))
        links = nextLinks
        revoked = nextRevoked
        revision++
    }

    /**
     * Reconstructed S4 reference admission: no top-k truncation before F computes q.
     * Budget covers *all* persisted rows, including stale-boot and foreign-scope
     * rows. Over budget fails closed; filtering never silently drops a fifth hit.
     * This does NOT validate exact entry TTL, consent epoch or provenance.
     */
    @Synchronized internal fun eligibleForS4(scope: String, scanBudget: Int): S4Catalogue {
        if (scope.isBlank() || scope in revoked) return S4Catalogue(S4Status.DENIED, emptyList(), 0)
        if (commit.uncertain) return S4Catalogue(S4Status.UNKNOWN, emptyList(), 0, reason = S4Reason.INDEX_UNAVAILABLE)
        if (scanBudget < 0) return S4Catalogue(S4Status.UNKNOWN, emptyList(), 0)
        if (links.size > scanBudget) return S4Catalogue(S4Status.BUDGET_EXCEEDED, emptyList(), 0)
        val hits = links.asSequence()
            .filter { it.boot == bootToken && it.scope == scope && it.scope !in revoked }
            .map { S4EligibleSummary(it.exactId, it.generation, it.sha256, it.scope, it.vector.copyOf()) }
            .toList()
        return S4Catalogue(if (hits.isEmpty()) S4Status.EMPTY else S4Status.COMPLETE, hits, links.size)
    }

    @Synchronized internal fun retrieve(scope: String, query: DoubleArray, k: Int, scanBudget: Int): SemanticRead {
        if (scope.isEmpty() || scope in revoked) return SemanticRead(SemanticStatus.DENIED, emptyList(), 0)
        if (commit.uncertain) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        if (k <= 0 || scanBudget < 0 || query.size != dimension || query.any { !it.isFinite() }) {
            return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        }
        val visible = links.filter { it.boot == bootToken && it.scope !in revoked }
        if (scanBudget < visible.size) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        return summarizeS4Catalogue(visible.filter { it.scope == scope }.map {
            S4EligibleSummary(it.exactId, it.generation, it.sha256, it.scope, it.vector.copyOf())
        }, query, k)
    }

    private data class Link(
        val exactId: Long, val generation: Long, val sha256: String,
        val scope: String, val boot: String, val vector: DoubleArray
    )
    private data class Snapshot(val links: List<Link>, val revoked: Set<String>)

    private fun seal(snapshot: Snapshot, key: SecretKey): ByteArray {
        val plain = ByteArrayOutputStream()
        DataOutputStream(plain).use { out ->
            out.writeUTF(SCHEMA)
            out.writeInt(snapshot.revoked.size)
            snapshot.revoked.sorted().forEach(out::writeUTF)
            out.writeInt(snapshot.links.size)
            snapshot.links.forEach { link ->
                out.writeLong(link.exactId)
                out.writeLong(link.generation)
                out.writeUTF(link.sha256)
                out.writeUTF(link.scope)
                out.writeUTF(link.boot)
                out.writeInt(link.vector.size)
                link.vector.forEach(out::writeDouble)
            }
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        cipher.updateAAD(SCHEMA.toByteArray(Charsets.US_ASCII))
        val iv = cipher.iv
        require(iv != null && iv.size == 12)
        return HEADER + iv + cipher.doFinal(plain.toByteArray())
    }

    private fun open(envelope: ByteArray, key: SecretKey): Snapshot {
        require(envelope.size > HEADER.size + 12 + 16 &&
            envelope.copyOfRange(0, HEADER.size).contentEquals(HEADER)) { "SEMANTIC_ENVELOPE" }
        val iv = envelope.copyOfRange(HEADER.size, HEADER.size + 12)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
        cipher.updateAAD(SCHEMA.toByteArray(Charsets.US_ASCII))
        val plain = cipher.doFinal(envelope, HEADER.size + 12, envelope.size - HEADER.size - 12)
        return DataInputStream(ByteArrayInputStream(plain)).use { input ->
            require(input.readUTF() == SCHEMA)
            val revokedCount = input.readInt()
            require(revokedCount in 0..MAX_LINKS)
            val revoked = (0 until revokedCount).map { input.readUTF() }.toSet()
            val count = input.readInt()
            require(count in 0..MAX_LINKS)
            val links = (0 until count).map {
                val id = input.readLong()
                val generation = input.readLong()
                val sha = input.readUTF()
                val scope = input.readUTF()
                val boot = input.readUTF()
                val size = input.readInt()
                require(size == dimension)
                val vector = DoubleArray(size) { input.readDouble() }
                require(vector.all(Double::isFinite))
                Link(id, generation, sha, scope, boot, vector)
            }
            require(input.available() == 0)
            Snapshot(links, revoked)
        }
    }

    companion object {
        const val DIM = 8
        private const val MAX_LINKS = 256
        private const val SCHEMA = "UNO_SEMANTIC/1"
        private val HEADER = byteArrayOf(85, 78, 79, 83, 1) // UNOS v1
    }
}

/** Equal-weight mean. v and -v become zero and do not recover either record. */
fun unoSemanticAggregate(vectors: List<DoubleArray>): DoubleArray {
    require(vectors.isNotEmpty())
    val width = vectors[0].size
    require(vectors.all { it.size == width && it.all(Double::isFinite) })
    return DoubleArray(width) { index -> vectors.sumOf { it[index] } / vectors.size }
}

private fun dot(left: DoubleArray, right: DoubleArray): Double {
    var sum = 0.0
    for (i in left.indices) sum += left[i] * right[i]
    return sum
}

private fun norm(value: DoubleArray): Double = sqrt(dot(value, value))

/** Score only already admitted rows; no second index scan or authority bypass. */
internal fun summarizeS4Catalogue(hits: List<S4EligibleSummary>, query: DoubleArray, k: Int): SemanticRead {
    if (k <= 0 || query.any { !it.isFinite() } || hits.any { it.vector.size != query.size })
        return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
    val queryNorm = norm(query)
    if (!queryNorm.isFinite() || queryNorm == 0.0) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
    val scored = hits.mapNotNull { hit ->
        val n = norm(hit.vector)
        if (!n.isFinite() || n == 0.0) return@mapNotNull null
        val score = dot(query, hit.vector) / (queryNorm * n)
        if (!score.isFinite()) return@mapNotNull null
        SemanticHit(hit.exactId, hit.generation, hit.sha256, hit.scope, score, hit.vector.copyOf())
    }.sortedWith(compareByDescending<SemanticHit> { it.score }.thenBy { it.exactId })
    return when {
        scored.isEmpty() -> SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        scored.size > k -> SemanticRead(SemanticStatus.TRUNCATED, scored.take(k), scored.size)
        else -> SemanticRead(SemanticStatus.SUMMARY_ONLY, scored, scored.size)
    }
}
