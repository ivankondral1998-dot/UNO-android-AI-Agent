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
    val score: Double
)

data class SemanticRead(
    val status: SemanticStatus,
    val hits: List<SemanticHit>,
    val matchedLowerBound: Int
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

    init {
        val bytes = load()
        if (bytes != null) {
            val opened = open(bytes, key)
            links = opened.links
            revoked = opened.revoked
        }
    }

    @Synchronized fun link(entry: ExactEntry, vector: DoubleArray) {
        require(entry.kind != EntryKind.SEMANTIC_SUMMARY &&
            entry.kind != EntryKind.VERIFIED_COMPLETION) { "SEMANTIC_LINK_KIND" }
        require(vector.size == dimension && vector.all(Double::isFinite)) { "SEMANTIC_VECTOR" }
        val kept = links.filterNot { it.exactId == entry.id && it.boot == bootToken }
        require(kept.size < MAX_LINKS) { "SEMANTIC_CAPACITY" }
        val next = kept + Link(entry.id, entry.generation, entry.sha256, entry.scope,
            bootToken, vector.copyOf())
        persist(seal(Snapshot(next, revoked), key))
        links = next
    }

    @Synchronized fun dropScope(scope: String) {
        require(scope.isNotEmpty())
        if (scope in revoked) return
        val nextRevoked = revoked + scope
        val nextLinks = links.filterNot { it.scope == scope }
        persist(seal(Snapshot(nextLinks, nextRevoked), key))
        links = nextLinks
        revoked = nextRevoked
    }

    @Synchronized fun retrieve(scope: String, query: DoubleArray, k: Int, scanBudget: Int): SemanticRead {
        if (scope.isEmpty() || scope in revoked) return SemanticRead(SemanticStatus.DENIED, emptyList(), 0)
        if (k <= 0 || scanBudget < 0 || query.size != dimension || query.any { !it.isFinite() }) {
            return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        }
        val visible = links.filter { it.boot == bootToken && it.scope !in revoked }
        if (scanBudget < visible.size) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        val queryNorm = norm(query)
        if (queryNorm == 0.0) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        val scored = visible.mapNotNull { link ->
            if (link.scope != scope) return@mapNotNull null
            val linkNorm = norm(link.vector)
            if (linkNorm == 0.0) return@mapNotNull null
            val score = dot(query, link.vector) / (queryNorm * linkNorm)
            if (!score.isFinite()) return@mapNotNull null
            SemanticHit(link.exactId, link.generation, link.sha256, link.scope, score)
        }.sortedWith(compareByDescending<SemanticHit> { it.score }.thenBy { it.exactId })
        if (scored.isEmpty()) return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        if (scored.size > k) {
            return SemanticRead(SemanticStatus.TRUNCATED, scored.take(k), scored.size)
        }
        return SemanticRead(SemanticStatus.SUMMARY_ONLY, scored, scored.size)
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
