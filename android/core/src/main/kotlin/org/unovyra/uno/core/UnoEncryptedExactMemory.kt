package org.unovyra.uno.core

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Host S4 authority view. No raw bytes or permission grants. */
data class S4RecordRef(val id: Long, val generation: Long, val sha256: String, val scope: String)
data class S4AuthorityView(val status: S4Status, val generation: Long,
                           val live: Set<S4RecordRef>, val scannedRows: Int,
                           val validUntilNanos: Long = Long.MAX_VALUE)
data class S4Access(val scope: String, val now: Long, val consentEpoch: Long, val scanBudget: Int)

/** Exact observation memory contract: no neural action authority. */
interface UnoExactMemoryPort {
    val generation: Long
    fun write(scope: String, factKey: String, raw: ByteArray, expiry: Long,
              consentEpoch: Long, kind: EntryKind, source: String): ExactEntry
    fun read(scope: String, factKey: String, k: Int, scanBudget: Int,
             now: Long, consentEpoch: Long): ExactRead
    fun revoke(scope: String)
    /** Unsupported backends fail closed. Callback runs under the authoritative store lock. */
    fun <T> withS4Authority(access: S4Access, use: (S4AuthorityView) -> T): T =
        use(S4AuthorityView(S4Status.UNKNOWN, generation, emptySet(), 0))
    /** Highest accepted event time for this boot, or -1 when this boot has none. */
    fun causalFloor(): Long
    /** Records that time after the observation commit. Not an owner fact. */
    fun noteCausalFloor(eventNanos: Long)
}

/** All metadata, provenance, revocations, and record ordering are authenticated. */
internal object UnoExactVaultCodec {
    private const val SCHEMA = "UNO_EXACT_MEMORY/1"
    private val header = byteArrayOf(85, 78, 79, 69, 1) // UNOE v1
    private val aad = SCHEMA.toByteArray(Charsets.US_ASCII)
    const val MAX_ROWS = 256
    const val MAX_PLAIN = 1_500_000
    const val MAX_ENVELOPE = MAX_PLAIN + 5 + 12 + 16

    data class Row(val entry: ExactEntry, val bootToken: String)
    data class Snapshot(val revision: Long, val rows: List<Row>, val revoked: Set<String>)

    private fun validLabel(value: String, max: Int = 128): Boolean =
        value.length in 1..max && value.all { it >= ' ' && it != '\u007f' }
    private fun sha(data: ByteArray) = MessageDigest.getInstance("SHA-256")
        .digest(data).joinToString("") { "%02x".format(it) }
    private fun validDigest(value: String) = value.length == 64 &&
        value.all { it in '0'..'9' || it in 'a'..'f' }
    private fun validate(snapshot: Snapshot) {
        require(snapshot.revision >= 0 && snapshot.rows.size <= MAX_ROWS &&
            snapshot.revoked.size <= MAX_ROWS) { "EXACT_SNAPSHOT_BOUNDS" }
        require(snapshot.revoked.all { validLabel(it) }) { "EXACT_REVOKED_SCOPE_INVALID" }
        var previousId = 0L
        var previousGeneration = 0L
        snapshot.rows.forEach { row ->
            val e = row.entry
            require(e.id > previousId && e.generation > previousGeneration &&
                e.generation <= snapshot.revision && e.id <= snapshot.revision) {
                "EXACT_ORDER_INVALID"
            }
            require(validLabel(e.scope) && validLabel(e.factKey) && validLabel(e.source, 96) &&
                validLabel(row.bootToken, 128) && e.scope !in snapshot.revoked &&
                e.expiryMonotonicNanos >= 0 && e.consentEpoch >= 0 &&
                e.raw.isNotEmpty() && e.raw.size <= 4096 &&
                e.kind != EntryKind.VERIFIED_COMPLETION &&
                validDigest(e.sha256) && e.sha256 == sha(e.raw)) {
                "EXACT_ROW_INVALID"
            }
            previousId = e.id
            previousGeneration = e.generation
        }
    }
    fun encode(snapshot: Snapshot): ByteArray {
        validate(snapshot)
        val stream = ByteArrayOutputStream()
        DataOutputStream(stream).use { output ->
            output.writeUTF(SCHEMA)
            output.writeLong(snapshot.revision)
            output.writeInt(snapshot.revoked.size)
            snapshot.revoked.sorted().forEach(output::writeUTF)
            output.writeInt(snapshot.rows.size)
            snapshot.rows.forEach { row ->
                val e = row.entry
                output.writeLong(e.id)
                output.writeLong(e.generation)
                output.writeUTF(e.scope)
                output.writeUTF(e.factKey)
                output.writeLong(e.expiryMonotonicNanos)
                output.writeLong(e.consentEpoch)
                output.writeUTF(e.kind.name)
                output.writeUTF(e.source)
                output.writeUTF(row.bootToken)
                output.writeUTF(e.sha256)
                output.writeInt(e.raw.size)
                output.write(e.raw)
            }
        }
        val data = stream.toByteArray()
        require(data.size <= MAX_PLAIN) { "EXACT_SNAPSHOT_TOO_LARGE" }
        return data
    }
    fun decode(data: ByteArray): Snapshot {
        require(data.size in 1..MAX_PLAIN) { "EXACT_SNAPSHOT_SIZE_INVALID" }
        return DataInputStream(ByteArrayInputStream(data)).use { input ->
            require(input.readUTF() == SCHEMA) { "EXACT_SCHEMA_INVALID" }
            val revision = input.readLong()
            val revokedCount = input.readInt()
            require(revokedCount in 0..MAX_ROWS) { "EXACT_REVOKED_TOO_LARGE" }
            val revoked = (0 until revokedCount).map { input.readUTF() }
            require(revoked.toSet().size == revoked.size) { "EXACT_REVOKED_DUPLICATE" }
            val rowCount = input.readInt()
            require(rowCount in 0..MAX_ROWS) { "EXACT_ROWS_TOO_LARGE" }
            val rows = (0 until rowCount).map {
                val id = input.readLong()
                val generation = input.readLong()
                val scope = input.readUTF()
                val factKey = input.readUTF()
                val expiry = input.readLong()
                val epoch = input.readLong()
                val kind = EntryKind.valueOf(input.readUTF())
                val source = input.readUTF()
                val boot = input.readUTF()
                val digest = input.readUTF()
                val size = input.readInt()
                require(size in 1..4096) { "EXACT_PAYLOAD_SIZE_INVALID" }
                val bytes = ByteArray(size)
                input.readFully(bytes)
                Row(ExactEntry(id, generation, scope, factKey, bytes, digest, expiry,
                    epoch, kind, source), boot)
            }
            require(input.available() == 0) { "EXACT_TRAILING_PAYLOAD" }
            Snapshot(revision, rows, revoked.toSet()).also(::validate)
        }
    }
    fun seal(snapshot: Snapshot, key: SecretKey): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        // AndroidKeyStore rejects a caller-supplied IV when randomized encryption
        // is required. The provider generates the IV; the file format still stores it.
        cipher.init(Cipher.ENCRYPT_MODE, key)
        cipher.updateAAD(aad)
        val iv = cipher.iv
        require(iv != null && iv.size == 12) { "EXACT_IV_INVALID" }
        return header + iv + cipher.doFinal(encode(snapshot))
    }
    fun open(envelope: ByteArray, key: SecretKey): Snapshot {
        require(envelope.size in (header.size + 12 + 17)..MAX_ENVELOPE &&
            envelope.copyOfRange(0, header.size).contentEquals(header)) {
            "EXACT_ENVELOPE_INVALID"
        }
        val iv = envelope.copyOfRange(header.size, header.size + 12)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
        cipher.updateAAD(aad)
        return decode(cipher.doFinal(envelope, header.size + 12,
            envelope.size - header.size - 12))
    }
    fun sha256(data: ByteArray): String = sha(data)
}

/** Single-writer persistence contract. Readback verifies visibility, not power-loss durability.
 * If a write failed and the previous authenticated envelope is not demonstrably still
 * present, quarantine the live instance. Never continue serving a possibly revoked view.
 */
internal class UnoSnapshotCommit(private val load: () -> ByteArray?,
                                 private val persist: (ByteArray) -> Unit) {
    private var initial = load()
    private var digest = initial?.let(UnoExactVaultCodec::sha256)
    fun takeInitial(): ByteArray? = initial.also { initial = null }
    var uncertain = false
        private set
    fun requireHealthy() { check(!uncertain) { "MEMORY_PERSISTENCE_UNCERTAIN_REOPEN_REQUIRED" } }
    fun write(bytes: ByteArray) {
        requireHealthy()
        val next = UnoExactVaultCodec.sha256(bytes)
        try {
            persist(bytes)
            check(load()?.let(UnoExactVaultCodec::sha256) == next) { "MEMORY_PERSISTENCE_READBACK_MISMATCH" }
            digest = next
        } catch (e: Exception) {
            // A failure before replacement is recoverable only when the old bytes
            // are read back successfully. An exception after replacement is ambiguous.
            uncertain = try { load()?.let(UnoExactVaultCodec::sha256) != digest }
                        catch (_: Exception) { true }
            throw e
        }
    }
}

/**
 * Owner-controlled exact observation store, not semantic synthesis or OS permission.
 * Persist before publishing a new generation; if disk fails no in-memory commit.
 * Original precise bytes are retained with their source and revocation tombstones.
 * Boot-token mismatch means UNKNOWN, never false COMPLETE on a stale monotonic clock.
 */
class UnoEncryptedExactMemory(
    private val key: SecretKey,
    private val bootToken: String,
    private val load: () -> ByteArray?,
    private val persist: (ByteArray) -> Unit,
    /**
     * Android-only first-use bootstrap. Persist an authenticated empty vault
     * before publishing it as available. Existing nonempty/corrupt snapshots
     * are NEVER replaced, and a missing snapshot with an existing key must
     * be rejected by the adapter before invoking this constructor.
     *
     * Deliberately before clockElapsedNanos: keep the clock lambda last,
     * preserving existing Kotlin trailing-lambda call sites.
     */
    private val initializeEmptyOnFirstOpen: Boolean = false,
    private val clockElapsedNanos: () -> Long
): UnoExactMemoryPort {
    private companion object {
        const val CAUSAL_SCOPE = "uno-causal"
        const val CAUSAL_KEY = "causal-floor"
    }
    init { require(bootToken.length in 1..128 && bootToken.all { it >= ' ' }) }
    private val commit = UnoSnapshotCommit(load, persist)
    private var snapshot = commit.takeInitial()?.let { UnoExactVaultCodec.open(it, key) }
        ?: UnoExactVaultCodec.Snapshot(0L, emptyList(), emptySet()).also { empty ->
            if (initializeEmptyOnFirstOpen) commit.write(UnoExactVaultCodec.seal(empty, key))
        }

    override val generation: Long @Synchronized get() { commit.requireHealthy(); return snapshot.revision }

    @Synchronized override fun write(scope: String, factKey: String, raw: ByteArray,
                                     expiry: Long, consentEpoch: Long,
                                     kind: EntryKind, source: String): ExactEntry {
        commit.requireHealthy()
        val now = clockElapsedNanos()
        require(now >= 0 && expiry > now && consentEpoch >= 0 &&
            scope.length in 1..128 && factKey.length in 1..128 &&
            source.length in 1..96 && raw.isNotEmpty() && raw.size <= 4096 &&
            kind != EntryKind.VERIFIED_COMPLETION &&
            scope !in snapshot.revoked && snapshot.rows.size < UnoExactVaultCodec.MAX_ROWS &&
            snapshot.revision < Long.MAX_VALUE &&
            listOf(scope, factKey, source).all { text -> text.all { it >= ' ' && it != '\u007f' } }
        ) { "EXACT_WRITE_NOT_ALLOWED" }
        val bytes = raw.copyOf()
        val nextRevision = snapshot.revision + 1
        val entry = ExactEntry(nextRevision, nextRevision, scope, factKey, bytes,
            UnoExactVaultCodec.sha256(bytes), expiry, consentEpoch, kind, source)
        val updated = snapshot.copy(revision = nextRevision,
            rows = snapshot.rows + UnoExactVaultCodec.Row(entry, bootToken))
        commit.write(UnoExactVaultCodec.seal(updated, key))
        snapshot = updated
        return entry.copy(raw = bytes.copyOf())
    }

    @Synchronized override fun revoke(scope: String) {
        commit.requireHealthy()
        require(scope.length in 1..128 && scope.all { it >= ' ' && it != '\u007f' })
        if (scope in snapshot.revoked) return
        require(snapshot.revoked.size < UnoExactVaultCodec.MAX_ROWS &&
            snapshot.revision < Long.MAX_VALUE) { "EXACT_REVOKE_CAPACITY" }
        val updated = snapshot.copy(revision = snapshot.revision + 1,
            rows = snapshot.rows.filterNot { it.entry.scope == scope },
            revoked = snapshot.revoked + scope)
        commit.write(UnoExactVaultCodec.seal(updated, key))
        snapshot = updated
    }

    @Synchronized override fun <T> withS4Authority(access: S4Access, use: (S4AuthorityView) -> T): T {
        fun result(status: S4Status, live: Set<S4RecordRef> = emptySet(), scanned: Int = 0,
                   validUntil: Long = Long.MAX_VALUE) =
            use(S4AuthorityView(status, snapshot.revision, live, scanned, validUntil))
        if (access.scope.isBlank() || access.scope in snapshot.revoked) return result(S4Status.DENIED)
        if (commit.uncertain) return result(S4Status.UNKNOWN)
        val current = clockElapsedNanos()
        if (access.now < 0 || current < 0 || access.consentEpoch < 0 || access.scanBudget < 0)
            return result(S4Status.UNKNOWN)
        if (snapshot.rows.size > access.scanBudget) return result(S4Status.BUDGET_EXCEEDED)
        val now = maxOf(access.now, current)
        val liveRows = snapshot.rows.filter { row ->
            val e = row.entry
            row.bootToken == bootToken && e.scope == access.scope && e.consentEpoch == access.consentEpoch &&
                now < e.expiryMonotonicNanos && e.kind != EntryKind.SEMANTIC_SUMMARY &&
                e.kind != EntryKind.VERIFIED_COMPLETION
        }
        val live = liveRows.map { row -> row.entry.let { S4RecordRef(it.id, it.generation, it.sha256, it.scope) } }.toSet()
        val rev = snapshot.revision
        val output = result(if (live.isEmpty()) S4Status.EMPTY else S4Status.COMPLETE, live, snapshot.rows.size,
            liveRows.minOfOrNull { it.entry.expiryMonotonicNanos } ?: Long.MAX_VALUE)
        val end = clockElapsedNanos()
        check(!commit.uncertain && snapshot.revision == rev && end >= current &&
            liveRows.all { maxOf(access.now, end) < it.entry.expiryMonotonicNanos }) { "S4_AUTHORITY_STALE" }
        return output
    }

    @Synchronized override fun causalFloor(): Long {
        commit.requireHealthy()
        val raw = snapshot.rows.lastOrNull {
            it.bootToken == bootToken && it.entry.scope == CAUSAL_SCOPE &&
                it.entry.factKey == CAUSAL_KEY
        }?.entry?.raw ?: return -1L
        if (raw.size != 8) return -1L
        var value = 0L
        raw.forEach { value = (value shl 8) or (it.toLong() and 0xff) }
        return value
    }

    @Synchronized override fun noteCausalFloor(eventNanos: Long) {
        val prior = causalFloor()
        require(eventNanos >= 0 && eventNanos > prior) { "CAUSAL_FLOOR_INVALID" }
        val bytes = ByteArray(8)
        var rest = eventNanos
        for (i in 7 downTo 0) {
            bytes[i] = (rest and 0xff).toByte()
            rest = rest ushr 8
        }
        val nextRevision = snapshot.revision + 1
        require(nextRevision > snapshot.revision) { "CAUSAL_FLOOR_CAPACITY" }
        val entry = ExactEntry(nextRevision, nextRevision, CAUSAL_SCOPE, CAUSAL_KEY, bytes,
            UnoExactVaultCodec.sha256(bytes), Long.MAX_VALUE, 0L,
            EntryKind.HYPOTHESIS, "CAUSAL_FLOOR")
        val kept = snapshot.rows.filterNot {
            it.bootToken == bootToken && it.entry.scope == CAUSAL_SCOPE &&
                it.entry.factKey == CAUSAL_KEY
        }
        require(kept.size < UnoExactVaultCodec.MAX_ROWS) { "CAUSAL_FLOOR_CAPACITY" }
        val updated = snapshot.copy(revision = nextRevision,
            rows = kept + UnoExactVaultCodec.Row(entry, bootToken))
        commit.write(UnoExactVaultCodec.seal(updated, key))
        snapshot = updated
    }

    @Synchronized override fun read(scope: String, factKey: String, k: Int,
                                     scanBudget: Int, now: Long,
                                     consentEpoch: Long): ExactRead {
        if (scope.isBlank() || scope in snapshot.revoked)
            return ExactRead(ExactStatus.DENIED, emptyList(), 0)
        if (commit.uncertain) return ExactRead(ExactStatus.UNKNOWN, emptyList(), 0)
        val currentNow = clockElapsedNanos()
        if (now < 0 || consentEpoch < 0 || k <= 0 || scanBudget < 0 ||
            currentNow < 0) return ExactRead(ExactStatus.UNKNOWN, emptyList(), 0)
        val effectiveNow = maxOf(now, currentNow)
        if (scanBudget < snapshot.rows.size)
            return ExactRead(ExactStatus.TRUNCATED, emptyList(), 0)
        val matching = snapshot.rows.filter { r ->
            r.entry.scope == scope && r.entry.factKey == factKey &&
                r.entry.kind != EntryKind.SEMANTIC_SUMMARY
        }
        if (matching.any { it.bootToken != bootToken &&
            !UnoManualFacts.survivesBootForRead(it.entry) })
            return ExactRead(ExactStatus.UNKNOWN, emptyList(), 0)
        val valid = matching.map { it.entry }.filter { effectiveNow < it.expiryMonotonicNanos }
        if (valid.any { it.consentEpoch != consentEpoch ||
            UnoExactVaultCodec.sha256(it.raw) != it.sha256 })
            return ExactRead(ExactStatus.UNKNOWN, emptyList(), 0)
        if (valid.isEmpty()) return ExactRead(ExactStatus.NOT_FOUND, emptyList(), 0)
        val copies = valid.take(k).map { it.copy(raw = it.raw.copyOf()) }
        if (valid.size > k) return ExactRead(ExactStatus.TRUNCATED, copies, valid.size)
        return ExactRead(if (valid.map { it.sha256 }.toSet().size > 1)
            ExactStatus.CONFLICT else ExactStatus.COMPLETE, copies, valid.size)
    }
}

/**
 * Decides how to open exact memory without hiding a lost vault.
 * COMMITTED means a finished base or legacy backup exists.
 * PARTIAL means only an interrupted AtomicFile ".new" exists.
 * NONE means no ciphertext file exists; a key alone is not a vault.
 */
enum class ExactVaultResidue { NONE, COMMITTED, PARTIAL }

enum class ExactFirstOpen {
    REOPEN_COMMITTED,
    PROMOTE_PARTIAL,
    WRITE_GENESIS,
    REJECT_PARTIAL,
    REJECT_READONLY_EMPTY
}

fun exactFirstOpen(
    residue: ExactVaultResidue,
    keyExists: Boolean,
    readOnly: Boolean,
    partialAuthentic: Boolean
): ExactFirstOpen = when (residue) {
    ExactVaultResidue.COMMITTED -> {
        require(keyExists) { "EXACT_KEY_MISSING" }
        ExactFirstOpen.REOPEN_COMMITTED
    }
    ExactVaultResidue.PARTIAL ->
        if (keyExists && partialAuthentic) ExactFirstOpen.PROMOTE_PARTIAL
        else ExactFirstOpen.REJECT_PARTIAL
    ExactVaultResidue.NONE ->
        if (readOnly) ExactFirstOpen.REJECT_READONLY_EMPTY
        else ExactFirstOpen.WRITE_GENESIS
}

fun exactPartialAuthentic(bytes: ByteArray, key: javax.crypto.SecretKey): Boolean =
    runCatching { UnoExactVaultCodec.open(bytes, key) }.isSuccess
