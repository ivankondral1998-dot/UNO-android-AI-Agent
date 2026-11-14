package org.unovyra.uno.core

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.Closeable
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.File
import java.io.IOException
import java.io.RandomAccessFile
import java.nio.channels.FileLock
import java.nio.channels.OverlappingFileLockException
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Single-writer persistent *intent* journal, independent of the neural model and Android APIs.
 *
 * This is NOT authorization, encryption, native dispatch, independent readback, or power-cut proof.
 * A recorded receipt is a source-tagged *claim* from the reference controller, not OS proof.
 * In particular, no code here calls Android OS actions or grants a permission. Callers must never
 * infer successful execution from an ARMED record. A recovery of ARMED means MAY_HAVE_EXECUTED.
 *
 * A full production outbox needs Android owner authentication, consent, readback and cross-resource
 * transactions. No automatic trimming/repair is allowed: damaged files fail closed.
 */
class ActionIntentJournal(file: File) : Closeable {
    enum class Phase { PREPARED, MAY_HAVE_EXECUTED, RECEIPT_RECORDED, REFERENCE_USED_RECEIPT }
    data class Row(
        val id: String,
        val proposalSha256: String,
        val phase: Phase,
        val recovered: Boolean,
        val receipt: NativeEvidence? = null,
        val used: Boolean = false
    )

    private val stop = AtomicBoolean(false)
    private val rows = LinkedHashMap<String, Row>()
    private val stream: RandomAccessFile
    private val lock: FileLock
    private var checksum = ByteArray(32)
    private var sequence = 0L
    private var failed = false
    private var closed = false

    init {
        require(file.parentFile?.isDirectory == true) { "OUTBOX_PARENT_NOT_DIRECTORY" }
        val raf = RandomAccessFile(file, "rw")
        val acquired = try { raf.channel.tryLock() }
            catch (_: OverlappingFileLockException) { null }
            catch (ex: Exception) { raf.close(); throw ex }
        if (acquired == null) {
            raf.close()
            throw IllegalStateException("OUTBOX_ALREADY_OPEN")
        }
        try {
            stream = raf
            lock = acquired
            replay()
        } catch (ex: Exception) {
            acquired.release()
            raf.close()
            throw ex
        }
    }

    @Synchronized fun snapshot(): List<Row> = rows.values.toList()
    @Synchronized fun isFailed(): Boolean = failed
    fun isStopped(): Boolean = stop.get()

    /** No replay of even PREPARED entries after restart. New consent would require a NEW ticket. */
    @Synchronized fun prepare(id: String, proposalSha256: String): Boolean {
        if (!usable() || !validId(id) || !validDigest(proposalSha256) || rows.size >= 4096 ||
            rows.containsKey(id)) return false
        if (!append(id, proposalSha256, 1)) return false
        rows[id] = Row(id, proposalSha256, Phase.PREPARED, recovered = false)
        return !stop.get()
    }

    /**
     * Persist the 'might be executed' state BEFORE an external controller attempts native dispatch.
     * true is a journal state, NEVER owner/OS authority and NEVER confirmation of an OS action.
     */
    @Synchronized fun arm(id: String, proposalSha256: String): Boolean {
        val old = rows[id] ?: return false
        if (!usable() || old.recovered || old.phase != Phase.PREPARED ||
            old.proposalSha256 != proposalSha256) return false
        if (!append(id, proposalSha256, 2)) return false
        rows[id] = old.copy(phase = Phase.MAY_HAVE_EXECUTED)
        // The caller still needs an independent STOP/admission check before dispatch.
        return !stop.get()
    }

    /**
     * Persist an already-controller-validated positive readback claim in the SAME hash chain.
     * An arbitrary caller can fabricate a NativeEvidence; this method is NOT a trusted verifier.
     * No P-version, memory references, or cross-file transaction exists in this reference store.
     */
    @Synchronized internal fun recordReadbackClaim(
        id: String, proposalSha256: String, evidence: NativeEvidence
    ): Boolean {
        val old = rows[id] ?: return false
        if (!usable() || old.recovered || old.phase != Phase.MAY_HAVE_EXECUTED ||
            old.proposalSha256 != proposalSha256 || evidence.ticketId != id ||
            evidence.endpoint != NativeEndpoint.TRUE || evidence.nativeGeneration <= 0 ||
            evidence.observedAtNanos < 0 || !validSource(evidence.source)) return false
        if (!append(id, proposalSha256, 3, evidence)) return false
        rows[id] = old.copy(phase = Phase.RECEIPT_RECORDED, receipt = evidence)
        return !stop.get()
    }

    /**
     * Reference-only atomic terminal marker: used=true and a positive source-tagged
     * receipt are written in ONE v2 append+fsync record. Not A_cap/A_tx for Android,
     * not atomic with external memory files or P versions, and not an OS proof.
     * Old v1 RECEIPT_RECORDED records never imply a durable used bit.
     */
    @Synchronized internal fun recordReferenceUsedReceipt(
        id: String, proposalSha256: String, evidence: NativeEvidence
    ): Boolean {
        val old = rows[id] ?: return false
        if (!usable() || old.recovered || old.phase != Phase.MAY_HAVE_EXECUTED ||
            old.proposalSha256 != proposalSha256 || evidence.ticketId != id ||
            evidence.endpoint != NativeEndpoint.TRUE || evidence.nativeGeneration <= 0 ||
            evidence.observedAtNanos < 0 || !validSource(evidence.source)) return false
        if (!append(id, proposalSha256, 4, evidence)) return false
        rows[id] = old.copy(phase = Phase.REFERENCE_USED_RECEIPT, receipt = evidence, used = true)
        return !stop.get()
    }

    /** One-way STOP for this journal instance. Does not interrupt an in-flight OS operation. */
    fun stop() { stop.set(true) }

    @Synchronized override fun close() {
        if (closed) return
        stop.set(true)
        closed = true
        try { lock.release() } finally { stream.close() }
    }

    private fun usable() = !closed && !failed && !stop.get() && sequence < Long.MAX_VALUE
    private fun validId(s: String) = s.length in 1..128 && s.all { it in 'a'..'z' ||
        it in 'A'..'Z' || it in '0'..'9' || it in "_-:." }
    private fun validDigest(s: String) = s.length == 64 && s.all { it in '0'..'9' || it in 'a'..'f' }
    private fun validSource(s: String) = s.length in 1..96 && s.all { it in 'a'..'z' ||
        it in 'A'..'Z' || it in '0'..'9' || it in "_-:." }

    private fun body(
        id: String, digest: String, phase: Int, number: Long, evidence: NativeEvidence?
    ): ByteArray {
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { out ->
            out.writeByte(if (phase == 4) 2 else 1) // v2 atomic reference used+receipt; v1 stays readable
            out.writeLong(number)
            out.writeByte(phase)
            out.writeUTF(id)
            out.writeUTF(digest)
            if (phase == 3 || phase == 4) {
                val receipt = evidence ?: error("RECEIPT_REQUIRED")
                out.writeUTF(receipt.source)
                out.writeLong(receipt.nativeGeneration)
                out.writeLong(receipt.observedAtNanos)
                out.writeByte(1) // Only controller-checked TRUE claims may be recorded.
                if (phase == 4) out.writeByte(1) // used=true in the SAME synced record
            }
        }
        return bytes.toByteArray()
    }
    private fun sha(last: ByteArray, record: ByteArray): ByteArray =
        MessageDigest.getInstance("SHA-256").digest(last + record)

    private fun append(
        id: String, digest: String, phase: Int, evidence: NativeEvidence? = null
    ): Boolean {
        try {
            val payload = body(id, digest, phase, sequence + 1, evidence)
            val next = sha(checksum, payload)
            stream.seek(stream.length())
            stream.writeInt(payload.size)
            stream.write(payload)
            stream.write(next)
            stream.fd.sync() // successful arm is only returned after the record sync
            sequence++
            checksum = next
            return true
        } catch (_: IOException) {
            failed = true // torn write must not lead to retries
            return false
        }
    }

    private fun replay() {
        stream.seek(0)
        while (stream.filePointer < stream.length()) {
            if (stream.length() - stream.filePointer < 4L) throw IOException("OUTBOX_TRUNCATED_LENGTH")
            val len = stream.readInt()
            if (len !in 13..512 || stream.length() - stream.filePointer < len.toLong() + 32L)
                throw IOException("OUTBOX_TRUNCATED_OR_INVALID_RECORD")
            val record = ByteArray(len)
            val recordedHash = ByteArray(32)
            stream.readFully(record)
            stream.readFully(recordedHash)
            val next = sha(checksum, record)
            if (!MessageDigest.isEqual(next, recordedHash)) throw IOException("OUTBOX_CHAIN_INVALID")
            val input = DataInputStream(ByteArrayInputStream(record))
            val ver = input.readUnsignedByte()
            val counter = input.readLong()
            val phase = input.readUnsignedByte()
            val id = input.readUTF()
            val digest = input.readUTF()
            if (!((ver == 1 && phase in 1..3) || (ver == 2 && phase == 4)) ||
                counter != sequence + 1 || !validId(id) || !validDigest(digest))
                throw IOException("OUTBOX_PAYLOAD_INVALID")
            val receipt = if (phase == 3 || phase == 4) {
                val source = input.readUTF()
                val generation = input.readLong()
                val observed = input.readLong()
                val endpointCode = input.readUnsignedByte()
                if (!validSource(source) || generation <= 0 || observed < 0 || endpointCode != 1)
                    throw IOException("OUTBOX_RECEIPT_INVALID")
                NativeEvidence(id, NativeEndpoint.TRUE, generation, observed, source)
            } else null
            if (phase == 4 && input.readUnsignedByte() != 1)
                throw IOException("OUTBOX_USED_MARKER_INVALID")
            if (input.available() != 0) throw IOException("OUTBOX_TRAILING_PAYLOAD")
            when (phase) {
                1 -> {
                    if (rows.size >= 4096 || rows.containsKey(id)) throw IOException("OUTBOX_DUPLICATE_PREPARE")
                    rows[id] = Row(id, digest, Phase.PREPARED, recovered = true)
                }
                2 -> {
                    val old = rows[id]
                    if (old == null || old.proposalSha256 != digest || old.phase != Phase.PREPARED)
                        throw IOException("OUTBOX_INVALID_TRANSITION")
                    rows[id] = old.copy(phase = Phase.MAY_HAVE_EXECUTED)
                }
                3 -> {
                    val old = rows[id]
                    if (old == null || old.proposalSha256 != digest ||
                        old.phase != Phase.MAY_HAVE_EXECUTED || receipt == null)
                        throw IOException("OUTBOX_INVALID_RECEIPT_TRANSITION")
                    rows[id] = old.copy(phase = Phase.RECEIPT_RECORDED, receipt = receipt)
                }
                4 -> {
                    val old = rows[id]
                    if (old == null || old.proposalSha256 != digest ||
                        old.phase != Phase.MAY_HAVE_EXECUTED || receipt == null)
                        throw IOException("OUTBOX_INVALID_ATOMIC_REFERENCE_COMMIT")
                    rows[id] = old.copy(
                        phase = Phase.REFERENCE_USED_RECEIPT, receipt = receipt, used = true
                    )
                }
                else -> throw IOException("OUTBOX_PHASE_UNKNOWN")
            }
            checksum = next
            sequence++
        }
    }
}
