package org.unovyra.uno

import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Owner-tapped, bounded app-private filesystem integration fixture.
 *
 * NOT a neural action, Android privilege, trusted NativePort, or independent OS attestation.
 * Separate readback opens the actual file again, instead of trusting the write return value.
 * A crash/STOP after create may leave an UNKNOWN marker: never retry the same ID blindly.
 * No file is deleted or overwritten by this probe.
 */
internal object AppPrivateReadbackProbe {
    private const val LIMIT = 16
    private const val DIR = "uno_local_effect_probe_v1"
    private val random = SecureRandom()

    enum class Status { VERIFIED_LOCAL_BYTES, UNKNOWN_MAY_HAVE_WRITTEN, DENIED, UNAVAILABLE }
    data class Result(val status: Status, val id: String?, val digest: String?, val detail: String)

    fun run(appFilesDir: File, stopped: () -> Boolean): Result {
        if (stopped()) return Result(Status.DENIED, null, null, "STOP_BEFORE_CREATE")
        val directory = File(appFilesDir, DIR)
        // Only trusted app-private filesDir is supplied by the Android Activity.
        if (!appFilesDir.isDirectory || directory.isSymbolicLink() ||
            (!directory.isDirectory && !directory.mkdir()) || !directory.isDirectory ||
            directory.canonicalFile.parentFile != appFilesDir.canonicalFile) {
            return Result(Status.UNAVAILABLE, null, null, "PRIVATE_DIRECTORY_UNAVAILABLE")
        }
        val existing = directory.listFiles() ?: return Result(Status.UNAVAILABLE, null, null, "LIST_FAILED")
        if (existing.size >= LIMIT) return Result(Status.DENIED, null, null, "FIXTURE_LIMIT_REACHED")
        if (stopped()) return Result(Status.DENIED, null, null, "STOP_BEFORE_CREATE")
        val nonce = ByteArray(16).also { random.nextBytes(it) }
            .joinToString("") { "%02x".format(it) }
        val id = "probe_$nonce"
        val file = File(directory, "$id.txt")
        val bytes = "UNO_APP_PRIVATE_EFFECT/1\n$id\n".toByteArray(Charsets.UTF_8)
        val digest = sha256(bytes)
        var created = false
        try {
            // No overwrite, no delete, no generic path or model-controlled payload.
            if (!file.createNewFile()) return Result(Status.DENIED, id, null, "NAME_COLLISION")
            created = true
            FileOutputStream(file, false).use { output ->
                if (stopped()) return Result(Status.UNKNOWN_MAY_HAVE_WRITTEN, id, digest, "STOP_AFTER_CREATE")
                output.write(bytes)
                output.fd.sync()
            }
            if (stopped()) return Result(Status.UNKNOWN_MAY_HAVE_WRITTEN, id, digest, "STOP_BEFORE_READBACK")
            // Fresh descriptor and actual bytes; write success is not the readback.
            val read = FileInputStream(file).use { input ->
                val actual = input.readBytes()
                if (actual.size > 128) return Result(Status.UNKNOWN_MAY_HAVE_WRITTEN, id, digest, "READBACK_OVERSIZE")
                actual
            }
            if (stopped()) return Result(Status.UNKNOWN_MAY_HAVE_WRITTEN, id, digest, "STOP_AFTER_READBACK")
            if (!read.contentEquals(bytes) || sha256(read) != digest) {
                return Result(Status.UNKNOWN_MAY_HAVE_WRITTEN, id, digest, "READBACK_MISMATCH")
            }
            return Result(Status.VERIFIED_LOCAL_BYTES, id, digest, "FRESH_DESCRIPTOR_BYTES_MATCH")
        } catch (_: Exception) {
            return Result(if (created) Status.UNKNOWN_MAY_HAVE_WRITTEN else Status.UNAVAILABLE,
                if (created) id else null, if (created) digest else null, "IO_ERROR_FAIL_CLOSED")
        }
    }

    /** Read-only inspection of one exact probe ID; does not confer action authority. */
    fun inspect(appFilesDir: File, id: String): Result {
        if (!Regex("probe_[0-9a-f]{32}").matches(id)) {
            return Result(Status.DENIED, null, null, "INVALID_ID")
        }
        val file = File(File(appFilesDir, DIR), "$id.txt")
        return try {
            if (!file.isFile || file.isSymbolicLink() || file.length() > 128L) {
                return Result(Status.UNAVAILABLE, id, null, "FILE_MISSING_OR_UNSAFE")
            }
            val actual = FileInputStream(file).use { it.readBytes() }
            val expected = "UNO_APP_PRIVATE_EFFECT/1\n$id\n".toByteArray(Charsets.UTF_8)
            if (actual.contentEquals(expected)) Result(Status.VERIFIED_LOCAL_BYTES,id,sha256(actual),"INDEPENDENT_REOPEN_MATCH")
            else Result(Status.UNKNOWN_MAY_HAVE_WRITTEN,id,sha256(actual),"INDEPENDENT_REOPEN_MISMATCH")
        } catch (_: Exception) {
            Result(Status.UNAVAILABLE,id,null,"READ_ERROR")
        }
    }

    private fun File.isSymbolicLink(): Boolean =
        try { canonicalFile != absoluteFile } catch (_: Exception) { true }

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
}
