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
 * This is NOT authorization, encryption, verified completion, native dispatch, or power-cut proof.
 * In particular, no code here calls Android OS actions or grants a permission. Callers must never
 * infer successful execution from an ARMED record. A recovery of ARMED means MAY_HAVE_EXECUTED.
 *
 * A full production outbox needs Android owner authentication, consent, readback and cross-resource
 * transactions. No automatic trimming/repair is allowed: damaged files fail closed.
 */
class ActionIntentJournal(file: File) : Closeable {
    enum class Phase { PREPARED, MAY_HAVE_EXECUTED }
    data class Row(val id: String, val proposalSha256: String, val phase: Phase, val recovered: Boolean)

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

    private fun body(id: String, digest: String, phase: Int, number: Long): ByteArray {
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { out ->
            out.writeByte(1) // format version
            out.writeLong(number)
            out.writeByte(phase)
            out.writeUTF(id)
            out.writeUTF(digest)
        }
        return bytes.toByteArray()
    }
    private fun sha(last: ByteArray, record: ByteArray): ByteArray =
        MessageDigest.getInstance("SHA-256").digest(last + record)

    private fun append(id: String, digest: String, phase: Int): Boolean {
        try {
            val payload = body(id, digest, phase, sequence + 1)
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
            if (input.available() != 0 || ver != 1 || counter != sequence + 1 ||
                !validId(id) || !validDigest(digest)) throw IOException("OUTBOX_PAYLOAD_INVALID")
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
                else -> throw IOException("OUTBOX_PHASE_UNKNOWN")
            }
            checksum = next
            sequence++
        }
    }
}
